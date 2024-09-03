import gspread
from google.oauth2.service_account import Credentials
import time
from gspread.exceptions import APIError
from ratelimit import limits, sleep_and_retry
import json

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

# Open a new Google Sheet for user chat IDs (create this sheet and replace with its ID)
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

# Cache job URLs to reduce read operations
job_urls_cache = None
last_cache_update = 0
CACHE_EXPIRY = 300  # 5 minutes

def ensure_header_row():
    if job_sheet.row_values(1) != HEADER_ROW:
        rate_limited_update(job_sheet, 'A1:I1', [HEADER_ROW])

def get_all_job_urls():
    global job_urls_cache, last_cache_update
    current_time = time.time()
    
    if job_urls_cache is None or (current_time - last_cache_update) > CACHE_EXPIRY:
        job_urls_cache = [row[1] for row in rate_limited_read(job_sheet)[1:]]
        last_cache_update = current_time
    
    return job_urls_cache

def batch_update_jobs(jobs):
    ensure_header_row()
    existing_urls = set(get_all_job_urls())
    new_jobs = [job for job in jobs if job['url'] not in existing_urls]

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
        rate_limited_append_rows(job_sheet, job_data)

def get_user_chat_ids():
    ensure_user_header_row()
    user_data = rate_limited_read(user_sheet)[1:]
    return [(int(row[0]), row[1].lower() == 'true') for row in user_data]

def add_user_chat_id(chat_id):
    existing_ids = [id for id, _ in get_user_chat_ids()]
    if chat_id not in existing_ids:
        rate_limited_append_row(user_sheet, [chat_id, 'false'])

def get_most_recent_job():
    jobs = rate_limited_read(job_sheet)[1:]  # Skip the header row
    if jobs:
        most_recent = jobs[-1]  # Get the last row
        return {
            'title': most_recent[0],
            'url': most_recent[1],
            'employer': most_recent[2],
            'location': most_recent[3],
            'days_until_closing': most_recent[4],
            'salary': most_recent[5],
            'closing_date': most_recent[6],
            'posting_date': most_recent[7],
            'scraped_date': most_recent[8]
        }
    return None

def ensure_user_header_row():
    if user_sheet.row_values(1) != USER_HEADER_ROW:
        rate_limited_update(user_sheet, 'A1:B1', [USER_HEADER_ROW])

# Ensure header rows are present when the module is imported
ensure_header_row()
ensure_user_header_row()