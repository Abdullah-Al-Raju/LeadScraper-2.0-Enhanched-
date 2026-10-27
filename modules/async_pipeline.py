"""
Async Main Pipeline for LeadScraper Falcon
10x FASTER with concurrent processing!
"""

import asyncio
import config
from modules.utils import logger, calculate_completeness
from modules.sheets import update_status, write_to_output
from modules import display
from modules.async_config import MAX_CONCURRENT_BUSINESSES


async def process_business_async(sheet, row, progress, stats, cache, semaphore):
    """
    Process a single business using multi-source intelligence (ASYNC!)
    
    Args:
        sheet: Google Sheet object
        row: Row data dictionary
        progress: Progress tracker  
        stats: Statistics dictionary
        cache: Progress cache
        semaphore: Concurrency limiter
    """
    async with semaphore:  # Limit concurrency
        row_number = row['row_number']
        category = row.get('category', '')
        business_name = row.get('business_name', '')
        search_term = row.get('search_term', business_name)
        city = row['city']
        
        display_name = category if category else business_name
        logger.info(f"\n--- Processing: {display_name} ({city}) ---")
        
        try:
            # Update status
            update_status(sheet, row_number, config.STATUS_PROCESSING)
            
            # Extract using pure Milli-First architecture
            from main import _async_scrape_single_business
            contacts = await _async_scrape_single_business(
                business_name=dup_check_name,
                city=city,
                category=category,
                website_url=row.get('website'),
                force_milli=True
            )
            
            if not contacts or contacts.get('confidence_score', 0) == 0 and not contacts.get('website'):
                update_status(sheet, row_number, config.STATUS_EXTRACTION_FAILED)
                stats['extraction_failed'] += 1
                progress.update("Failed")
                return
            
            confidence = contacts.get('confidence_score', 0)
            logger.info(f"Milli extraction complete - Confidence: {confidence}%")
            
            # ===== WRITE TO OUTPUT =====
            write_to_output(sheet, contacts)
            
            # Show completion separator
            display.print_completion_separator(progress.current, progress.total)
            
            # Update status based on confidence
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
            
            # Save progress
            if cache:
                cache.add_completed_row(row_number)
            
        except Exception as e:
            logger.error(f"Error processing {display_name}: {e}", exc_info=True)
            error_msg = f"[ERROR] {str(e)[:50]}"
            update_status(sheet, row_number, error_msg)
            stats['extraction_failed'] += 1
            progress.update("Error")


async def run_pipeline_async(sheet, rows, cache):
    """
    Process all businesses concurrently with semaphore control
    
    Args:
        sheet: Google Sheet object
        rows: List of rows to process
        cache: Progress cache
    """
    from modules.utils import ProgressTracker
    
    # Initialize progress tracker
    progress = ProgressTracker(len(rows))
    
    # Statistics
    stats = {
        'total': len(rows),
        'success': 0,
        'partial': 0,
        'no_website': 0,
        'extraction_failed': 0,
        'duplicates': 0
    }
    
    # Create semaphore to limit concurrency
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_BUSINESSES)
    
    logger.info(f"\nASYNC MODE: Processing {len(rows)} businesses with {MAX_CONCURRENT_BUSINESSES} concurrent!")
    
    # Create tasks for all businesses
    tasks = [
        process_business_async(sheet, row, progress, stats, cache, semaphore)
        for row in rows
    ]
    
    # Process all concurrently!
    await asyncio.gather(*tasks, return_exceptions=True)
    
    # Finish
    progress.finish()
    
    return stats
