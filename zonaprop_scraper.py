import requests
from bs4 import BeautifulSoup
import json
import re
import time
import logging
import argparse
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from ratelimit import limits, sleep_and_retry

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_session_with_retries():
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session


def safe_extract(element, selector, attribute=None):
    found = element.select_one(selector)
    if not found:
        return None
    if attribute:
        return found.get(attribute)
    return found.get_text(strip=True)


# Rate limiting: 1 request per 5 seconds
@sleep_and_retry
@limits(calls=1, period=5)
def rate_limited_request(session, url, headers):
    try:
        response = session.get(url, headers=headers)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return None


def scrape_listing_details(session, url):

    response = rate_limited_request(session, url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
    if not response:
        return {}

    soup = BeautifulSoup(response.content, 'html.parser')
    details = {}

    # Find the section with the specified attributes
    feature_section = soup.find('ul', id='section-icon-features-property')

    if feature_section:
        # Dictionary to map icon classes to attribute names
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
                # Extract only the numeric part
                numeric_value = re.search(r'\d+', value)
                if numeric_value:
                    details[attr_name] = numeric_value.group()

    return details


def scrape_zonaprop_page(url, session):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    response = rate_limited_request(session, url, headers)
    if not response:
        return [], None

    soup = BeautifulSoup(response.content, 'html.parser')

    listings = []
    listing_containers = soup.find_all('div', class_='PostingCardLayout-sc-i1odl-0')

    logger.info(f"Found {len(listing_containers)} listings on this page")

    for listing in listing_containers:
        try:
            item = {
                'price': safe_extract(listing, 'div[data-qa="POSTING_CARD_PRICE"]'),
                'expenses': safe_extract(listing, 'div[data-qa="expensas"]'),
                'location_address': safe_extract(listing, 'div.postingAddress'),
                'location_area': safe_extract(listing, 'h2[data-qa="POSTING_CARD_LOCATION"]'),
                'features': [span.text.strip() for span in listing.select('h3.PostingMainFeaturesBlock-sc-1uhtbxc-0 span')],
                'description': safe_extract(listing, 'h3[data-qa="POSTING_CARD_DESCRIPTION"]'),
                'url': f"https://www.zonaprop.com.ar{safe_extract(listing, 'a', 'href')}",
            }

            # Scrape detailed information from the listing page
            detailed_info = scrape_listing_details(session, item['url'])
            item.update(detailed_info)

            listings.append(item)
        except Exception as e:
            logger.error(f"Error parsing a listing: {e}")

    current_page = int(re.search(r'PAGING_(\d+)', str(soup)).group(1))
    next_page = soup.find('a', attrs={'data-qa': f'PAGING_{current_page + 1}'})
    next_page_url = f"https://www.zonaprop.com.ar{next_page['href']}" if next_page else None

    return listings, next_page_url

def scrape_zonaprop(start_url, max_pages=None):
    all_listings = []
    current_url = start_url
    page_num = 1
    session = create_session_with_retries()

    while current_url:
        logger.info(f"Scraping page {page_num}...")
        page_listings, next_page_url = scrape_zonaprop_page(current_url, session)
        all_listings.extend(page_listings)

        if max_pages and page_num >= max_pages:
            logger.info(f"Reached maximum number of pages ({max_pages})")
            break

        current_url = next_page_url
        page_num += 1

    return all_listings

def main():
    parser = argparse.ArgumentParser(description='Scrape Zonaprop listings.')
    parser.add_argument('--max_pages', type=int, default=1, help='Maximum number of pages to scrape')
    parser.add_argument('--output', type=str, default='zonaprop_caballito_rentals_detailed.json', help='Output JSON file name')
    parser.add_argument('--url', type=str, default='https://www.zonaprop.com.ar/casas-departamentos-ph-alquiler-caballito.html', help='Starting URL for scraping')
    args = parser.parse_args()

    listings = scrape_zonaprop(args.url, max_pages=args.max_pages)

    if listings:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(listings, f, ensure_ascii=False, indent=4)
        logger.info(f"Scraped {len(listings)} detailed listings and saved to {args.output}")
    else:
        logger.warning("No listings were found or scraped.")

if __name__ == "__main__":
    main()