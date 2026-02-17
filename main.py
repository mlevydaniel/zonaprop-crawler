import argparse
import json
import logging
from src.scraper_manager import ScraperManager
from src.repositories import ZonapropRepository
from src.services import ScraperService


# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """
    Command-line entry point for the Zonaprop scraping tool.

    This function parses CLI arguments, wires up the scraping components
    (`ScraperService`, `ZonapropRepository`, `ScraperManager`), runs the
    scraping process and persists the results to a JSON file.

    CLI arguments:
        --max_pages: Maximum number of result pages to traverse.
        --output: Name of the output JSON file.
        --url: Initial listings URL to start scraping from.
    """

    parser = argparse.ArgumentParser(description='Scrape Zonaprop listings.')
    parser.add_argument('--max_pages', type=int, default=2, help='Maximum number of pages to scrape')
    parser.add_argument('--output', type=str, default='zonaprop_caballito_rentals.json', help='Output JSON file name')
    parser.add_argument('--url', type=str, default='https://www.zonaprop.com.ar/casas-departamentos-ph-alquiler-caballito.html', help='Starting URL for scraping')
    args = parser.parse_args()

    logger.info(f"Starting scraping process with max_pages={args.max_pages}, output={args.output}, url={args.url}")

    scraper_service = ScraperService()
    repository = ZonapropRepository(scraper_service)
    manager = ScraperManager(repository)

    listings = manager.scrape(args.url, max_pages=args.max_pages)

    if listings:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump([listing.to_dict() for listing in listings], f, ensure_ascii=False, indent=4)
        logger.info(f"Scraped {len(listings)} listings and saved to {args.output}")
    else:
        logger.warning("No listings were found or scraped.")

    logger.info("Scraping process completed")


if __name__ == "__main__":
    main()
