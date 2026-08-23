"""
Professional Terminal Display Module
Beautiful, clean terminal output using rich library
NO EMOJIS - Pure professional design
WINDOWS-SAFE: ASCII-only characters (no Unicode box-drawing)
"""

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich import box

# Global console instance
console = Console()


def print_banner():
    """Display startup banner - Windows-safe ASCII version"""
    banner = """
+===================================================+
|                                                   |
|           LeadScraper AI Agent v2.0              |
|       Intelligent Business Discovery              |
|                                                   |
+===================================================+
    """
    console.print(banner, style="bold cyan")


def success(message):
    """Print success message in green"""
    console.print(f"[SUCCESS] {message}", style="bold green")


def warning(message):
    """Print warning message in yellow"""
    console.print(f"[WARNING] {message}", style="bold yellow")


def error(message):
    """Print error message in red"""
    console.print(f"[ERROR] {message}", style="bold red")


def ai(message):
    """Print AI operation message in cyan"""
    console.print(f"[AI] {message}", style="bold cyan")


def info(message):
    """Print info message in white"""
    console.print(f"[INFO] {message}", style="white")


def section_header(title):
    """Print section header"""
    console.print(f"\n{'=' * 60}", style="bold blue")
    console.print(f"{title}", style="bold blue")
    console.print(f"{'=' * 60}", style="bold blue")


def create_progress_bar(description="Processing"):
    """
    Create a progress bar

    Returns:
        Progress object
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("{task.completed}/{task.total}"),
        TimeRemainingColumn(),
        console=console
    )


def create_status_panel(phase, business, progress, model, elapsed, eta):
    """
    Create live status panel

    Args:
        phase: Current phase
        business: Current business name
        progress: Progress string (e.g., "7/10 (70%)")
        model: Current AI model
        elapsed: Elapsed time
        eta: Estimated time remaining

    Returns:
        Panel object
    """
    content = f"""[bold]Phase:[/bold]     {phase}
[bold]Business:[/bold]  {business}
[bold]Progress:[/bold]  {progress}
[bold]Model:[/bold]     {model}
[bold]Elapsed:[/bold]   {elapsed}
[bold]ETA:[/bold]       {eta}"""

    return Panel(
        content,
        title="Current Operation",
        border_style="cyan",
        box=box.ROUNDED
    )


def create_results_table(results):
    """
    Create results summary table

    Args:
        results: List of dicts with keys: name, phone, email, confidence

    Returns:
        Table object
    """
    table = Table(
        title="Extraction Results",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )

    table.add_column(
        "Business Name",
        style="white",
        no_wrap=False,
        max_width=30)
    table.add_column("Phone", justify="center", style="white")
    table.add_column("Email", justify="center", style="white")
    table.add_column("Confidence", justify="right", style="white")

    for r in results:
        phone_status = "[green]YES[/green]" if r.get(
            'phone') else "[red]NO[/red]"
        email_status = "[green]YES[/green]" if r.get(
            'email') else "[red]NO[/red]"

        # Color code confidence
        conf = r.get('confidence', 0)
        if conf >= 80:
            conf_str = f"[green]{conf}%[/green]"
        elif conf >= 60:
            conf_str = f"[yellow]{conf}%[/yellow]"
        else:
            conf_str = f"[red]{conf}%[/red]"

        table.add_row(
            r.get('name', 'Unknown'),
            phone_status,
            email_status,
            conf_str
        )

    return table


def print_summary_box(total, success, partial, failed, total_time, avg_time):
    """
    Print final statistics box - Windows-safe ASCII version

    Args:
        total: Total processed
        success: Success count
        partial: Partial count
        failed: Failed count
        total_time: Total time string
        avg_time: Average time string
    """
    success_pct = success * 100 // total if total else 0
    partial_pct = partial * 100 // total if total else 0
    failed_pct = failed * 100 // total if total else 0

    summary = f"""
+===================================================+
|              EXTRACTION COMPLETE                  |
+---------------------------------------------------+
|  Total Processed:     {total:<27} |
|  Success:            {success} ({success_pct}%){' ' * 20} |
|  Partial:            {partial} ({partial_pct}%){' ' * 20} |
|  Failed:             {failed} ({failed_pct}%){' ' * 20} |
|  Total Time:          {total_time:<26} |
|  Avg per Business:    {avg_time:<26} |
+===================================================+
    """
    console.print(summary, style="bold green")


def print_divider():
    """Print a simple divider - Windows-safe"""
    console.print("-" * 60, style="dim")


def print_completion_separator(number, total=None):
    """
    Print beautiful 3-line completion separator - Windows-safe

    Args:
        number: Item number just completed
        total: Total items (optional)

    Example output:
        ------------------------------------------------------------
        --------------------------- 3/10 ---------------------------
        ------------------------------------------------------------
    """
    line = "-" * 60

    if total:
        center_text = f" {number}/{total} "
    else:
        center_text = f" {number} "

    # Calculate padding
    text_len = len(center_text)
    total_len = 60
    left_pad = (total_len - text_len) // 2
    right_pad = total_len - text_len - left_pad

    middle_line = "-" * left_pad + center_text + "-" * right_pad

    console.print()
    console.print(line, style="dim cyan")
    console.print(middle_line, style="bold cyan")
    console.print(line, style="dim cyan")
    console.print()


# Spinner for long operations
def spinner(message, style="cyan"):
    """
    Context manager for spinner

    Usage:
        with spinner("Processing..."):
            # do work
    """
    from rich.spinner import Spinner

    class SpinnerContext:
        def __enter__(self):
            self.live = Live(
                Spinner(
                    "dots",
                    text=message,
                    style=style),
                console=console)
            self.live.start()
            return self

        def __exit__(self, *args):
            self.live.stop()

    return SpinnerContext()
