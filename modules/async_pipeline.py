"""
Async Main Pipeline for LeadScraper Pro
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

            # ===== MULTI-SOURCE DISCOVERY (ASYNC!) =====
            logger.info("Step 1: Multi-Source Discovery...")

            from modules.search import search_for_website

            # Search concurrently for different sources
            website_task = search_for_website(search_term, city)

            # Run website search
            website_url = await website_task

            if not website_url:
                update_status(sheet, row_number, config.STATUS_NO_WEBSITE)
                stats['no_website'] += 1
                progress.update("No website found")
                return

            logger.info(f"Found website: {website_url}")

            # ===== MULTI-SOURCE EXTRACTION (ASYNC & CONCURRENT!) =====
            logger.info("Step 2: Extracting from all sources concurrently...")

            # Create concurrent extraction tasks
            extraction_tasks = []

            # Task 1: Crawl website
            from modules.crawler import crawl_website
            extraction_tasks.append(crawl_website(website_url))

            # Task 2: Search results extraction (run in executor - it's sync)
            async def extract_search_results():
                try:
                    from modules.sources.search_result_extractor import extract_from_search_results
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(
                        None,
                        extract_from_search_results,
                        search_term,
                        city,
                        category
                    )
                except Exception as e:
                    logger.warning(f"Search extraction failed: {e}")
                    return None

            extraction_tasks.append(extract_search_results())

            #Task 3: Facebook search (run in executor)
            async def extract_facebook():
                try:
                    from modules.sources.search_result_extractor import extract_from_social_search
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(
                        None,
                        extract_from_social_search,
                        search_term,
                        city,
                        'facebook'
                    )
                except Exception as e:
                    logger.warning(f"Facebook extraction failed: {e}")
                    return None

            extraction_tasks.append(extract_facebook())

            # Task 4: Instagram search (run in executor)
            async def extract_instagram():
                try:
                    from modules.sources.search_result_extractor import extract_from_social_search
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(
                        None,
                        extract_from_social_search,
                        search_term,
                        city,
                        'instagram'
                    )
                except Exception as e:
                    logger.warning(f"Instagram extraction failed: {e}")
                    return None

            extraction_tasks.append(extract_instagram())

            # Run all extractions CONCURRENTLY!
            logger.info(f"Running {len(extraction_tasks)} extractions in parallel...")
            extraction_results = await asyncio.gather(*extraction_tasks, return_exceptions=True)

            # Filter out None and exceptions
            sources_data = [
                result for result in extraction_results
                if result and not isinstance(result, Exception)
            ]

            logger.info(f"Got data from {len(sources_data)} sources")

            if not sources_data:
                update_status(sheet, row_number, config.STATUS_EXTRACTION_FAILED)
                stats['extraction_failed'] += 1
                progress.update("Extraction failed")
                return

            # ===== DATA FUSION =====
            logger.info("Step 3: Fusing data from all sources...")

            from modules.fusion import merge_multi_source_data
            contacts = merge_multi_source_data(sources_data)

            # Add metadata
            contacts['business_name'] = business_name or search_term
            contacts['city'] = city
            contacts['category'] = category
            contacts['website'] = website_url

            # Calculate completeness
            confidence = calculate_completeness(contacts)
            contacts['completeness_score'] = confidence

            logger.info(f"Data fusion complete - Confidence: {confidence}%")

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
