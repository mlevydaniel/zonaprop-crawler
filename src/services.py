import requests
import logging
import time
import random
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

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
