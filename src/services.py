import requests
import logging
import time
import random
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class ScraperService:
    """
    Low-level HTTP client for the scraper with retries and rate limiting.

    This service wraps a `requests.Session` configured with automatic
    retries and adds a random delay before each outbound request to
    reduce the risk of being rate-limited by the remote server.
    """
    def __init__(self):
        self.session = self.create_session_with_retries()

    @staticmethod
    def create_session_with_retries():
        """
        Create and configure a `requests.Session` with retry behavior.

        Returns:
            A `requests.Session` instance that will automatically retry
            failed requests for a subset of 5xx HTTP status codes.
        """
        session = requests.Session()
        retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        session.mount('https://', HTTPAdapter(max_retries=retries))
        return session

    def rate_limited_request(self, url, headers):
        """
        Perform a GET request respecting a random delay and retry policy.

        Args:
            url: Absolute URL to fetch.
            headers: Dictionary of HTTP headers to send with the request.

        Returns:
            A `requests.Response` object on success, or `None` if the
            request ultimately fails even after retries.
        """
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
