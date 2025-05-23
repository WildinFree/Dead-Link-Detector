import asyncio
import argparse
import yaml
from core.verifier import URLVerifier
from core.chunk_reader import ChunkReader
from core.output_writer import OutputWriter
from core.result_folder import ResultFolder
from core.logger import Logger
from rich.progress import Progress
import sys
import cloudscraper
import logging

async def main():
    parser = argparse.ArgumentParser(description="UltraLinkVerifier: Validate massive URL lists.")
    parser.add_argument("--input", default="urls.txt", help="Input file with URLs")
    parser.add_argument("--output", default="results/", help="Output directory")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # Configure logging
    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
        logging.getLogger("cloudscraper").setLevel(logging.DEBUG)
        logging.getLogger("aiohttp").setLevel(logging.DEBUG)
        logging.getLogger("selenium").setLevel(logging.DEBUG)
        logging.getLogger("undetected_chromedriver").setLevel(logging.DEBUG)

    # Load config
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    # Initialize components
    logger = Logger()
    result_folder = ResultFolder(args.output)
    output_dir = result_folder.create()
    output_writer = OutputWriter(output_dir)
    chunk_reader = ChunkReader(args.input, config['chunk_size'])
    scraper = cloudscraper.create_scraper(browser={"browser": "chrome", "platform": "windows", "mobile": False})
    verifier = URLVerifier(
        config['timeout'],
        config['max_retries'],
        config['concurrency'],
        config['status_codes'],
        logger,
        use_get_fallback=config.get('use_get_fallback', False),
        disable_ssl_verification=config.get('disable_ssl_verification', False),
        scraper=scraper
    )

    logger.info("Starting UltraLinkVerifier...")
    with Progress() as progress:
        task = progress.add_task("[cyan]Processing URLs...", total=None)
        async with output_writer:
            async with verifier:
                async for chunk in chunk_reader.read_chunks():
                    await verifier.process_urls(chunk, output_writer)
                    progress.update(task, advance=len(chunk))
    logger.info("Processing complete.")

if __name__ == "__main__":
    # Set event loop policy for Windows to avoid ProactorEventLoop issues
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Create and run event loop explicitly
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()