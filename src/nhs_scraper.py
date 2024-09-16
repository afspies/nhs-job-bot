import requests
from bs4 import BeautifulSoup
import datetime
from google_sheets import batch_update_jobs
from gspread.exceptions import APIError
from tqdm import tqdm
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.jobs.nhs.uk/candidate/search/results"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Define the relevant terms
RELEVANT_TERMS = [
    ('assistant', 'psychologist'),
    ('research', 'assistant'),
]

def is_relevant_title(title):
    title_lower = title.lower()
    for term in RELEVANT_TERMS:
        if isinstance(term, tuple):
            if all(t in title_lower for t in term):
                return True
        elif term in title_lower:
            return True
    return False

def fetch_nhs_jobs():
    queries = [
        {'keyword': 'Assistant Psychologist', 'location': 'London', 'distance': '20', 'language': 'en'},
        {'keyword': 'Research Assistant', 'location': 'London', 'distance': '20', 'language': 'en'}
    ]
    all_jobs = []
    for query in queries:
        logger.info(f"Fetching jobs for query: {query['keyword']}")
        jobs = scrape_all_pages(BASE_URL, query)
        all_jobs.extend(jobs)
    return all_jobs

def scrape_all_pages(base_url, params):
    all_jobs = []
    page = 1
    pbar = tqdm(desc="Scraping pages", unit="page")
    while True:
        params['page'] = str(page)
        try:
            response = requests.get(base_url, params=params, headers=HEADERS)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            jobs = parse_jobs(soup)
            logger.info(f"Page {page}: Found {len(jobs)} jobs")
            if not jobs:
                logger.info(f"No more jobs found on page {page}. Stopping.")
                break
            
            all_jobs.extend(jobs)
            page += 1
            pbar.update(1)
        except requests.RequestException as e:
            logger.error(f"Error fetching page {page}: {str(e)}")
            break
    pbar.close()

    logger.info(f"Total jobs found: {len(all_jobs)}")
    return all_jobs

def parse_jobs(soup):
    job_listings = soup.find_all('li', class_='search-result')
    logger.info(f"Found {len(job_listings)} job listings on page")
    
    jobs = []
    current_date = datetime.datetime.now().date()
    
    for job in tqdm(job_listings, desc="Parsing jobs", leave=False):
        try:
            title = job.find('a', {'data-test': 'search-result-job-title'}).text.strip()
            
            # Check if the job title is relevant
            if not is_relevant_title(title):
                logger.debug(f"Skipping irrelevant job: {title}")
                continue
            
            url = "https://www.jobs.nhs.uk" + job.find('a', {'data-test': 'search-result-job-title'})['href']
            
            employer_element = job.find('h3', class_='nhsuk-u-font-weight-bold')
            employer = employer_element.contents[0].strip() if employer_element else "Unknown Employer"
            location = job.find('div', class_='location-font-size').text.strip()
            
            salary_element = job.find('li', {'data-test': 'search-result-salary'})
            salary = salary_element.text.strip().replace('Salary:', '').strip()
            salary = salary.split('a year')[0].strip()  # Remove 'a year' from the end
            
            closing_date_str = job.find('li', {'data-test': 'search-result-closingDate'}).text.strip().replace('Closing date:', '').strip()
            
            closing_date = datetime.datetime.strptime(closing_date_str, '%d %B %Y').date()
            if closing_date < current_date:
                logger.debug(f"Skipping closed job: {title}")
                continue
            closing_date_str = closing_date.strftime('%d/%m/%Y')
            days_until_closing = (closing_date - current_date).days
            
            posting_date_str = job.find('li', {'data-test': 'search-result-publicationDate'}).text.strip().replace('Date posted:', '').strip()
            posting_date = datetime.datetime.strptime(posting_date_str, '%d %B %Y').date()
            posting_date_str = posting_date.strftime('%d/%m/%Y')
            
            jobs.append({
                'title': title,
                'url': url,
                'employer': employer,
                'location': location,
                'days_until_closing': days_until_closing,
                'salary': salary,
                'closing_date': closing_date_str,
                'posting_date': posting_date_str,
                'scraped_date': datetime.datetime.now().strftime('%d/%m/%Y')
            })
            logger.debug(f"Added job: {title}")
        except Exception as e:
            logger.error(f"Error parsing job: {str(e)}")
    
    logger.info(f"Successfully parsed {len(jobs)} relevant jobs")
    return jobs

def main():
    logger.info("Starting NHS job scraper...")
    jobs = fetch_nhs_jobs()
    
    logger.info("Updating Google Sheets...")
    new_jobs = batch_update_jobs(jobs)
    
    if new_jobs:
        logger.info(f"\nNew jobs added: {len(new_jobs)}")
        
        logger.info("\nSample of new jobs:")
        for job in new_jobs[:5]:  # Print only the first 5 new jobs as a sample
            logger.info(f"Title: {job['title']}")
            logger.info(f"URL: {job['url']}")
            logger.info(f"Employer: {job['employer']}")
            logger.info(f"Location: {job['location']}")
            logger.info(f"Salary: {job['salary']}")
            logger.info(f"Closing Date: {job['closing_date']}")
            logger.info(f"Scraped Date: {job['scraped_date']}")
            logger.info("---")
    else:
        logger.info("No new jobs found.")
    
    logger.info(f"\nTotal jobs scraped: {len(jobs)}")
    logger.info(f"New jobs added: {len(new_jobs)}")

if __name__ == "__main__":
    main()