from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.table import Table
from rich.status import Status
from rich.theme import Theme
from rich.padding import Padding
from rich.columns import Columns
import sys
import time

# Custom Theme for a professional look
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "august": "bold bright_blue",
    "user": "bold magenta",
    "system": "dim white",
    "action": "bold yellow",
    "data": "italic grey70",
})

console = Console(theme=custom_theme)

class AugustInterface:
    def __init__(self):
        self.console = console
        self._status = None

    def startup_banner(self):
        banner_art = r"""
 █████╗ ██╗   ██╗ ██████╗ ██╗   ██╗███████╗████████╗
██╔══██╗██║   ██║██╔════╝ ██║   ██║██╔════╝╚══██╔══╝
███████║██║   ██║██║  ███╗██║   ██║███████╗   ██║   
██╔══██║██║   ██║██║   ██║██║   ██║╚════██║   ██║   
██║  ██║╚██████╔╝╚██████╔╝╚██████╔╝███████║   ██║   
╚═╝  ╚═╝ ╚═════╝  ╚═════╝  ╚═════╝  ╚══════╝   ╚═╝   
        """
        self.console.print("\n")
        self.console.print(Panel(
            Text(banner_art, style="august"),
            title="[system]v2.0.0[/system]",
            subtitle="[action]SYSTEM ONLINE[/action]",
            border_style="august",
            expand=False,
            padding=(0, 2)
        ))
        
        self.console.print("[system]Initializing secure connection...[/system]")
        time.sleep(0.3)
        self.console.print("[system]Loading G-Suite modules: Google Applications[/system]")
        time.sleep(0.3)
        self.console.print("[success]Core directives active. Voice sensors calibrated.[/success]")
        self.console.print("[dim white]Shortcuts: [bold cyan]'L'[/bold cyan] Logout | [bold cyan]'H'[/bold cyan] Clear Cache/Responses[/dim white]\n")

    def log_system(self, message):
        self.console.print(f"[system][{time.strftime('%H:%M:%S')}] {message}[/system]")

    def log_success(self, message):
        self.console.print(f"[success]✔ {message}[/success]")

    def log_error(self, message):
        self.console.print(f"[error]✘ {message}[/error]")

    def log_action(self, func_name, args):
        self.stop_thinking()
        table = Table(show_header=False, box=None, padding=(0, 1))
        # table.add_column("Key", style="dim")
        # table.add_column("Value", style="white")
        
        for k, v in args.items():
            table.add_row(Text(f"  {k}:", style="dim"), Text(str(v), style="white"))
        
        self.console.print(Panel(
            table,
            title=f"[action]EXECUTING: {func_name}[/action]",
            border_style="yellow",
            expand=False
        ))

    def show_thinking(self, text=None):
        self.stop_thinking()
        
        status_text = "August is processing..."
        if text:
            # truncate long text
            if len(text) > 50:
                text = text[:47] + "..."
            status_text = f"Analyzing: [italic]\"{text}\"[/italic]"
            
        self._status = self.console.status(status_text, spinner="aesthetic")
        self._status.start()

    def stop_thinking(self):
        if hasattr(self, '_status') and self._status:
            try:
                self._status.stop()
            except Exception:
                pass
            self._status = None

    def user_heard(self, text):
        self.stop_thinking()
        # Only show if not empty
        if text.strip():
            self.console.print(Padding(
                Panel(
                    Text(text, style="white"),
                    title="[user]USER[/user]",
                    border_style="magenta",
                    expand=False
                ),
                (0, 0, 0, 2)
            ))

    def assistant_response(self, text):
        self.stop_thinking()
        self.console.print(Panel(
            Text(text, style="bright_white"),
            title="[august]AUGUST[/august]",
            border_style="bright_blue",
            padding=(1, 2)
        ))

    def waiting(self):
        self.stop_thinking()
        self.console.print("[system]Listening... (Ambient Mode)[/system]")

    def clear(self):
        self.console.clear()
