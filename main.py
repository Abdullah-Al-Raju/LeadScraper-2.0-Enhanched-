"""
LeadScraper Falcon - Main Pipeline Orchestrator
Automated local business contact finder
"""

import sys
import argparse
import time
import asyncio

# Windows asyncio event loop initialization
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

import config
from modules.utils import logger, calculate_completeness, ProgressTracker
from modules.sheets import (
    connect_to_sheet, get_unprocessed_rows, update_status,
    write_to_output, is_duplicate, load_existing_results,
    initialize_input_sheet, initialize_output_sheet
)
from modules.search import search_for_website, validate_search_setup
from modules.crawler import crawl_website
from modules.extractor import extract_contacts
from modules import display
from modules.cache import ProgressCache


# ============================================================
# MAIN PIPELINE
# ============================================================

def run_pipeline():
    """
    Main pipeline execution
    Reads from Google Sheet, processes each row, writes results
    """
    # Start stopwatch
    start_time = time.time()
    
    display.section_header("LeadScraper Falcon Pipeline Starting")
    
    # Validate configuration
    if not _validate_config():
        display.error("Configuration validation failed. Exiting.")
        return
    
    # Validate search
    display.info("Validating search setup...")
    if not validate_search_setup():
        display.error("Search validation failed. Exiting.")
        return
    
    display.success("Search validation successful")
    
    try:
        # Connect to Google Sheet
        logger.info("Connecting to Google Sheet...")
        sheet = connect_to_sheet()
        
        # Initialize sheets if needed
        initialize_input_sheet(sheet)
        initialize_output_sheet(sheet)
        
        # Load existing results for duplicate detection
        load_existing_results(sheet)
        
        # Get unprocessed rows
        logger.info("Fetching unprocessed rows...")
        rows = get_unprocessed_rows(sheet)
        
        if not rows:
            logger.info("No unprocessed rows found. Exiting.")
            return
        
        logger.info(f"Found {len(rows)} rows to process")
        
        # ===== PROGRESS CACHE (NEW!) =====
        cache = ProgressCache()
        
        # Check for cached progress
        if cache.exists():
            display.info("Found cached progress - checking if resume available...")
            cached_data = cache.load()
            completed_rows = cache.get_completed_rows()
            
            if completed_rows:
                display.success(f"Can resume from {len(completed_rows)} completed items!")
                # Filter out already completed rows
                rows = [r for r in rows if r['row_number'] not in completed_rows]
                display.info(f"Remaining to process: {len(rows)} items")
        
        # ===== ASYNC MODE (NEW - SPEED!) =====
        try:
            from modules.async_config import ENABLE_ASYNC
            use_async = ENABLE_ASYNC
        except:
            use_async = False
        
        if use_async:
            # ===== ASYNC PIPELINE (10x FASTER!) =====
            display.success("ASYNC MODE ENABLED - Processing at HIGH SPEED!")
            
            # Run async pipeline
            import asyncio
            from modules.async_pipeline import run_pipeline_async
            
            stats = asyncio.run(run_pipeline_async(sheet, rows, cache))
            
            # Clear cache on success
            cache.clear()
            display.success("All businesses processed successfully - cache cleared!")
            
            # Show stopwatch
            total_time = time.time() - start_time
            minutes = int(total_time // 60)
            seconds = int(total_time % 60)
            display.success(f"Total execution time: {minutes}m {seconds}s")
            logger.info(f"Total execution time: {minutes} minutes, {seconds} seconds")
            
            return  # IMPORTANT: Don't run sync mode after async succeeds!
            
        else:
            # ===== SYNC PIPELINE (Original) =====
            display.info("Running in SYNC mode (slower but stable)")
        
        # ===== CHECK FOR DISCOVERY MODE =====
        if not use_async and config.ENABLE_DISCOVERY_MODE and _is_discovery_mode(rows):
            logger.info("DISCOVERY MODE DETECTED")
            
            # Extract discovery parameters from first row
            location = rows[0]['city']
            category = rows[0].get('category', 'business') or 'business'
            quantity = config.DEFAULT_DISCOVERY_QUANTITY
            
            logger.info(f"Starting discovery: {quantity} {category}s in {location}")
            
            # Discover businesses
            from modules.discovery import discover_businesses
            discovered = discover_businesses(location, quantity, category)
            
            if not discovered:
                logger.warning("No businesses discovered")
                return
            
            logger.info(f"Discovered {len(discovered)} businesses with contact info")
            
            # Auto-manage sheets
            if config.AUTO_CLEAR_INPUT_ON_DISCOVERY:
                from modules.sheets import clear_input_sheet, populate_input_sheet
                clear_input_sheet(sheet)
                populate_input_sheet(sheet, discovered)
            
            # Reload rows
            rows = get_unprocessed_rows(sheet)
            logger.info(f"Proceeding to process {len(rows)} discovered businesses")
        
        # Initialize progress tracker
        progress = ProgressTracker(len(rows))
        
        # Statistics
        stats = {
            'total': len(rows),
            'success': 0,
            'partial': 0,
            'no_website': 0,
            'crawl_failed': 0,
            'extraction_failed': 0,
            'duplicates': 0
        }
        
        # Process each row
        for row in rows:
            process_business(sheet, row, progress, stats, cache)
        
        # Finish
        progress.finish()
        
        # Clear cache on successful completion
        cache.clear()
        display.success("All businesses processed successfully - cache cleared!")
        
        # Auto-cleanup results
        if config.AUTO_DEDUPLICATE_RESULTS:
            logger.info("Auto-deduplicating results...")
            from modules.sheets import deduplicate_results
            deduplicate_results(sheet)
        
        if config.AUTO_SORT_RESULTS:
            logger.info("Auto-sorting results by confidence...")
            from modules.sheets import sort_results_by_confidence
            sort_results_by_confidence(sheet)
        
        _print_summary(stats)
        
        # Calculate total time
        total_time = time.time() - start_time
        minutes = int(total_time // 60)
        seconds = int(total_time % 60)
        
        logger.info("="*60)
        logger.info("LeadScraper Falcon Pipeline Completed")
        logger.info("="*60)
        display.success(f"Total execution time: {minutes}m {seconds}s")
        logger.info(f"Total execution time: {minutes} minutes, {seconds} seconds")
        
    except KeyboardInterrupt:
        logger.warning("\nPipeline interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        sys.exit(1)


def process_business(sheet, row, progress, stats, cache=None):
    """
    Process a single business using multi-source intelligence
    
    Args:
        sheet: Google Sheet object
        row: Row data dictionary
        progress: Progress tracker
        stats: Statistics dictionary
    """
    row_number = row['row_number']
    category = row.get('category', '')
    business_name = row.get('business_name', '')
    search_term = row.get('search_term', business_name)  # What we'll actually search for
    city = row['city']
    
    # Display what we're searching for
    display_name = category if category else business_name
    logger.info(f"\n--- Processing: {display_name} ({city}) ---")
    
    try:
        # Check for duplicate (use actual business name if we have it, otherwise search term)
        dup_check_name = business_name if business_name else search_term
        if is_duplicate(dup_check_name, city):
            update_status(sheet, row_number, "[DUPLICATE]")
            stats['duplicates'] += 1
            progress.update("Duplicate")
            return
        
        # Update status to processing
        update_status(sheet, row_number, config.STATUS_PROCESSING)
        
        # ===== MULTI-SOURCE DISCOVERY =====
        logger.info("Step 1: Multi-Source Discovery...")
        
        from modules.search import search_multi_source
        source_urls = search_multi_source(search_term, city, category)
        
        # Check if we found anything
        found_sources = [k for k, v in source_urls.items() if v]
        if not found_sources:
            update_status(sheet, row_number, config.STATUS_NO_WEBSITE)
            stats['no_website'] += 1
            progress.update("No sources found")
            return
        
        logger.info(f"Found {len(found_sources)} sources: {', '.join(found_sources)}")
        
        # ===== MULTI-SOURCE EXTRACTION =====
        logger.info("Step 2: Extracting from all sources...")
        
        sources_data = []
        
        # Extract from general search results (phones in snippets)
        try:
            from modules.sources.search_result_extractor import extract_from_search_results
            search_data = extract_from_search_results(search_term, city, category)
            if search_data:
                sources_data.append(search_data)
                logger.info(f"Search results extraction successful")
        except Exception as e:
            logger.warning(f"Search results extraction failed: {e}")
        
        # Extract from Facebook search (snippet + URL)
        if source_urls.get('facebook'):
            try:
                from modules.sources.search_result_extractor import extract_from_social_search
                fb_data = extract_from_social_search(search_term, city, 'facebook')
                if fb_data:
                    sources_data.append(fb_data)
                    logger.info(f"Facebook search extraction successful")
            except Exception as e:
                logger.warning(f"Facebook search extraction failed: {e}")
        
        # Extract from Instagram search (snippet + URL)
        if source_urls.get('instagram'):
            try:
                from modules.sources.search_result_extractor import extract_from_social_search
                ig_data = extract_from_social_search(search_term, city, 'instagram')
                if ig_data:
                    sources_data.append(ig_data)
                    logger.info(f"Instagram search extraction successful")
            except Exception as e:
                logger.warning(f"Instagram search extraction failed: {e}")
        
        # Extract from website if found
        if source_urls.get('website'):
            try:
                # Check if it's a directory site
                from modules.sources.directory_extractor import is_extractable_directory, extract_from_directory
                
                is_dir, dir_type = is_extractable_directory(source_urls['website'])
                
                if is_dir:
                    # Extract FROM the directory
                    logger.info(f"Found {dir_type} directory - extracting...")
                    dir_data = extract_from_directory(source_urls['website'], dir_type)
                    if dir_data:
                        sources_data.append(dir_data)
                        logger.info(f"Directory extraction successful")
                else:
                    # Normal website crawling
                    logger.info("Crawling traditional website...")
                    crawl_data = crawl_website(source_urls['website'])
                    
                    if crawl_data:
                        # Extract with category-aware AI
                        website_contacts = extract_contacts(crawl_data, category=category)
                        if website_contacts:
                            website_contacts['source_type'] = 'website'
                            website_contacts['website'] = source_urls['website']
                            sources_data.append(website_contacts)
                            logger.info(f"Website extraction successful")
                    else:
                        logger.warning("Website crawl failed")
                        
            except Exception as e:
                logger.error(f"Website processing error: {e}")
        
        # Check if we got any data
        if not sources_data:
            update_status(sheet, row_number, config.STATUS_EXTRACTION_FAILED)
            stats['extraction_failed'] += 1
            progress.update("Extraction failed")
            return
        
        # ===== DATA FUSION =====
        logger.info(f"Step 3: Fusing data from {len(sources_data)} sources...")

        
        from modules.fusion import merge_multi_source_data
        contacts = merge_multi_source_data(sources_data)
        
        if not contacts:
            update_status(sheet, row_number, config.STATUS_EXTRACTION_FAILED)
            stats['extraction_failed'] += 1
            progress.update("Fusion failed")
            return
        
        # Set business name if not extracted (AI should extract the real name from website)
        if not contacts.get('business_name'):
            # Use search_term as fallback, but AI should have found the real name
            contacts['business_name'] = search_term
        
        # Set website if not already set
        if not contacts.get('website') and source_urls.get('website'):
            contacts['website'] = source_urls['website']
        
        # Calculate completeness (for backward compatibility)
        completeness = calculate_completeness(contacts)
        confidence = contacts.get('confidence_score', 0)
        
        logger.info(f"Results:")
        logger.info(f"  - Business: {contacts.get('business_name', 'Unknown')}")
        logger.info(f"  - Phones: {len(contacts.get('phone_numbers', []))}")
        logger.info(f"  - Emails: {len(contacts.get('email_addresses', []))}")
        logger.info(f"  - Address: {'Yes' if contacts.get('street_address') else 'No'}")
        logger.info(f"  - Confidence: {confidence}%")
        logger.info(f"  - Sources: {', '.join(contacts.get('sources_used', []))}")
        logger.info(f"  - Verified: {', '.join(contacts.get('verified_fields', []))}")
        
        # Step 4: Write to output
        write_to_output(sheet, contacts)
        
        # Show beautiful completion separator
        display.print_completion_separator(progress.current, progress.total)
        
        # Update status based on confidence score
        if confidence >= 80:
            update_status(sheet, row_number, "[DONE] High Confidence")
            stats['success'] += 1
            progress.update("Done")
        elif confidence >= 60:
            update_status(sheet, row_number, "[DONE]")
            stats['success'] += 1
            progress.update("Done")
        else:
            update_status(sheet, row_number, config.STATUS_PARTIAL)
            stats['partial'] += 1
            progress.update("Partial")
        
        # ===== SAVE PROGRESS (NEW!) =====
        if cache:
            cache.add_completed_row(row_number)
        
    except Exception as e:
        logger.error(f"Error processing {display_name}: {e}", exc_info=True)
        error_msg = f"[ERROR] {str(e)[:50]}"
        update_status(sheet, row_number, error_msg)
        progress.update("Error")



# ============================================================
# VALIDATION
# ============================================================

def _validate_config(require_sheets=True):
    """
    Validate configuration
    
    Args:
        require_sheets: Whether Google Sheets setup is strictly required
        
    Returns:
        Boolean indicating if config is valid
    """
    valid = True
    
    if require_sheets:
        if not config.GOOGLE_SHEET_ID:
            logger.error("GOOGLE_SHEET_ID not set in .env. Run with --local or --output to operate standalone without Google Sheets.")
            valid = False
        
        if not config.SERVICE_ACCOUNT_FILE or not os.path.exists(config.SERVICE_ACCOUNT_FILE):
            logger.error(f"SERVICE_ACCOUNT_FILE ({config.SERVICE_ACCOUNT_FILE}) not found. Run with --local or --output to operate standalone.")
            valid = False
    
    return valid


# ============================================================
# STATISTICS
# ============================================================

def _print_summary(stats):
    """Print summary statistics"""
    logger.info("\n" + "="*60)
    logger.info("SUMMARY STATISTICS")
    logger.info("="*60)
    logger.info(f"Total Processed:     {stats['total']}")
    logger.info(f"  [SUCCESS] Success:        {stats['success']} ({stats['success']/stats['total']*100:.1f}%)")
    logger.info(f"  [PARTIAL] Partial:        {stats['partial']} ({stats['partial']/stats['total']*100:.1f}%)")
    logger.info(f"  [FAILED]  No Website:     {stats['no_website']} ({stats['no_website']/stats['total']*100:.1f}%)")
    logger.info(f"  [FAILED]  Crawl Failed:   {stats['crawl_failed']} ({stats['crawl_failed']/stats['total']*100:.1f}%)")
    logger.info(f"  [FAILED]  Extract Failed: {stats['extraction_failed']} ({stats['extraction_failed']/stats['total']*100:.1f}%)")
    logger.info(f"  [INFO]    Duplicates:     {stats['duplicates']}")
    logger.info("="*60)


def _is_discovery_mode(rows):
    """
    Detect if we're in discovery mode
    
    Discovery mode when:
    - Input has only 1 row
    - Category is empty OR generic (restaurant, cafe, etc.)
    - Location is present
    """
    if not rows or len(rows) != 1:
        return False
    
    row = rows[0]
    category = row.get('category', '').strip().lower()
    business_name = row.get('business_name', '').strip()
    location = row.get('city', '').strip()
    
    if not location:
        return False
    
    # Generic terms trigger discovery
    generic_terms = ['restaurant', 'cafe', 'food', 'dining', 'eatery', 'bistro', 'bar']
    
    if not business_name and category:
        return True
    
    if category in generic_terms:
        return True
    
    return False


# ============================================================
# ENTRY POINT & STANDALONE CLI RUNNERS
# ============================================================

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description='LeadScraper Falcon - Intelligent Business Discovery & Extraction (Milli-Enhanced)'
    )
    
    parser.add_argument(
        '--discover',
        type=str,
        help='Discovery mode: location to search (e.g., "Dhaka, Bangladesh")'
    )
    
    parser.add_argument(
        '--quantity',
        type=int,
        default=getattr(config, 'DEFAULT_DISCOVERY_QUANTITY', 10),
        help='Number of businesses to find (default: 10)'
    )
    
    parser.add_argument(
        '--category',
        type=str,
        default='business',
        help='Business category (default: business, e.g., plumber, dentist, coffee, saas, restaurant)'
    )

    parser.add_argument(
        '--url',
        type=str,
        help='Direct URL mode: Scrape and extract contacts directly from website URL'
    )

    parser.add_argument(
        '--business',
        type=str,
        help='Direct business mode: Search and extract a single business by name'
    )

    parser.add_argument(
        '--city',
        type=str,
        default='',
        help='City/location filter for business search'
    )

    parser.add_argument(
        '--local',
        action='store_true',
        help='Run in local mode without requiring Google Sheets'
    )

    parser.add_argument(
        '--output',
        type=str,
        help='Output file path (.csv or .json) for local exports'
    )

    parser.add_argument(
        '--no-milli',
        action='store_true',
        help='Disable Milli Universal Scraper and use fallback HTTPX'
    )

    parser.add_argument(
        '--ai',
        action='store_true',
        help='Force enable OpenRouter AI free auto-router tier'
    )

    parser.add_argument(
        '--no-ai',
        action='store_true',
        help='Disable OpenRouter AI tier even if OPENROUTER_API_KEY is configured'
    )
    
    return parser.parse_args()


async def _async_scrape_direct_url(url: str, category: str = "", force_milli: bool = True):
    from urllib.parse import urlparse
    from modules.crawler import crawl_website
    from modules.extractor import extract_contacts
    from modules.utils import calculate_completeness
    
    crawl_data = await crawl_website(url, force_milli=force_milli)
    if not crawl_data:
        return None
        
    contacts = extract_contacts(crawl_data, category=category) or {}
    contacts['website'] = url
    domain_name = urlparse(url).netloc.replace('www.', '').split('.')[0].title()
    comp = calculate_completeness(contacts)
    contacts['completeness_score'] = comp
    contacts['confidence_score'] = int(comp * 100) if comp <= 1.0 else int(comp)
    contacts['sources_used'] = [crawl_data.get('engine_used', 'milli_universal')]
    return contacts


async def _async_scrape_single_business(business_name: str, city: str = "", category: str = "", force_milli: bool = True):
    from modules.search import search_for_website
    from modules.sources.search_result_extractor import extract_from_search_results, extract_from_social_search
    from modules.fusion import merge_multi_source_data
    from modules.crawler import crawl_website
    from modules.extractor import extract_contacts
    from modules.utils import calculate_completeness
    
    loop = asyncio.get_event_loop()
    sources_data = []
    website_url = None
    
    # 1. Search snippet extraction (captures snippets, phone, email, address, and official site)
    try:
        search_contacts = await loop.run_in_executor(None, extract_from_search_results, business_name, city, category)
        if search_contacts:
            sources_data.append(search_contacts)
            if search_contacts.get('website'):
                website_url = search_contacts['website']
    except Exception as e:
        logger.debug(f"Search snippet extraction: {e}")
        
    # 2. Search for official website only if not found in snippets
    if not website_url:
        display.info(f"Searching official website for: {business_name} ({city})...")
        website_url = await search_for_website(business_name, city)
        
    # 3. Crawl website with Milli
    if website_url:
        display.info(f"Found website: {website_url}. Crawling with Milli...")
        crawl_data = await crawl_website(website_url, force_milli=force_milli)
        if crawl_data:
            contacts = extract_contacts(crawl_data, category=category) or {}
            contacts['source_type'] = 'website'
            contacts['website'] = website_url
            sources_data.append(contacts)
            
    # 4. Social search (Facebook) only if not already discovered
    if not any(s.get('facebook') for s in sources_data):
        try:
            fb_contacts = await loop.run_in_executor(None, extract_from_social_search, business_name, city, 'facebook')
            if fb_contacts:
                sources_data.append(fb_contacts)
        except Exception:
            pass
            
    if not sources_data:
        return {'business_name': business_name, 'city': city, 'confidence_score': 0}
        
    merged = merge_multi_source_data(sources_data)
    merged['business_name'] = business_name
    merged['city'] = city
    merged['category'] = category
    if website_url and not merged.get('website'):
        merged['website'] = website_url
    merged['completeness_score'] = calculate_completeness(merged)
    return merged


def run_cli_discovery(location, quantity, category, local_mode=False, output_file=None, force_milli=True):
    """
    Run discovery mode from CLI. Supports both Google Sheets and Local Export.
    """
    from modules.discovery import discover_businesses
    from modules.local_exporter import export_to_csv, export_to_json, print_lead_summary
    
    cat_label = category or "business"
    display.section_header(f"DISCOVERY MODE: {quantity} {cat_label}s in {location}")
    display.ai(f"Discovering {quantity} {cat_label}s...")
    
    businesses = discover_businesses(location, quantity, category)
    if not businesses:
        display.error("Discovery failed - no businesses found")
        sys.exit(1)
        
    display.success(f"Discovered {len(businesses)} businesses!")

    if local_mode or output_file:
        display.info("Running local extraction with Milli...")
        leads = []
        for idx, item in enumerate(businesses, 1):
            name = item.get('name') or item.get('business_name') or item.get('search_term')
            city = item.get('city') or location
            display.info(f"[{idx}/{len(businesses)}] Processing: {name} ({city})")
            lead = asyncio.run(_async_scrape_single_business(name, city=city, category=category, force_milli=force_milli))
            if lead:
                leads.append(lead)
                print_lead_summary(lead)
            if idx < len(businesses):
                time.sleep(1.0)
                
        if output_file:
            if output_file.endswith('.csv'):
                export_to_csv(leads, output_file)
            elif output_file.endswith('.txt'):
                export_to_txt(leads, output_file)
            else:
                export_to_json(leads, output_file)
            display.section_header(f"SUCCESS: {len(leads)} leads exported to {output_file}")
        else:
            from modules.local_exporter import export_all_formats
            saved = export_all_formats(leads)
            print("\n" + "=" * 65)
            print(f"  🎉 SUCCESS: {len(leads)} leads exported to your machine!")
            print("=" * 65)
            print(f"  📁 Excel / Sheets (CSV):  {saved['csv']}")
            print(f"  📁 Structured Data (JSON): {saved['json']}")
            print(f"  📁 Human-Readable Report:  {saved['txt']}")
            print("=" * 65)
        return
        
    # Google Sheets mode
    from modules.sheets import clear_input_sheet, populate_input_sheet
    display.info("Connecting to Google Sheet...")
    workbook = connect_to_sheet()
    
    if config.AUTO_CLEAR_INPUT_ON_DISCOVERY:
        display.info("Clearing input sheet for fresh start...")
        clear_input_sheet(workbook)
        
    display.info(f"Populating input sheet with {len(businesses)} businesses...")
    populate_input_sheet(workbook, businesses)
    display.section_header(f"DISCOVERY COMPLETE: {len(businesses)} businesses added")
    run_pipeline()


def interactive_menu():
    """Interactive guided wizard for users who prefer not to use CLI commands."""
    display.print_banner()
    display.info("Engine: Milli Universal V8 Hyper-Reflex (Integrated Core Engine)")
    
    from modules.ai_manager import ai_manager
    if ai_manager.is_available() and getattr(config, 'ENABLE_AI_FALLBACK', True):
        display.info(f"AI Tier: OpenRouter Free Auto-Router ({config.OPENROUTER_MODEL})")
    else:
        display.info("AI Tier: Standalone Deterministic Mode ($0 Cost)")

    print("\n" + "=" * 65)
    print("  SELECT AN EXTRACTION TEMPLATE:")
    print("=" * 65)
    print("  [1] Direct Website Extraction")
    print("      -> Provide a website link (e.g. https://example.com)")
    print("  [2] Named Business Search")
    print("      -> Provide a business name and location (e.g. Joe's Bakery, Austin)")
    print("  [3] Dynamic Business Discovery")
    print("      -> Provide a country/city, category, and quantity of leads")
    print("  [4] Exit")
    print("=" * 65)

    choice = ""
    while choice not in ('1', '2', '3', '4'):
        choice = input("\n👉 Choose template [1-4]: ").strip()

    if choice == '4':
        print("\nExiting. Have a great day!")
        sys.exit(0)

    from modules.local_exporter import print_lead_summary, export_all_formats
    leads = []

    if choice == '1':
        print("\n" + "-" * 50)
        print("Template 1: Direct Website Extraction")
        print("-" * 50)
        url = ""
        while not url:
            url = input("Enter website URL (e.g. https://www.joscoffee.com): ").strip()
            if not url:
                print("Website URL cannot be empty.")
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        display.section_header(f"EXTRACTING: {url}")
        lead = asyncio.run(_async_scrape_direct_url(url, force_milli=True))
        if lead:
            leads.append(lead)
            print_lead_summary(lead)

    elif choice == '2':
        print("\n" + "-" * 50)
        print("Template 2: Named Business Search")
        print("-" * 50)
        biz_name = ""
        while not biz_name:
            biz_name = input("Enter business name (e.g. Joe's Bakery): ").strip()
            if not biz_name:
                print("Business name cannot be empty.")
        city = input("Enter city / location (e.g. Austin, TX) [optional]: ").strip()

        display.section_header(f"SEARCHING & VERIFYING: {biz_name} ({city})")
        lead = asyncio.run(_async_scrape_single_business(biz_name, city=city, force_milli=True))
        if lead:
            leads.append(lead)
            print_lead_summary(lead)

    elif choice == '3':
        print("\n" + "-" * 50)
        print("Template 3: Dynamic Business Discovery")
        print("-" * 50)
        location = ""
        while not location:
            location = input("Enter country / city (e.g. Austin, TX or London, UK): ").strip()
            if not location:
                print("Location cannot be empty.")
                
        category = ""
        while not category:
            category = input("Enter business category (e.g. coffee shop, plumber, dentist): ").strip()
            if not category:
                print("Category cannot be empty.")

        qty_input = input("Enter quantity of leads to discover [default: 5]: ").strip()
        quantity = int(qty_input) if qty_input.isdigit() and int(qty_input) > 0 else 5

        display.section_header(f"DISCOVERING {quantity} {category.upper()} LEADS IN {location.upper()}")
        from modules.discovery import discover_businesses
        discovered = discover_businesses(location, quantity, category)
        if not discovered:
            display.error("Discovery failed - no businesses found")
            return

        display.success(f"Discovered {len(discovered)} businesses! Processing with Milli...")
        for idx, item in enumerate(discovered, 1):
            name = item.get('name') or item.get('business_name') or item.get('search_term')
            b_city = item.get('city') or location
            display.info(f"[{idx}/{len(discovered)}] Processing: {name} ({b_city})")
            lead = asyncio.run(_async_scrape_single_business(name, city=b_city, category=category, force_milli=True))
            if lead:
                leads.append(lead)
                print_lead_summary(lead)
            if idx < len(discovered):
                time.sleep(1.0)

    if leads:
        saved = export_all_formats(leads)
        print("\n" + "=" * 65)
        print("  🎉 SUCCESS: All leads successfully saved to your machine!")
        print("=" * 65)
        print(f"  📁 CSV (Excel / Sheets):  {saved['csv']}")
        print(f"  📁 JSON (Data / CRM):      {saved['json']}")
        print(f"  📁 Text Report (Summary):  {saved['txt']}")
        print("=" * 65)
        print("  You can open the CSV file directly in Microsoft Excel or Google Sheets.\n")
    else:
        display.warning("No leads could be extracted.")


def cli():
    # If no flags passed, launch the friendly interactive wizard!
    if len(sys.argv) == 1:
        interactive_menu()
        return

    display.print_banner()
    display.info("Engine: Milli Universal V8 Hyper-Reflex High-Speed Extraction ($0.00 Cost)")
    
    args = parse_args()
    force_milli = not args.no_milli

    from modules.ai_manager import ai_manager
    if args.no_ai:
        config.ENABLE_AI_FALLBACK = False
    elif args.ai:
        config.ENABLE_AI_FALLBACK = True

    if ai_manager.is_available() and getattr(config, 'ENABLE_AI_FALLBACK', True):
        display.info(f"AI Tier: OpenRouter Free Auto-Router (Model: {config.OPENROUTER_MODEL} with server-side fallbacks)")
    else:
        display.info("AI Tier: Standalone Deterministic Mode ($0 Cost). Optional: Add OPENROUTER_API_KEY to .env for free AI auto-rotation.")
    
    # Direct URL mode
    if args.url:
        display.section_header(f"DIRECT URL SCRAPE: {args.url}")
        lead = asyncio.run(_async_scrape_direct_url(args.url, category=args.category, force_milli=force_milli))
        if lead:
            from modules.local_exporter import print_lead_summary, export_to_csv, export_to_json, export_to_txt, export_all_formats
            print_lead_summary(lead)
            if args.output:
                if args.output.endswith('.csv'):
                    export_to_csv([lead], args.output)
                elif args.output.endswith('.txt'):
                    export_to_txt([lead], args.output)
                else:
                    export_to_json([lead], args.output)
                display.success(f"Lead saved to: {args.output}")
            else:
                saved = export_all_formats([lead])
                print("\n" + "=" * 65)
                print("  🎉 SUCCESS: Lead saved to all formats!")
                print(f"  📁 CSV:  {saved['csv']}")
                print(f"  📁 JSON: {saved['json']}")
                print(f"  📁 TXT:  {saved['txt']}")
                print("=" * 65)
        sys.exit(0)
        
    # Direct single business search mode
    if args.business:
        display.section_header(f"DIRECT BUSINESS SCRAPE: {args.business}")
        lead = asyncio.run(_async_scrape_single_business(args.business, city=args.city, category=args.category, force_milli=force_milli))
        if lead:
            from modules.local_exporter import print_lead_summary, export_to_csv, export_to_json, export_to_txt, export_all_formats
            print_lead_summary(lead)
            if args.output:
                if args.output.endswith('.csv'):
                    export_to_csv([lead], args.output)
                elif args.output.endswith('.txt'):
                    export_to_txt([lead], args.output)
                else:
                    export_to_json([lead], args.output)
                display.success(f"Lead saved to: {args.output}")
            else:
                saved = export_all_formats([lead])
                print("\n" + "=" * 65)
                print("  🎉 SUCCESS: Lead saved to all formats!")
                print(f"  📁 CSV:  {saved['csv']}")
                print(f"  📁 JSON: {saved['json']}")
                print(f"  📁 TXT:  {saved['txt']}")
                print("=" * 65)
        sys.exit(0)

    # Discovery mode
    if args.discover:
        run_cli_discovery(
            args.discover,
            args.quantity,
            args.category,
            local_mode=args.local or bool(args.output),
            output_file=args.output,
            force_milli=force_milli
        )
    else:
        # Standard Sheets pipeline mode
        run_pipeline()


if __name__ == "__main__":
    cli()
