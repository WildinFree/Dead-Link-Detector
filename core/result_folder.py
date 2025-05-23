from pathlib import Path
from datetime import datetime

class ResultFolder:
    def __init__(self, base_path):
        self.base_path = Path(base_path)

    def create(self):
        """Create timestamped output folder."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = self.base_path / f"output_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir