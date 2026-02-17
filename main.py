"""
LeadScraper - Main Pipeline Orchestrator
Automated local business contact finder
"""

import sys
import argparse
import time
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
from modules.ai_manager import init_ai_manager
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
    
    display.section_header("LeadScraper Pipeline Starting")
    
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
            category = rows[0].get('category', 'restaurant') or 'restaurant'
            quantity = config.DEFAULT_DISCOVERY_QUANTITY
            
            logger.info(f"Starting discovery: {quantity} {category}s in {location}")
            
            # Discover restaurants
            from modules.restaurant_discovery import discover_restaurants
            restaurants = discover_restaurants(location, quantity, category)
            
            if not restaurants:
                logger.warning("No restaurants discovered")
                return
            
            logger.info(f"Discovered {len(restaurants)} restaurants with contact info")
            
            # Auto-manage sheets
            if config.AUTO_CLEAR_INPUT_ON_DISCOVERY:
                from modules.sheets import clear_input_sheet, populate_input_sheet
                clear_input_sheet(sheet)
                populate_input_sheet(sheet, restaurants)
            
            # Reload rows
            rows = get_unprocessed_rows(sheet)
            logger.info(f"Proceeding to process {len(rows)} discovered restaurants")
        
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
        logger.info("LeadScraper Pipeline Completed")
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

def _validate_config():
    """
    Validate configuration
    
    Returns:
        Boolean indicating if config is valid
    """
    valid = True
    
    if not config.GOOGLE_SHEET_ID:
        logger.error("GOOGLE_SHEET_ID not set. Please configure in .env file")
        valid = False
    
    if not config.SERVICE_ACCOUNT_FILE:
        logger.error("SERVICE_ACCOUNT_FILE not set. Please configure in .env file")
        valid = False
    
    if not config.OPENROUTER_API_KEY:
        logger.warning("OPENROUTER_API_KEY not set. AI extraction will be disabled.")
        logger.warning("The tool will still work with regex fallback.")
    
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
# ENTRY POINT
# ============================================================

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description='LeadScraper AI Agent - Intelligent Business Discovery & Extraction'
    )
    
    parser.add_argument(
        '--discover',
        type=str,
        help='Discovery mode: location to search (e.g., "Dhaka, Bangladesh")'
    )
    
    parser.add_argument(
        '--quantity',
        type=int,
        default=config.DEFAULT_DISCOVERY_QUANTITY,
        help=f'Number of businesses to find (default: {config.DEFAULT_DISCOVERY_QUANTITY})'
    )
    
    parser.add_argument(
        '--category',
        type=str,
        default='restaurant',
        help='Business category (default: restaurant)'
    )
    
    return parser.parse_args()


def run_cli_discovery(location, quantity, category):
    """
    Run discovery mode from CLI - COMPLETE SOLUTION
    
    Discovers businesses AND extracts contact details automatically!
    
    Args:
        location: Location to search
        quantity: Number to find
        category: Business type
    """
    from modules.restaurant_discovery import discover_restaurants
    from modules.sheets import clear_input_sheet, populate_input_sheet
    
    display.section_header(f"AI AGENT MODE: {quantity} {category}s in {location}")
    
    # Connect to sheets
    display.info("Connecting to Google Sheet...")
    workbook = connect_to_sheet()
    
    # Clear input sheet
    if config.AUTO_CLEAR_INPUT_ON_DISCOVERY:
        display.info("Clearing input sheet for fresh start...")
        clear_input_sheet(workbook)
    
    # Discover
    display.ai(f"Discovering {quantity} {category}s...")
    restaurants = discover_restaurants(location, quantity, category)
    
    if not restaurants:
        display.error("Discovery failed - no businesses found")
        sys.exit(1)
    
    # Populate input sheet
    display.info(f"Populating input sheet with {len(restaurants)} businesses...")
    populate_input_sheet(workbook, restaurants)
    
    display.section_header(f"DISCOVERY COMPLETE: {len(restaurants)} businesses added")
    display.info("Now starting EXTRACTION phase...")
    display.print_divider()
    
    # Automatically run extraction pipeline
    run_pipeline()


if __name__ == "__main__":
    # Show banner
    display.print_banner()
    
    # Initialize AI Manager with multi-model support
    init_ai_manager(
        api_key=config.OPENROUTER_API_KEY,
        models=config.OPENROUTER_MODELS,
        base_url=config.OPENROUTER_BASE_URL
    )
    display.success(f"AI Manager initialized with {len(config.OPENROUTER_MODELS)} models")
    
    # Parse CLI args
    args = parse_args()
    
    if args.discover:
        # CLI discovery mode
        run_cli_discovery(args.discover, args.quantity, args.category)
    else:
        # Normal mode - run pipeline
        run_pipeline()
