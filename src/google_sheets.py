import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError
from ratelimit import limits, sleep_and_retry
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up the scope and credentials
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = './secrets/service_account.json'

creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

# Read sheet IDs from the secrets file
with open('./secrets/sheet_ids.json', 'r') as f:
    sheet_ids = json.load(f)

# Open the Google Sheet for job listings
JOB_SHEET_ID = sheet_ids['JOB_SHEET_ID']
job_sheet = client.open_by_key(JOB_SHEET_ID).sheet1

# Open a new Google Sheet for user chat IDs
USER_SHEET_ID = sheet_ids['USER_SHEET_ID']
user_sheet = client.open_by_key(USER_SHEET_ID).sheet1

# Update the header row
HEADER_ROW = ['Title', 'URL', 'Employer', 'Location', 'Days Until Closing', 'Salary', 'Closing Date', 'Posting Date', 'Scraped Date']

# Update the user sheet header row
USER_HEADER_ROW = ['Chat ID', 'Debug']

# Reduce rate limits for both read and write operations
@sleep_and_retry
@limits(calls=40, period=60)
def rate_limited_read(worksheet, *args, **kwargs):
    return worksheet.get_all_values(*args, **kwargs)

@sleep_and_retry
@limits(calls=40, period=60)
def rate_limited_update(worksheet, *args, **kwargs):
    return worksheet.update(*args, **kwargs)

@sleep_and_retry
@limits(calls=40, period=60)
def rate_limited_append_rows(worksheet, *args, **kwargs):
    return worksheet.append_rows(*args, **kwargs)

@sleep_and_retry
@limits(calls=40, period=60)
def rate_limited_append_row(worksheet, *args, **kwargs):
    return worksheet.append_row(*args, **kwargs)

def ensure_header_row():
    if job_sheet.row_values(1) != HEADER_ROW:
        rate_limited_update(job_sheet, 'A1:I1', [HEADER_ROW])

def get_all_jobs():
    all_jobs = rate_limited_read(job_sheet)[1:]  # Skip the header row
    return [
        {
            'title': job[0],
            'url': job[1],
            'employer': job[2],
            'location': job[3],
            'days_until_closing': job[4],
            'salary': job[5],
            'closing_date': job[6],
            'posting_date': job[7],
            'scraped_date': job[8]
        }
        for job in all_jobs
    ]

def batch_update_jobs(jobs):
    ensure_header_row()
    existing_jobs = get_all_jobs()
    existing_urls = set(job['url'] for job in existing_jobs)
    new_jobs = [job for job in jobs if job['url'] not in existing_urls]

    logger.info(f"Total jobs received: {len(jobs)}")
    logger.info(f"New jobs to add: {len(new_jobs)}")

    if new_jobs:
        job_data = [
            [
                job['title'],
                job['url'],
                job['employer'],
                job['location'],
                job['days_until_closing'],
                job['salary'],
                job['closing_date'],
                job['posting_date'],
                job['scraped_date']
            ] for job in new_jobs
        ]
        try:
            result = rate_limited_append_rows(job_sheet, job_data)
            updated_rows = result.get('updates', {}).get('updatedRows', 0)
            logger.info(f"Rows added: {updated_rows}")
            if updated_rows == 0:
                logger.warning("No rows were added to the sheet. This might indicate an issue.")
                logger.info(f"First new job data: {job_data[0]}")
            return new_jobs
        except Exception as e:
            logger.error(f"Error appending rows: {str(e)}")
            return []
    else:
        logger.info("No new jobs to add")
        return []

def get_user_chat_ids():
    ensure_user_header_row()
    user_data = rate_limited_read(user_sheet)[1:]
    return [(int(row[0]), row[1].lower() == 'true') for row in user_data]

def add_user_chat_id(chat_id, debug=False):
    existing_ids = [id for id, _ in get_user_chat_ids()]
    if chat_id not in existing_ids:
        rate_limited_append_row(user_sheet, [chat_id, str(debug).lower()])
    else:
        # Update existing user's debug status
        user_row = next(i for i, (id, _) in enumerate(get_user_chat_ids(), start=2) if id == chat_id)
        rate_limited_update(user_sheet, f'B{user_row}', [[str(debug).lower()]])

def get_debug_user_chat_ids():
    return [id for id, debug in get_user_chat_ids() if debug]

def get_most_recent_job():
    jobs = get_all_jobs()
    return jobs[-1] if jobs else None

def ensure_user_header_row():
    if user_sheet.row_values(1) != USER_HEADER_ROW:
        rate_limited_update(user_sheet, 'A1:B1', [USER_HEADER_ROW])

# Ensure header rows are present when the module is imported
ensure_header_row()
ensure_user_header_row()