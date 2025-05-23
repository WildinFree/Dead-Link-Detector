from rich.console import Console
from rich.theme import Theme

class Logger:
    def __init__(self):
        self.console = Console(theme=Theme({
            "success": "green",
            "error": "red",
            "warning": "yellow",
            "info": "blue"
        }))

    def success(self, message):
        self.console.print(f"[✓] {message}", style="success")

    def error(self, message):
        self.console.print(f"[✗] {message}", style="error")

    def warning(self, message):
        self.console.print(f"[!] {message}", style="warning")

    def info(self, message):
        self.console.print(f"[*] {message}", style="info")