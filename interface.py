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

from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import ANSI
from io import StringIO

console = Console(theme=custom_theme, force_terminal=True, color_system="standard", soft_wrap=True)

class AugustInterface:
    def __init__(self):
        self.console = console
        self._status = None
        self.hybrid_mode = False

    def _safe_print(self, content):
        """Prints content safely, handling prompt-toolkit redirection if active."""
        if self.hybrid_mode:
            # Capture Rich output to a string with ANSI codes
            with StringIO() as buf:
                temp_console = Console(file=buf, theme=custom_theme, force_terminal=True, color_system="standard", width=80)
                temp_console.print(content)
                text = buf.getvalue().strip()
                # Use prompt-toolkit's ANSI printer to ensure codes are interpreted correctly
                print_formatted_text(ANSI(text))
        else:
            self.console.print(content)


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
        self._safe_print(Panel(
            Text(banner_art, style="august"),
            title="[system]v2.0.0[/system]",
            subtitle="[action]SYSTEM ONLINE[/action]",
            border_style="august",
            expand=False,
            padding=(0, 2)
        ))

        
        self._safe_print("[system]Initializing secure connection...[/system]")
        # time.sleep(0.3)
        self._safe_print("[system]Loading G-Suite modules: Google Applications[/system]")
        # time.sleep(0.3)
        self._safe_print("[success]Core directives active. Hybrid input sensors calibrated.[/success]")
        self._safe_print("[dim white]Type commands or speak freely. Use [bold cyan]'/logout'[/bold cyan] or [bold cyan]'/clear'[/bold cyan] for maintenance.[/dim white]\n")


    def log_system(self, message):
        self._safe_print(f"[system][{time.strftime('%H:%M:%S')}] {message}[/system]")


    def log_success(self, message):
        self._safe_print(f"[success]✔ {message}[/success]")

    def log_error(self, message):
        self._safe_print(f"[error]✘ {message}[/error]")


    def log_action(self, func_name, args):
        self.stop_thinking()
        table = Table(show_header=False, box=None, padding=(0, 1))
        # table.add_column("Key", style="dim")
        # table.add_column("Value", style="white")
        
        for k, v in args.items():
            table.add_row(Text(f"  {k}:", style="dim"), Text(str(v), style="white"))
        
        self._safe_print(Panel(
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
            truncated_text = text[:47] + "..." if len(text) > 50 else text
            status_text = f"Analyzing: [italic]\"{truncated_text}\"[/italic]"
            
        # Simplified static status to avoid ANSI junk with prompt_toolkit session
        self._safe_print(f"[success]▰▰▰▰▰▰▰[/success] {status_text}")


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
            self._safe_print(Padding(
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
        self._safe_print(Panel(
            Text(text, style="bright_white"),
            title="[august]AUGUST[/august]",
            border_style="bright_blue",
            padding=(1, 2),
            expand=False
        ))

    def waiting(self):
        self.stop_thinking()
        self._safe_print("\n[success]⦿ MICROPHONE ACTIVE[/success] [system]| Dual Input Mode Online[/system]")



    def clear(self):
        self.console.clear()
