from abc import ABC, abstractmethod
import logging
import re
import json
from bs4 import BeautifulSoup
from src.models import Listing
from datetime import date
from src.utils import (
    safe_extract,
    clean_price_string,
    clean_expenses_string,
    get_currency_type
)


logger = logging.getLogger(__name__)


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

        for index, listing in enumerate(listing_containers, start=1):
            logger.info(f"Processing listing {index} of {len(listing_containers)}")
            try:
                listing_url = f"https://www.zonaprop.com.ar{safe_extract(listing, 'a', 'href')}"

                id_match = re.search(r'-(\d+)\.html$', listing_url)
                listing_id = id_match.group(1) if id_match else None

                item = Listing(
                    id=listing_id,
                    date=date.today(),
                    price=clean_price_string(safe_extract(listing, 'div[data-qa="POSTING_CARD_PRICE"]')),
                    currency=get_currency_type(safe_extract(listing, 'div[data-qa="POSTING_CARD_PRICE"]')),
                    expenses=clean_expenses_string(safe_extract(listing, 'div[data-qa="expensas"]')),
                    location_address=safe_extract(listing, 'div.postingAddress'),
                    location_area=safe_extract(listing, 'h2[data-qa="POSTING_CARD_LOCATION"]'),
                    features=[span.text.strip() for span in listing.select('h3.PostingMainFeaturesBlock-sc-1uhtbxc-0 span')],
                    description=safe_extract(listing, 'h3[data-qa="POSTING_CARD_DESCRIPTION"]'),
                    url=listing_url
                )

                logger.info(f"Scraping detailed information for listing: {item.url}")
                detailed_info = self.scrape_listing_details(item.url)

                item.update_details(detailed_info)
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
