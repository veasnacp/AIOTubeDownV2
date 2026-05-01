import json
import logging
import random
import time
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

import cloudscraper
import requests
from fake_useragent import UserAgent
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class AdvancedCloudScraper:
    """
    Advanced CloudScraper wrapper with comprehensive features for bypassing anti-bot protection
    """

    def __init__(self,
                 browser: str = 'chrome',
                 platform: str = 'windows',
                 desktop: bool = True,
                 timeout: int = 30,
                 retries: int = 3,
                 delay_range: tuple = (1, 3),
                 use_fake_ua: bool = True,
                 custom_headers: Optional[Dict] = None,
                 proxies: Optional[Dict] = None,
                 session_persistence: bool = True,
                 verify_ssl: bool = True):
        """
        Initialize the Advanced CloudScraper

        Args:
            browser: Browser type ('chrome', 'firefox', 'safari', 'edge')
            platform: Platform ('windows', 'mac', 'linux', 'android', 'ios')
            desktop: Whether to use desktop or mobile user agent
            timeout: Request timeout in seconds
            retries: Number of retry attempts
            delay_range: Range of delays between retries (min, max) in seconds
            use_fake_ua: Whether to use fake user agent
            custom_headers: Custom headers to add to requests
            proxies: Proxy configuration
            session_persistence: Whether to maintain session across requests
            verify_ssl: Whether to verify SSL certificates
        """
        self.browser = browser
        self.platform = platform
        self.desktop = desktop
        self.timeout = timeout
        self.retries = retries
        self.delay_range = delay_range
        self.use_fake_ua = use_fake_ua
        self.custom_headers = custom_headers or {}
        self.proxies = proxies
        self.session_persistence = session_persistence
        self.verify_ssl = verify_ssl

        # Initialize logging
        self.logger = logging.getLogger(__name__)
        self.setup_logging()

        # Initialize fake user agent generator
        self.ua = UserAgent() if use_fake_ua else None

        # Initialize scraper
        self.scraper = None
        self.session = None
        self.init_scraper()

        # Request statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'retry_count': 0
        }

    def setup_logging(self, level=logging.INFO):
        """Setup logging configuration"""
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(level)

    def init_scraper(self):
        """Initialize the cloudscraper with configured settings"""
        scraper_config = {
            'browser': {
                'browser': self.browser,
                'platform': self.platform,
                'desktop': self.desktop
            }
        }

        try:
            self.scraper = cloudscraper.create_scraper(**scraper_config)

            # Configure retry strategy
            retry_strategy = Retry(
                total=self.retries,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self.scraper.mount("http://", adapter)
            self.scraper.mount("https://", adapter)

            # Set default headers
            self._setup_headers()

            # Set proxies if provided
            if self.proxies:
                self.scraper.proxies.update(self.proxies)

            # Configure SSL verification
            self.scraper.verify = self.verify_ssl

            self.logger.info("CloudScraper initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize scraper: {str(e)}")
            raise

    def _setup_headers(self):
        """Setup default headers for requests"""
        default_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

        # Add fake user agent if enabled
        if self.use_fake_ua and self.ua:
            default_headers['User-Agent'] = self.ua.random

        # Merge with custom headers
        default_headers.update(self.custom_headers)
        self.scraper.headers.update(default_headers)

    def update_user_agent(self):
        """Update the user agent to a random one"""
        if self.use_fake_ua and self.ua:
            new_ua = self.ua.random
            self.scraper.headers.update({'User-Agent': new_ua})
            self.logger.debug(f"Updated User-Agent to: {new_ua}")

    def rotate_proxy(self, new_proxy: Dict[str, str]):
        """Rotate to a new proxy"""
        self.proxies = new_proxy
        if self.scraper:
            self.scraper.proxies.clear()
            self.scraper.proxies.update(new_proxy)
            self.logger.info("Proxy rotated successfully")

    def _delay(self):
        """Add random delay between retries"""
        delay = random.uniform(*self.delay_range)
        time.sleep(delay)

    def _update_stats(self, success: bool, retry_attempted: bool = False):
        """Update request statistics"""
        self.stats['total_requests'] += 1
        if success:
            self.stats['successful_requests'] += 1
        else:
            self.stats['failed_requests'] += 1
        if retry_attempted:
            self.stats['retry_count'] += 1

    def get(self, url: str, params: Optional[Dict] = None,
            headers: Optional[Dict] = None, **kwargs) -> Optional[requests.Response]:
        """
        Perform GET request with retry mechanism

        Args:
            url: Target URL
            params: Query parameters
            headers: Additional headers
            **kwargs: Additional arguments for requests

        Returns:
            Response object or None if failed
        """
        for attempt in range(self.retries):
            try:
                # Update user agent periodically
                if attempt > 0 and self.use_fake_ua:
                    self.update_user_agent()

                # Merge headers
                request_headers = self.scraper.headers.copy()
                if headers:
                    request_headers.update(headers)

                # Make request
                response = self.scraper.get(
                    url,
                    params=params,
                    headers=request_headers,
                    timeout=self.timeout,
                    **kwargs
                )

                response.raise_for_status()
                self._update_stats(success=True)
                self.logger.info(f"GET request successful: {url}")
                return response

            except cloudscraper.exceptions.CloudflareChallengeError as e:
                self.logger.warning(
                    f"Cloudflare challenge failed (attempt {attempt + 1}/{self.retries}): {str(e)}")
                self._update_stats(success=False, retry_attempted=attempt > 0)

                if attempt < self.retries - 1:
                    self._delay()
                    continue

            except requests.exceptions.RequestException as e:
                self.logger.warning(
                    f"Request failed (attempt {attempt + 1}/{self.retries}): {str(e)}")
                self._update_stats(success=False, retry_attempted=attempt > 0)

                if attempt < self.retries - 1:
                    self._delay()
                    continue

            except Exception as e:
                self.logger.error(f"Unexpected error: {str(e)}")
                self._update_stats(success=False)
                return None

        self.logger.error(f"All retries failed for URL: {url}")
        return None

    def post(self, url: str, data: Optional[Dict] = None,
             json_data: Optional[Dict] = None, headers: Optional[Dict] = None,
             **kwargs) -> Optional[requests.Response]:
        """
        Perform POST request with retry mechanism
        """
        for attempt in range(self.retries):
            try:
                if attempt > 0 and self.use_fake_ua:
                    self.update_user_agent()

                request_headers = self.scraper.headers.copy()
                if headers:
                    request_headers.update(headers)

                response = self.scraper.post(
                    url,
                    data=data,
                    json=json_data,
                    headers=request_headers,
                    timeout=self.timeout,
                    **kwargs
                )

                response.raise_for_status()
                self._update_stats(success=True)
                self.logger.info(f"POST request successful: {url}")
                return response

            except Exception as e:
                self.logger.warning(
                    f"POST failed (attempt {attempt + 1}/{self.retries}): {str(e)}")
                self._update_stats(success=False, retry_attempted=attempt > 0)

                if attempt < self.retries - 1:
                    self._delay()
                    continue

        self.logger.error(f"All POST retries failed for URL: {url}")
        return None

    def get_json(self, url: str, params: Optional[Dict] = None, **kwargs) -> Optional[Dict]:
        """
        Perform GET request and return JSON response
        """
        response = self.get(url, params=params, **kwargs)
        if response and response.status_code == 200:
            try:
                return response.json()
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON: {str(e)}")
                return None
        return None

    def download_file(self, url: str, filepath: str, chunk_size: int = 8192) -> bool:
        """
        Download a file from URL

        Args:
            url: File URL
            filepath: Local path to save file
            chunk_size: Download chunk size

        Returns:
            Boolean indicating success
        """
        try:
            response = self.get(url, stream=True)
            if not response:
                return False

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)

            self.logger.info(f"File downloaded successfully: {filepath}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to download file: {str(e)}")
            return False

    def get_session(self):
        """Get or create a persistent session"""
        if not self.session_persistence:
            return self.scraper

        if not self.session:
            self.session = requests.Session()
            # Copy headers and proxies
            self.session.headers.update(self.scraper.headers)
            if self.proxies:
                self.session.proxies.update(self.proxies)

        return self.session

    def get_stats(self) -> Dict:
        """Get request statistics"""
        return self.stats.copy()

    def reset_stats(self):
        """Reset request statistics"""
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'retry_count': 0
        }

    def close(self):
        """Close the scraper session"""
        if self.scraper:
            self.scraper.close()
        if self.session:
            self.session.close()
        self.logger.info("Scraper closed successfully")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# Usage example and configuration presets
class CloudScraperPresets:
    """Pre-configured presets for common use cases"""

    @staticmethod
    def mobile_scraper():
        """Mobile browser configuration"""
        return AdvancedCloudScraper(
            browser='chrome',
            platform='android',
            desktop=False,
            use_fake_ua=True,
            timeout=25
        )

    @staticmethod
    def stealth_scraper():
        """Stealth configuration for hard-to-scrape sites"""
        return AdvancedCloudScraper(
            browser='chrome',
            platform='windows',
            desktop=True,
            use_fake_ua=True,
            delay_range=(2, 5),
            retries=5,
            custom_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="120"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
            }
        )

    @staticmethod
    def high_performance_scraper():
        """High performance configuration for fast scraping"""
        return AdvancedCloudScraper(
            browser='chrome',
            platform='linux',
            desktop=True,
            timeout=10,
            retries=2,
            delay_range=(0.5, 1),
            use_fake_ua=False
        )


# Example usage
if __name__ == "__main__":
    url = 'https://www.shortmovs.com/m/wodexiongdijiaofengxian/1.html'
    # Make a request
    headers = {
        "Referer": "https://www.shortmovs.com/",
        "Origin": "https://www.shortmovs.com"
    }
    # Example: Using presets
    with CloudScraperPresets.stealth_scraper() as scraper:
        scraper.setup_logging()
        response = scraper.get(url, headers=headers)
        if response:
            with open('__test2.html', 'w', encoding='utf-8') as f:
                f.write(response.text)

    # Example 3: Get JSON data
    # json_data = scraper.get_json('https://api.github.com/repos/python/cpython')
    # if json_data:
    #     print(f"Repository: {json_data.get('full_name')}")

    # Example 4: Check statistics
    print(f"Statistics: {scraper.get_stats()}")

    # Close the scraper
    scraper.close()
