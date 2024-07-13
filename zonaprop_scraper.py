import requests
from bs4 import BeautifulSoup
import json
import re
import time
import logging
import argparse
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import random
from datetime import date
from abc import ABC, abstractmethod

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Listing:
    def __init__(self, id, date, price, expenses, location_address, location_area, features, description, url):
        self.id = id
        self.date = date
        self.price = price
        self.expenses = expenses
        self.location_address = location_address
        self.location_area = location_area
        self.features = features
        self.description = description
        self.url = url


class ScraperService:
    def __init__(self):
        self.session = self.create_session_with_retries()

    @staticmethod
    def create_session_with_retries():
        session = requests.Session()
        retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        session.mount('https://', HTTPAdapter(max_retries=retries))
        return session

    def rate_limited_request(self, url, headers):
        delay = random.uniform(3, 7)
        time.sleep(delay)
        try:
            logger.info(f"Sending request to: {url} after {delay:.2f} seconds delay")
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            logger.info(f"Received response from: {url}")
            return response
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    @staticmethod
    def safe_extract(element, selector, attribute=None):
        found = element.select_one(selector)
        if not found:
            return None
        if attribute:
            return found.get(attribute)
        return found.get_text(strip=True)


class ListingRepository(ABC):
    @abstractmethod
    def get_all_page_urls(self, start_url, max_pages=None):
        pass

    @abstractmethod
    def scrape_page(self, url):
        pass

    @abstractmethod
    def scrape_listing_details(self, url):
        pass


class ZonapropRepository(ListingRepository):
    def __init__(self, scraper_service):
        self.scraper_service = scraper_service

    def get_all_page_urls(self, start_url, max_pages=None):
        logger.info(f"Getting all page URLs starting from: {start_url}")
        page_urls = [start_url]
        current_url = start_url
        page_num = 1

        while current_url:
            response = self.scraper_service.rate_limited_request(current_url, headers={'User-Agent': 'Mozilla/5.0'})
            if not response:
                break

            soup = BeautifulSoup(response.content, 'html.parser')
            current_page = int(re.search(r'PAGING_(\d+)', str(soup)).group(1))
            next_page = soup.find('a', attrs={'data-qa': f'PAGING_{current_page + 1}'})

            if next_page:
                next_page_url = f"https://www.zonaprop.com.ar{next_page['href']}"
                page_urls.append(next_page_url)
                current_url = next_page_url
                page_num += 1
                logger.info(f"Found page {page_num}: {next_page_url}")
            else:
                current_url = None

            if max_pages and page_num >= max_pages:
                logger.info(f"Reached maximum number of pages ({max_pages})")
                break

        logger.info(f"Found a total of {len(page_urls)} pages")
        return page_urls

    def scrape_page(self, url):
        logger.info(f"Scraping page: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = self.scraper_service.rate_limited_request(url, headers)
        if not response:
            logger.error(f"Failed to get response from {url}")
            return []

        soup = BeautifulSoup(response.content, 'html.parser')
        listings = []
        listing_containers = soup.find_all('div', class_='PostingCardLayout-sc-i1odl-0')

        logger.info(f"Found {len(listing_containers)} listings on this page")

        current_date = date.today().isoformat()

        for index, listing in enumerate(listing_containers, start=1):
            logger.info(f"Processing listing {index} of {len(listing_containers)}")
            try:
                listing_url = f"https://www.zonaprop.com.ar{self.scraper_service.safe_extract(listing, 'a', 'href')}"

                id_match = re.search(r'-(\d+)\.html$', listing_url)
                listing_id = id_match.group(1) if id_match else None

                item = Listing(
                    id=listing_id,
                    date=current_date,
                    price=self.scraper_service.safe_extract(listing, 'div[data-qa="POSTING_CARD_PRICE"]'),
                    expenses=self.scraper_service.safe_extract(listing, 'div[data-qa="expensas"]'),
                    location_address=self.scraper_service.safe_extract(listing, 'div.postingAddress'),
                    location_area=self.scraper_service.safe_extract(listing, 'h2[data-qa="POSTING_CARD_LOCATION"]'),
                    features=[span.text.strip() for span in listing.select('h3.PostingMainFeaturesBlock-sc-1uhtbxc-0 span')],
                    description=self.scraper_service.safe_extract(listing, 'h3[data-qa="POSTING_CARD_DESCRIPTION"]'),
                    url=listing_url
                )

                logger.info(f"Scraping detailed information for listing: {item.url}")
                detailed_info = self.scrape_listing_details(item.url)
                item.__dict__.update(detailed_info)

                listings.append(item)
                logger.info(f"Successfully processed listing {index} with ID {listing_id}")
            except Exception as e:
                logger.error(f"Error parsing listing {index}: {e}")

        return listings

    def scrape_listing_details(self, url):
        logger.info(f"Scraping detailed listing from: {url}")
        response = self.scraper_service.rate_limited_request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        if not response:
            logger.warning(f"No response received for listing: {url}")
            return {}

        soup = BeautifulSoup(response.content, 'html.parser')
        details = {}

        details.update(self._extract_feature_information(soup))
        details.update(self._extract_publisher_information(soup))

        logger.info(f"Finished scraping details for listing: {url}")
        return details

    def _extract_feature_information(self, soup):
        details = {}
        feature_section = soup.find('ul', id='section-icon-features-property')
        if feature_section:
            logger.info("Found feature section in the listing page")
            icon_to_attr = {
                'icon-stotal': 'total_area',
                'icon-scubierta': 'covered_area',
                'icon-ambiente': 'rooms',
                'icon-bano': 'bathrooms',
                'icon-cochera': 'parking_spaces',
                'icon-dormitorio': 'bedrooms',
                'icon-antiguedad': 'age'
            }

            for icon_class, attr_name in icon_to_attr.items():
                element = feature_section.find('i', class_=icon_class)
                if element and element.parent:
                    value = element.parent.get_text(strip=True)
                    numeric_value = re.search(r'\d+', value)
                    if numeric_value:
                        details[attr_name] = numeric_value.group()
                        logger.info(f"Extracted {attr_name}: {details[attr_name]}")
                    else:
                        logger.warning(f"Could not extract numeric value for {attr_name}")
                else:
                    logger.warning(f"Could not find element for {attr_name}")
        else:
            logger.warning("Could not find feature section in the listing page")

        return details

    def _extract_publisher_information(self, soup):
        details = {}
        script_tags = soup.find_all('script')
        for script in script_tags:
            if script.string and "'publisher':" in script.string:
                match = re.search(r"'publisher'\s*:\s*(\{[^}]+\})", script.string)
                if match:
                    publisher_json = match.group(1).replace("'", '"')
                    try:
                        publisher_data = json.loads(publisher_json)
                        details['publisher_name'] = publisher_data.get('name')
                        details['publisher_id'] = publisher_data.get('publisherId')
                        details['publisher_url'] = publisher_data.get('url')
                        logger.info(f"Extracted publisher data: {publisher_data}")
                        break
                    except json.JSONDecodeError:
                        logger.error("Error decoding publisher JSON")
                else:
                    logger.warning("Could not find publisher data in script")
        else:
            logger.warning("Could not find script with publisher data")

        return details

class ScraperManager:
    def __init__(self, repository):
        self.repository = repository

    def scrape(self, start_url, max_pages=None):
        page_urls = self.repository.get_all_page_urls(start_url, max_pages)
        all_listings = []

        for page_num, page_url in enumerate(page_urls, start=1):
            logger.info(f"Scraping page {page_num} of {len(page_urls)}")
            page_listings = self.repository.scrape_page(page_url)
            all_listings.extend(page_listings)

        return all_listings

def main():
    parser = argparse.ArgumentParser(description='Scrape Zonaprop listings.')
    parser.add_argument('--max_pages', type=int, default=1, help='Maximum number of pages to scrape')
    parser.add_argument('--output', type=str, default='zonaprop_caballito_rentals_detailed.json', help='Output JSON file name')
    parser.add_argument('--url', type=str, default='https://www.zonaprop.com.ar/casas-departamentos-ph-alquiler-caballito.html', help='Starting URL for scraping')
    args = parser.parse_args()

    logger.info(f"Starting scraping process with max_pages={args.max_pages}, output={args.output}, url={args.url}")

    scraper_service = ScraperService()
    repository = ZonapropRepository(scraper_service)
    manager = ScraperManager(repository)

    listings = manager.scrape(args.url, max_pages=args.max_pages)

    if listings:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump([listing.__dict__ for listing in listings], f, ensure_ascii=False, indent=4)
        logger.info(f"Scraped {len(listings)} listings and saved to {args.output}")
    else:
        logger.warning("No listings were found or scraped.")

    logger.info("Scraping process completed")

if __name__ == "__main__":
    main()
