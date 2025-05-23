import asyncio
from core.verifier import URLVerifier
from core.logger import Logger
from core.output_writer import OutputWriter
from pathlib import Path

async def test_verifier():
    logger = Logger()
    output_writer = OutputWriter(Path("test_output"))
    verifier = URLVerifier(timeout=4, max_retries=2, concurrency=10, valid_status_codes=[200, 301, 302], logger=logger)
    urls = ["https://google.com", "https://nonexistent123456789.com"]
    await verifier.process_urls(urls, output_writer)

if __name__ == "__main__":
    asyncio.run(test_verifier())