"""
User Interface and Interactive Wizard for LeadScraper.
Designed for non-technical users with clean prompts, live tables,
and zero-configuration auto-export.
"""

import asyncio
import sys
from typing import List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from lead_scraper.models import Lead
from lead_scraper.core import LeadScraper
from lead_scraper.exporter import export_leads

console = Console()


def show_banner():
    """Renders the friendly terminal header banner."""
    console.print(
        Panel(
            "[bold cyan]⚡ LEADSCRAPER FALCON ⚡[/bold cyan]\n"
            "[white]High-Speed Lead Collection Powered by Milli-Scrapes[/white]\n"
            "[dim]Sub-second V8 extraction • Anti-Bot auto-consent • Zero search waste[/dim]",
            border_style="cyan",
            expand=False,
        )
    )


def show_lead_table(leads: List[Lead]):
    """Displays a clean summary table of extracted leads."""
    if not leads:
        console.print("[yellow]No leads extracted.[/yellow]")
        return

    table = Table(title="[bold green]Extracted Business Leads[/bold green]", border_style="dim")
    table.add_column("#", style="dim", width=4)
    table.add_column("Business Name", style="bold cyan")
    table.add_column("Website", style="blue")
    table.add_column("Email", style="green")
    table.add_column("Phone", style="magenta")
    table.add_column("Socials", style="yellow")
    table.add_column("Quality", justify="right", style="bold")

    for i, lead in enumerate(leads, 1):
        email_str = lead.emails[0] if lead.emails else "[dim]None[/dim]"
        phone_str = lead.phones[0] if lead.phones else "[dim]None[/dim]"
        social_count = len(lead.social_media)
        social_str = f"{social_count} handles" if social_count else "[dim]None[/dim]"
        score_pct = f"{int(lead.confidence_score * 100)}%"
        
        table.add_row(
            str(i),
            lead.business_name,
            lead.website or "[dim]N/A[/dim]",
            email_str,
            phone_str,
            social_str,
            score_pct,
        )

    console.print(table)


def show_export_summary(paths: dict):
    """Displays the exact local output file paths clearly."""
    console.print(
        Panel(
            f"[bold green]✔ All leads saved locally in 3 formats:[/bold green]\n\n"
            f"[bold cyan]📄 JSON:[/bold cyan]  {paths['json']}\n"
            f"[bold cyan]📊 CSV:[/bold cyan]   {paths['csv']}\n"
            f"[bold cyan]📝 TXT:[/bold cyan]   {paths['txt']}\n\n"
            f"[dim]Tip: You can double-click or open these files anytime.[/dim]",
            title="[bold white]Export Location[/bold white]",
            border_style="green",
        )
    )


async def run_interactive_wizard():
    """Runs the 3-template interactive wizard for non-coders."""
    show_banner()

    console.print("\n[bold]Select an extraction template:[/bold]")
    console.print(" [bold cyan]1[/bold cyan] » Direct Website Extraction [dim](Provide a specific website URL)[/dim]")
    console.print(" [bold cyan]2[/bold cyan] » Named Business [dim](Provide business name & optional location)[/dim]")
    console.print(" [bold cyan]3[/bold cyan] » Dynamic Discovery [dim](Provide category, location, and quantity)[/dim]")
    console.print(" [bold cyan]0[/bold cyan] » Exit\n")

    choice = Prompt.ask("[bold yellow]Enter your choice[/bold yellow]", choices=["1", "2", "3", "0"], default="3")

    if choice == "0":
        console.print("[dim]Goodbye![/dim]")
        return

    leads: List[Lead] = []
    scraper = LeadScraper()

    try:
        # Template 1: Direct Website
        if choice == "1":
            url = Prompt.ask("\n[bold]Enter Website URL[/bold] (e.g. https://bluebottlecoffee.com)")
            if not url.strip():
                console.print("[red]Invalid URL provided.[/red]")
                return

            with console.status("[cyan]Extracting lead via Milli-Scrapes...[/cyan]"):
                lead = await scraper.scrape_website(url.strip())
                leads = [lead]

        # Template 2: Named Business
        elif choice == "2":
            name = Prompt.ask("\n[bold]Enter Business Name[/bold] (e.g. Tartine Bakery)")
            loc = Prompt.ask("[bold]Enter Location / City (optional)[/bold]", default="")

            with console.status(f"[cyan]Finding official website and extracting {name}...[/cyan]"):
                lead = await scraper.scrape_named_business(name.strip(), location=loc.strip() or None)
                leads = [lead]

        # Template 3: Dynamic Category & Location
        elif choice == "3":
            category = Prompt.ask("\n[bold]Enter Business Category[/bold] (e.g. Dentist, Bakery, Plumber)")
            location = Prompt.ask("[bold]Enter Location / City / Country[/bold] (e.g. Austin TX, London, Tokyo)")
            quantity = IntPrompt.ask("[bold]How many leads do you want?[/bold]", default=10)

            console.print(f"\n[cyan]Starting dynamic discovery for {quantity} {category}s in {location}...[/cyan]")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                scrape_task = progress.add_task(f"Extracting {quantity} leads...", total=quantity)

                def on_progress(completed: int, total: int, current_lead: Lead):
                    progress.update(
                        scrape_task,
                        completed=completed,
                        description=f"[green]Scraped:[/green] {current_lead.business_name[:25]}",
                    )

                leads = await scraper.discover_and_scrape(
                    category=category.strip(),
                    location=location.strip(),
                    quantity=quantity,
                    on_progress=on_progress,
                )

        # Display results
        console.print()
        show_lead_table(leads)

        # Auto-Export
        if leads:
            output_paths = export_leads(leads)
            console.print()
            show_export_summary(output_paths)

    finally:
        await scraper.close()
