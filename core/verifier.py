import aiohttp
import asyncio
import certifi
import ssl
import random
from urllib.parse import urlparse, urlunparse
from .logger import Logger
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import undetected_chromedriver as uc

class URLVerifier:
    def __init__(self, timeout, max_retries, concurrency, valid_status_codes, logger: Logger, use_get_fallback=False, disable_ssl_verification=False, scraper=None):
        self.timeout = timeout
        self.max_retries = max_retries
        self.semaphore = asyncio.Semaphore(concurrency)
        self.valid_status_codes = valid_status_codes
        self.logger = logger
        self.use_get_fallback = use_get_fallback
        self.disable_ssl_verification = disable_ssl_verification
        self.scraper = scraper
        self.session = None
        self.failure_counts = {"connection": 0, "ssl": 0, "status": 0, "timeout": 0, "client": 0, "other": 0}
        self.total_urls = 0
        self.successful_urls = 0
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0"
        ]
        if disable_ssl_verification:
            self.logger.warning("SSL verification is disabled globally. Use with caution.")

    async def __aenter__(self):
        ssl_context = None if self.disable_ssl_verification else ssl.create_default_context(cafile=certifi.where())
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        headers = {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": "https://www.google.com/",
            "DNT": "1",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Dest": "document",
            "Upgrade-Insecure-Requests": "1"
        }
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout), connector=connector, headers=headers)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()
            self.session = None
        self.logger.info(f"Summary: Total URLs: {self.total_urls}, Successful: {self.successful_urls}, "
                         f"Connection failures: {self.failure_counts['connection']}, "
                         f"SSL failures: {self.failure_counts['ssl']}, "
                         f"Status failures: {self.failure_counts['status']}, "
                         f"Timeout failures: {self.failure_counts['timeout']}, "
                         f"Client failures: {self.failure_counts['client']}, "
                         f"Other failures: {self.failure_counts['other']}")

    def normalize_url(self, url):
        """Add scheme if missing and normalize URL."""
        if not url:
            return None
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        parsed = urlparse(url)
        return urlunparse(parsed._replace(fragment=''))

    async def check_url_selenium(self, url):
        """Check URL using Selenium with undetected-chromedriver."""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument(f"user-agent={random.choice(self.user_agents)}")
            driver = uc.Chrome(options=chrome_options, enable_cdp_events=True)
            try:
                driver.get(url)
                await asyncio.sleep(3)  # Wait for page load
                page_source = driver.page_source
                if any(code in page_source for code in ["200", "301", "302"]) or ("<title>" in page_source and ("X" in driver.title or "Twitter" in driver.title)):
                    self.logger.success(f"{url} — OK (Selenium fallback)")
                    return True
                else:
                    self.logger.error(f"{url} — Failed: Invalid page content (Selenium fallback)")
                    return False
            finally:
                driver.quit()
        except Exception as e:
            self.logger.error(f"{url} — Failed: Selenium Fallback Error ({str(e)})")
            return False

    async def check_url(self, url, output_writer):
        """Check URL status with retries, HEAD-to-GET fallback, SSL fallback, cloudscraper fallback, and selenium fallback."""
        url = self.normalize_url(url)
        if not url:
            self.logger.error(f"Invalid URL: {url}")
            self.failure_counts["other"] += 1
            self.total_urls += 1
            await output_writer.write_not_working(url)
            return

        self.total_urls += 1
        for attempt in range(self.max_retries + 1):
            async with self.semaphore:
                try:
                    async with self.session.head(url, allow_redirects=True) as response:
                        status = response.status
                        if status in self.valid_status_codes:
                            self.logger.success(f"{url} — {status} OK")
                            self.successful_urls += 1
                            await output_writer.write_working(url)
                            return
                        elif status in [400, 403] and self.use_get_fallback:
                            try:
                                async with self.session.get(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=self.timeout + 4)) as get_response:
                                    status = get_response.status
                                    if status in self.valid_status_codes:
                                        self.logger.success(f"{url} — {status} OK (GET fallback)")
                                        self.successful_urls += 1
                                        await output_writer.write_working(url)
                                        return
                                    elif status == 400 and attempt < self.max_retries:
                                        self.logger.warning(f"Retrying {url} (Attempt {attempt + 1}/{self.max_retries}) — 400 Error (GET)")
                                        await asyncio.sleep(2)
                                        continue
                                    else:
                                        self.logger.error(f"{url} — {status} Failed (GET fallback)")
                                        self.failure_counts["status"] += 1
                                        await output_writer.write_not_working(url)
                                        return
                            except asyncio.TimeoutError:
                                if attempt < self.max_retries:
                                    self.logger.warning(f"Retrying {url} (Attempt {attempt + 1}/{self.max_retries}) — Timeout Error (GET)")
                                    await asyncio.sleep(2)
                                else:
                                    self.logger.error(f"{url} — Failed: Timeout Error (GET)")
                                    self.failure_counts["timeout"] += 1
                                    await output_writer.write_not_working(url)
                                    return
                        else:
                            self.logger.error(f"{url} — {status} Failed")
                            self.failure_counts["status"] += 1
                            await output_writer.write_not_working(url)
                            return
                except aiohttp.ClientSSLError as e:
                    if attempt < self.max_retries:
                        self.logger.warning(f"Retrying {url} (Attempt {attempt + 1}/{self.max_retries}) — SSL Error")
                        await asyncio.sleep(2)
                    else:
                        self.logger.warning(f"Attempting {url} with SSL verification disabled")
                        try:
                            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout), connector=aiohttp.TCPConnector(ssl=False), headers={
                                "User-Agent": random.choice(self.user_agents),
                                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                                "Accept-Language": "en-US,en;q=0.5",
                                "Accept-Encoding": "gzip, deflate, br",
                                "Connection": "keep-alive",
                                "Referer": "https://www.google.com/",
                                "DNT": "1",
                                "Sec-Fetch-Site": "none",
                                "Sec-Fetch-Mode": "navigate",
                                "Sec-Fetch-Dest": "document",
                                "Upgrade-Insecure-Requests": "1"
                            }) as temp_session:
                                async with temp_session.head(url, allow_redirects=True) as response:
                                    status = response.status
                                    if status in self.valid_status_codes:
                                        self.logger.success(f"{url} — {status} OK (SSL fallback)")
                                        self.successful_urls += 1
                                        await output_writer.write_working(url)
                                        return
                                    elif status in [400, 403] and self.use_get_fallback:
                                        async with temp_session.get(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=self.timeout + 4)) as get_response:
                                            status = get_response.status
                                            if status in self.valid_status_codes:
                                                self.logger.success(f"{url} — {status} OK (GET and SSL fallback)")
                                                self.successful_urls += 1
                                                await output_writer.write_working(url)
                                                return
                                            else:
                                                self.logger.error(f"{url} — {status} Failed (GET and SSL fallback)")
                                                self.failure_counts["status"] += 1
                                                await output_writer.write_not_working(url)
                                                return
                                    else:
                                        self.logger.error(f"{url} — {status} Failed (SSL fallback)")
                                        self.failure_counts["status"] += 1
                                        await output_writer.write_not_working(url)
                                        return
                        except (aiohttp.ClientSSLError, aiohttp.ClientConnectionError, asyncio.TimeoutError, aiohttp.ClientError) as e:
                            self.logger.error(f"{url} — Failed: SSL Fallback Error ({str(e)})")
                            self.failure_counts["ssl"] += 1
                            await output_writer.write_not_working(url)
                            return
                except aiohttp.ClientConnectionError as e:
                    if attempt < self.max_retries:
                        self.logger.warning(f"Retrying {url} (Attempt {attempt + 1}/{self.max_retries}) — Connection Error")
                        await asyncio.sleep(2)
                    else:
                        self.logger.error(f"{url} — Failed: Connection Error ({str(e)})")
                        self.failure_counts["connection"] += 1
                        await output_writer.write_not_working(url)
                        return
                except asyncio.TimeoutError as e:
                    if attempt < self.max_retries:
                        self.logger.warning(f"Retrying {url} (Attempt {attempt + 1}/{self.max_retries}) — Timeout Error")
                        await asyncio.sleep(2)
                    else:
                        self.logger.error(f"{url} — Failed: Timeout Error")
                        self.failure_counts["timeout"] += 1
                        await output_writer.write_not_working(url)
                        return
                except aiohttp.ClientError as e:
                    if attempt < self.max_retries:
                        self.logger.warning(f"Retrying {url} (Attempt {attempt + 1}/{self.max_retries}) — Client Error")
                        await asyncio.sleep(2)
                    else:
                        self.logger.warning(f"Attempting {url} with cloudscraper fallback")
                        await asyncio.sleep(3)  # Increased delay
                        try:
                            response = await asyncio.get_event_loop().run_in_executor(None, lambda: self.scraper.get(url, allow_redirects=True))
                            status = response.status_code
                            if status in self.valid_status_codes:
                                self.logger.success(f"{url} — {status} OK (Cloudscraper fallback)")
                                self.successful_urls += 1
                                await output_writer.write_working(url)
                                return
                            elif status == 403:
                                self.logger.warning(f"Retrying {url} with alternate cloudscraper headers")
                                try:
                                    alternate_headers = {
                                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/91.0",
                                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                                        "Accept-Language": "en-US,en;q=0.5",
                                        "Accept-Encoding": "gzip, deflate, br",
                                        "Connection": "keep-alive",
                                        "Referer": "https://www.bing.com/",
                                        "DNT": "1",
                                        "Sec-Fetch-Site": "none",
                                        "Sec-Fetch-Mode": "navigate",
                                        "Sec-Fetch-Dest": "document",
                                        "Upgrade-Insecure-Requests": "1"
                                    }
                                    response = await asyncio.get_event_loop().run_in_executor(None, lambda: self.scraper.get(url, headers=alternate_headers, allow_redirects=True))
                                    status = response.status_code
                                    if status in self.valid_status_codes:
                                        self.logger.success(f"{url} — {status} OK (Cloudscraper alternate fallback)")
                                        self.successful_urls += 1
                                        await output_writer.write_working(url)
                                        return
                                    else:
                                        self.logger.error(f"{url} — {status} Failed (Cloudscraper alternate fallback)")
                                        self.failure_counts["status"] += 1
                                        await output_writer.write_not_working(url)
                                        return
                                except Exception as e:
                                    self.logger.error(f"{url} — Failed: Cloudscraper Alternate Fallback Error ({str(e)})")
                                    self.failure_counts["client"] += 1
                                    await output_writer.write_not_working(url)
                                    return
                            else:
                                self.logger.error(f"{url} — {status} Failed (Cloudscraper fallback)")
                                self.failure_counts["status"] += 1
                                # Attempt Selenium fallback
                                self.logger.warning(f"Attempting {url} with selenium fallback")
                                success = await self.check_url_selenium(url)
                                if success:
                                    self.successful_urls += 1
                                    await output_writer.write_working(url)
                                else:
                                    self.failure_counts["client"] += 1
                                    await output_writer.write_not_working(url)
                                return
                        except Exception as e:
                            self.logger.error(f"{url} — Failed: Cloudscraper Fallback Error ({str(e)})")
                            self.failure_counts["client"] += 1
                            # Attempt Selenium fallback
                            self.logger.warning(f"Attempting {url} with selenium fallback")
                            success = await self.check_url_selenium(url)
                            if success:
                                self.successful_urls += 1
                                await output_writer.write_working(url)
                            else:
                                self.failure_counts["client"] += 1
                                await output_writer.write_not_working(url)
                            return

    async def process_urls(self, urls, output_writer):
        """Process a chunk of URLs concurrently."""
        tasks = [self.check_url(url.strip(), output_writer) for url in urls if url.strip()]
        await asyncio.gather(*tasks)