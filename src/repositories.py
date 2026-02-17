from abc import ABC, abstractmethod
from src.services import ScraperService
from typing import List, Optional

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
    def get_all_page_urls(self, start_url: str, max_pages: Optional[int] = None) -> List[str]:
        pass

    @abstractmethod
    def scrape_page(self, url):
        pass

    @abstractmethod
    def scrape_listing_details(self, url):
        pass


class ZonapropRepository(ListingRepository):
    """
    `ListingRepository` implementation for Zonaprop.

    Encapsulates all Zonaprop-specific URL discovery and HTML parsing
    required to build `Listing` objects from search result and detail pages.
    """

    def __init__(self, scraper_service: ScraperService):
        self.scraper_service = scraper_service

    def get_all_page_urls(self, start_url: str, max_pages: Optional[int] = None) -> List[str]:
        """
        Discover all pagination URLs starting from the given Zonaprop URL.

        Follows the "next page" links until either there are no more pages
        or the optional `max_pages` limit is reached.

        Args:
            start_url: URL of the first Zonaprop results page.
            max_pages: Optional maximum number of pages to include.

        Returns:
            List of strings with absolute URLs for each discovered page.
        """
        logger.info(f"Getting page URLs starting from: {start_url}")
        page_urls = [start_url]
        current_url = start_url
        page_num = 1

        while current_url:

            # Break if we reached the max pages limit
            if max_pages is not None and page_num >= max_pages:
                logger.info(f"Reached max pages limit: {max_pages}")
                break

            response = self.scraper_service.rate_limited_request(current_url, headers={'User-Agent': 'Mozilla/5.0'})
            if not response:
                logger.warning(f"Failed to get response from {current_url}")
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
                logger.info("No more pages found")
                break

        logger.info(f"Found a total of {len(page_urls)} pages")
        return page_urls

    def scrape_page(self, url):
        """
        Scrape all listing cards from a single Zonaprop results page.

        For each card, this method builds a base `Listing` object using
        summary information and then enriches it by fetching the detail page.

        Args:
            url: Absolute URL of the Zonaprop results page.

        Returns:
            List of fully-populated `Listing` instances.
        """
        logger.info(f"Scraping page: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # Make a request to the results page
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
                # Extract the listing URL from the listing container
                listing_url = f"https://www.zonaprop.com.ar{safe_extract(listing, 'a', 'href')}"
                id_match = re.search(r'-(\d+)\.html$', listing_url)
                listing_id = id_match.group(1) if id_match else None

                # Build the listing object with the base information
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

                # Scrape additional information from the listing detail page
                detailed_info = self.scrape_listing_details(item.url)

                # Update the listing object with the additional information
                item.update_details(detailed_info)

                # Add the listing object to the list of listings
                listings.append(item)

                logger.info(f"Successfully processed listing {index} with ID {listing_id}")
            except Exception as e:
                logger.error(f"Error parsing listing {index}: {e}")

        return listings

    def scrape_listing_details(self, url):
        """
        Scrape additional feature and publisher information for a listing.

        This fetches the individual listing detail page to extract structured data.

        Args:
            url: Absolute URL of the listing detail page.

        Returns:
            Dictionary with extra attributes to update a `Listing`.
        """
        logger.info(f"Scraping detailed listing from: {url}")

        # Make a request to the listing page
        response = self.scraper_service.rate_limited_request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        if not response:
            logger.warning(f"No response received for listing: {url}")
            return {}

        soup = BeautifulSoup(response.content, 'html.parser')
        details = {}

        # Extract information from the listing page
        details.update(self._extract_feature_information(soup))
        details.update(self._extract_publisher_information(soup))

        logger.info(f"Finished scraping details for listing: {url}")
        return details

    def _extract_feature_information(self, soup):
        """
        Extract structured feature information from a listing detail page.

        Args:
            soup: BeautifulSoup instance of the listing detail HTML.

        Returns:
            Dictionary mapping feature names to values.
        """
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

            # Extract the feature information by iterating over the icon_to_attr dictionary
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
        """
        Extract publisher metadata embedded in inline JavaScript.

        Args:
            soup: BeautifulSoup instance of the listing detail HTML.

        Returns:
            Dictionary with publisher-related fields.
        """
        details = {}
        script_tags = soup.find_all('script')

        # Extract the publisher data by iterating over the script tags
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
