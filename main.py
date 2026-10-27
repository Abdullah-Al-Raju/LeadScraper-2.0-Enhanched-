"""
LeadScraper Falcon: Main Entry Point.
Supports both non-technical interactive wizard and automated CLI arguments.
"""

import argparse
import asyncio
import sys
from typing import List
from rich.console import Console

from lead_scraper.models import Lead
from lead_scraper.core import LeadScraper
from lead_scraper.exporter import export_leads
from lead_scraper.ui import run_interactive_wizard, show_lead_table, show_export_summary

# Windows Proactor Event Loop compatibility
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

console = Console()


async def async_main():
    """Parses arguments or starts the interactive wizard."""
    parser = argparse.ArgumentParser(
        description="⚡ LeadScraper Falcon: Pure Milli-First Lead Collection Engine"
    )
    
    # Template 1
    parser.add_argument("--url", help="Direct website URL to extract lead from (Template 1)")
    
    # Template 2
    parser.add_argument("--name", help="Specific business name to extract (Template 2)")
    
    # Template 3
    parser.add_argument("--category", help="Business category for dynamic discovery (Template 3)")
    parser.add_argument("--location", help="Target location (city, state, or country)")
    parser.add_argument("--quantity", type=int, default=10, help="Number of leads to extract (default: 10)")
    
    # Concurrency
    parser.add_argument("--concurrency", type=int, default=5, help="Concurrent extraction workers (default: 5)")

    args = parser.parse_args()

    # If no CLI arguments provided, run the friendly interactive wizard
    if not (args.url or args.name or (args.category and args.location)):
        await run_interactive_wizard()
        return

    # Headless / CLI Execution Mode
    leads: List[Lead] = []
    scraper = LeadScraper()

    try:
        if args.url:
            console.print(f"[cyan]Scraping direct URL:[/cyan] {args.url}")
            lead = await scraper.scrape_website(args.url)
            leads = [lead]

        elif args.name:
            console.print(f"[cyan]Scraping named business:[/cyan] {args.name} in {args.location or 'Global'}")
            lead = await scraper.scrape_named_business(args.name, location=args.location)
            leads = [lead]

        elif args.category and args.location:
            console.print(
                f"[cyan]Discovering {args.quantity} {args.category} leads in {args.location}...[/cyan]"
            )
            leads = await scraper.discover_and_scrape(
                category=args.category,
                location=args.location,
                quantity=args.quantity,
                max_concurrency=args.concurrency,
            )

        show_lead_table(leads)
        if leads:
            output_paths = export_leads(leads)
            show_export_summary(output_paths)

    finally:
        await scraper.close()


def main():
    """Main synchronous entry point."""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Execution error:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
