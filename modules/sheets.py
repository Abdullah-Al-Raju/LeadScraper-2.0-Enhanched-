"""
Google Sheets Integration Module
Read inputs, write outputs, manage status
"""

import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import config
from modules.utils import logger, hash_business


# ============================================================
# GOOGLE SHEETS CONNECTION
# ============================================================

def connect_to_sheet():
    """
    Connect to Google Sheet using service account

    Returns:
        gspread Spreadsheet object
    """
    try:
        # Define the scopes
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]

        # Authenticate
        creds = Credentials.from_service_account_file(
            config.SERVICE_ACCOUNT_FILE,
            scopes=scopes
        )

        # Create client
        client = gspread.authorize(creds)

        # Open the sheet
        sheet = client.open_by_key(config.GOOGLE_SHEET_ID)

        logger.info(f"Successfully connected to Google Sheet: {sheet.title}")

        return sheet

    except FileNotFoundError:
        logger.error(f"Service account file not found: {config.SERVICE_ACCOUNT_FILE}")
        raise
    except Exception as e:
        logger.error(f"Failed to connect to Google Sheet: {e}")
        raise


# ============================================================
# READ INPUT DATA
# ============================================================

def get_unprocessed_rows(sheet):
    """
    Get all unprocessed rows from Input tab

    Args:
        sheet: gspread Spreadsheet object

    Returns:
        List of dictionaries with row data
    """
    try:
        # Get the Input worksheet
        worksheet = sheet.worksheet(config.INPUT_TAB_NAME)

        # Get all records
        all_records = worksheet.get_all_records()

        # Filter unprocessed rows
        unprocessed = []
        for idx, record in enumerate(all_records, start=2):  # Start at 2 (headers in row 1)
            status = record.get('Status', '').strip()

            # Process if status is empty or marked for retry
            if not status or status == config.STATUS_RETRY:
                # Support both old format (Business Name) and new format (Category)
                business_name = record.get('Business Name', '').strip()
                category = record.get('Category', '').strip() or record.get('Business Type', '').strip()

                # Use category if provided, otherwise fall back to business name
                search_term = category if category else business_name

                unprocessed.append({
                    'row_number': idx,
                    'category': category,
                    'business_name': business_name,
                    'search_term': search_term,  # What we'll search for
                    'city': record.get('City/Location', '').strip() or record.get('Location', '').strip(),
                    'status': status
                })

        logger.info(f"Found {len(unprocessed)} unprocessed rows")

        return unprocessed

    except gspread.exceptions.WorksheetNotFound:
        logger.error(f"Worksheet '{config.INPUT_TAB_NAME}' not found")
        raise
    except Exception as e:
        logger.error(f"Error reading input rows: {e}")
        raise


# ============================================================
# UPDATE STATUS
# ============================================================

def update_status(sheet, row_number, status):
    """
    Update status for a specific row in Input tab

    Args:
        sheet: gspread Spreadsheet object
        row_number: Row number to update
        status: Status message
    """
    try:
        worksheet = sheet.worksheet(config.INPUT_TAB_NAME)

        # Update status column (Column C)
        worksheet.update_cell(row_number, 3, status)

        logger.debug(f"Updated row {row_number} status to: {status}")

    except Exception as e:
        logger.error(f"Error updating status for row {row_number}: {e}")


# ============================================================
# WRITE OUTPUT DATA
# ============================================================

def write_to_output(sheet, contacts):
    """
    Write extracted contacts to Output tab

    Args:
        sheet: gspread Spreadsheet object
        contacts: Dictionary of contact information
    """
    try:
        worksheet = sheet.worksheet(config.OUTPUT_TAB_NAME)

        # Get source URLs
        source_urls = contacts.get('source_urls', {})

        # Prepare row data matching the output columns
        row_data = [
            contacts.get('business_name', ''),
            ', '.join(contacts.get('phone_numbers', [])) if contacts.get('phone_numbers') else '',
            ', '.join(contacts.get('email_addresses', [])) if contacts.get('email_addresses') else '',
            contacts.get('street_address', ''),
            contacts.get('city', ''),
            contacts.get('state', ''),
            contacts.get('zip_code', ''),
            contacts.get('website', '') or source_urls.get('website', ''),
            contacts.get('facebook', '') or source_urls.get('facebook', ''),
            contacts.get('instagram', '') or source_urls.get('instagram', ''),
            source_urls.get('directory', ''),  # Directory URL
            contacts.get('business_hours', ''),
            contacts.get('owner_name', ''),
            contacts.get('confidence_score', 0),  # Confidence score
            ', '.join(contacts.get('sources_used', [])) if contacts.get('sources_used') else '',  # Sources
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ]

        # Append the row
        worksheet.append_row(row_data, value_input_option='USER_ENTERED')

        logger.info(f"Wrote contact data for: {contacts.get('business_name', 'Unknown')}")

    except gspread.exceptions.WorksheetNotFound:
        logger.error(f"Worksheet '{config.OUTPUT_TAB_NAME}' not found")
        raise
    except Exception as e:
        logger.error(f"Error writing to output: {e}")
        raise


# ============================================================
# DUPLICATE DETECTION
# ============================================================

_processed_hashes = set()

def is_duplicate(business_name, city=""):
    """
    Check if business has already been processed

    Args:
        business_name: Business name
        city: City/location

    Returns:
        Boolean indicating if duplicate
    """
    business_hash = hash_business(business_name, city)

    if business_hash in _processed_hashes:
        logger.warning(f"Duplicate detected: {business_name} ({city})")
        return True

    _processed_hashes.add(business_hash)
    return False


def load_existing_results(sheet):
    """
    Load existing results to populate duplicate detection

    Args:
        sheet: gspread Spreadsheet object
    """
    try:
        worksheet = sheet.worksheet(config.OUTPUT_TAB_NAME)
        all_records = worksheet.get_all_records()

        for record in all_records:
            name = record.get('Business Name', '').strip()
            city = record.get('City', '').strip()
            if name:
                business_hash = hash_business(name, city)
                _processed_hashes.add(business_hash)

        logger.info(f"Loaded {len(_processed_hashes)} existing results for duplicate detection")

    except Exception as e:
        logger.warning(f"Could not load existing results: {e}")


# ============================================================
# SHEET INITIALIZATION
# ============================================================

def initialize_output_sheet(sheet):
    """
    Initialize output sheet with headers if needed

    Args:
        sheet: gspread Spreadsheet object
    """
    try:
        try:
            worksheet = sheet.worksheet(config.OUTPUT_TAB_NAME)
        except gspread.exceptions.WorksheetNotFound:
            # Create the worksheet if it doesn't exist
            worksheet = sheet.add_worksheet(
                title=config.OUTPUT_TAB_NAME,
                rows=1000,
                cols=16  # Increased for new columns
            )

        # Check if headers exist
        first_row = worksheet.row_values(1)

        if not first_row or first_row[0] != 'Business Name':
            # Set headers with source URLs
            headers = [
                'Business Name', 'Phone', 'Email', 'Address', 'City',
                'State', 'Zip', 'Website', 'Facebook', 'Instagram',
                'Directory', 'Hours', 'Owner', 'Confidence', 'Sources', 'Scraped At'
            ]
            worksheet.update('A1:P1', [headers])

            # Format headers (bold)
            worksheet.format('A1:P1', {
                'textFormat': {'bold': True},
                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
            })

            logger.info("Initialized output sheet with enhanced headers (includes source URLs)")

    except Exception as e:
        logger.error(f"Error initializing output sheet: {e}")


def initialize_input_sheet(sheet):
    """
    Initialize input sheet with headers if needed

    Args:
        sheet: gspread Spreadsheet object
    """
    try:
        try:
            worksheet = sheet.worksheet(config.INPUT_TAB_NAME)
        except gspread.exceptions.WorksheetNotFound:
            # Create the worksheet if it doesn't exist
            worksheet = sheet.add_worksheet(
                title=config.INPUT_TAB_NAME,
                rows=1000,
                cols=3
            )

        # Check if headers exist
        first_row = worksheet.row_values(1)

        # Support both old and new header formats
        if not first_row or (first_row[0] not in ['Business Name', 'Category', 'Business Type']):
            # Set new category-based headers
            headers = ['Category', 'Location', 'Status']
            worksheet.update('A1:C1', [headers])

            # Format headers (bold)
            worksheet.format('A1:C1', {
                'textFormat': {'bold': True},
                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
            })

            logger.info("Initialized input sheet with category-based headers")

    except Exception as e:
        logger.error(f"Error initializing input sheet: {e}")


# ============================================================
# DISCOVERY MODE - SHEET MANAGEMENT
# ============================================================

def clear_input_sheet(sheet):
    """Clear all rows from input sheet (keep headers)"""
    try:
        worksheet = sheet.worksheet(config.INPUT_TAB_NAME)
        all_values = worksheet.get_all_values()

        if len(all_values) <= 1:
            logger.info("Input sheet already empty")
            return

        if len(all_values) > 1:
            worksheet.delete_rows(2, len(all_values))
        logger.info(f"Cleared {len(all_values) - 1} rows from input sheet")
    except Exception as e:
        logger.error(f"Error clearing input sheet: {e}")


def populate_input_sheet(sheet, restaurants):
    """Auto-populate input sheet with discovered restaurants"""
    try:
        worksheet = sheet.worksheet(config.INPUT_TAB_NAME)
        rows = [[r['name'], r['location'], ''] for r in restaurants]

        if rows:
            worksheet.append_rows(rows, value_input_option='USER_ENTERED')
            logger.info(f"Populated input sheet with {len(rows)} restaurants")
    except Exception as e:
        logger.error(f"Error populating input sheet: {e}")


def deduplicate_results(sheet):
    """Remove duplicate entries from results sheet"""
    try:
        worksheet = sheet.worksheet(config.OUTPUT_TAB_NAME)
        all_records = worksheet.get_all_records()

        if not all_records:
            return

        seen = set()
        unique_rows = []
        duplicates = 0

        for record in all_records:
            business_name = record.get('Business Name', '').strip().lower()
            phones = record.get('Phone', '').strip()
            first_phone = phones.split(',')[0].strip() if phones else ''
            key = f"{business_name}|{first_phone}"

            if key not in seen:
                seen.add(key)
                unique_rows.append(list(record.values()))
            else:
                duplicates += 1

        if duplicates > 0:
            headers = worksheet.row_values(1)
            worksheet.clear()
            worksheet.append_row(headers, value_input_option='USER_ENTERED')
            if unique_rows:
                worksheet.append_rows(unique_rows, value_input_option='USER_ENTERED')
            logger.info(f"Removed {duplicates} duplicate entries")
    except Exception as e:
        logger.error(f"Error deduplicating results: {e}")


def sort_results_by_confidence(sheet):
    """Sort results by confidence score (highest first)"""
    try:
        worksheet = sheet.worksheet(config.OUTPUT_TAB_NAME)
        all_values = worksheet.get_all_values()

        if len(all_values) <= 1:
            return

        headers = all_values[0]
        data_rows = all_values[1:]

        try:
            confidence_idx = headers.index('Confidence')
        except ValueError:
            return

        sorted_rows = sorted(
            data_rows,
            key=lambda row: float(row[confidence_idx]) if row[confidence_idx] and str(row[confidence_idx]).replace('.', '').isdigit() else 0,
            reverse=True
        )

        worksheet.clear()
        worksheet.append_row(headers, value_input_option='USER_ENTERED')
        if sorted_rows:
            worksheet.append_rows(sorted_rows, value_input_option='USER_ENTERED')
        logger.info(f"Sorted {len(sorted_rows)} results by confidence")
    except Exception as e:
        logger.error(f"Error sorting results: {e}")
