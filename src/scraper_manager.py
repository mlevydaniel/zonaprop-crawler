import logging
from src.repositories import ListingRepository
from src.models import Listing
from typing import List, Optional

logger = logging.getLogger(__name__)


class ScraperManager:
    """
    Orchestrates the scraping process across multiple pages.

    This class coordinates the retrieval of all listing page URLs from
    the repository, then iterates through each page to scrape the listings
    and aggregate the results.
    """

    def __init__(self, repository: ListingRepository):
        self.repository = repository

    def scrape(self, start_url: str, max_pages: Optional[int] = None) -> List[Listing]:

        # Get all page URLs from the repository
        page_urls = self.repository.get_all_page_urls(start_url, max_pages)
        all_listings = []

        # Iterate through each page to scrape the listings and aggregate the results
        for page_num, page_url in enumerate(page_urls, start=1):
            logger.info(f"Scraping page {page_num} of {len(page_urls)}")
            page_listings = self.repository.scrape_page(page_url)
            all_listings.extend(page_listings)

        return all_listings
