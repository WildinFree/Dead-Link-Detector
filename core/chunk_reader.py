class ChunkReader:
    def __init__(self, input_file, chunk_size):
        self.input_file = input_file
        self.chunk_size = chunk_size

    async def read_chunks(self):
        """Stream-read URLs in chunks."""
        with open(self.input_file, 'r', encoding='utf-8') as f:
            chunk = []
            for line in f:
                chunk.append(line.strip())
                if len(chunk) >= self.chunk_size:
                    yield chunk
                    chunk = []
            if chunk:
                yield chunk