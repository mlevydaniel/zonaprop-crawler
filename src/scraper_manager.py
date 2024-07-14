import logging

logger = logging.getLogger(__name__)

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
