import aiofiles
import asyncio
from pathlib import Path

class OutputWriter:
    def __init__(self, output_dir):
        self.working_file = Path(output_dir) / "working.txt"
        self.notworking_file = Path(output_dir) / "notworking.txt"
        self.lock = asyncio.Lock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def write_working(self, url):
        """Write to working.txt thread-safely."""
        async with self.lock:
            async with aiofiles.open(self.working_file, 'a', encoding='utf-8') as f:
                await f.write(f"{url}\n")

    async def write_not_working(self, url):
        """Write to notworking.txt thread-safely."""
        async with self.lock:
            async with aiofiles.open(self.notworking_file, 'a', encoding='utf-8') as f:
                await f.write(f"{url}\n")