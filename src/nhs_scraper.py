import requests
from bs4 import BeautifulSoup
import datetime
from google_sheets import batch_update_jobs
from gspread.exceptions import APIError
from tqdm import tqdm
import re

BASE_URL = "https://www.jobs.nhs.uk/candidate/search/results"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

RELEVANT_TITLES = ['psychologist','therapist']

def fetch_nhs_jobs():
    params = {
        'keyword': 'Assistant Psychologist',
        'location': 'London',
        'distance': '20',
        'language': 'en'
    }
    return scrape_all_pages(BASE_URL, params)

def scrape_all_pages(base_url, params):
    all_jobs = []
    page = 1
    pbar = tqdm(desc="Scraping pages", unit="page")
    while True:
        params['page'] = str(page)
        response = requests.get(base_url, params=params, headers=HEADERS)
        soup = BeautifulSoup(response.content, 'html.parser')
        jobs = parse_jobs(soup)
        if not jobs:
            break
        
        all_jobs.extend(jobs)
        page += 1
        pbar.update(1)
    pbar.close()

    print(f"Total jobs found: {len(all_jobs)}")
    try:
        print("Updating Google Sheets...")
        batch_update_jobs(all_jobs)
        print("Google Sheets update completed.")
    except APIError as e:
        print(f"Error updating jobs in Google Sheets: {str(e)}")

    return all_jobs

def parse_jobs(soup):
    job_listings = soup.find_all('li', class_='search-result')
    
    jobs = []
    current_date = datetime.datetime.now().date()
    
    for job in tqdm(job_listings, desc="Parsing jobs", leave=False):
        title = job.find('a', {'data-test': 'search-result-job-title'}).text.strip()
        
        # Check if the job title is relevant
        if not any(word.lower() in title.lower() for word in RELEVANT_TITLES):
            continue
        
        url = "https://www.jobs.nhs.uk" + job.find('a', {'data-test': 'search-result-job-title'})['href']
        
        employer_element = job.find('h3', class_='nhsuk-u-font-weight-bold')
        employer = employer_element.contents[0].strip() if employer_element else "Unknown Employer"
        location = job.find('div', class_='location-font-size').text.strip()
        
        salary_element = job.find('li', {'data-test': 'search-result-salary'})
        salary = salary_element.text.strip().replace('Salary:', '').strip()
        salary = salary.split('a year')[0].strip()  # Remove 'a year' from the end
        
        closing_date_str = job.find('li', {'data-test': 'search-result-closingDate'}).text.strip().replace('Closing date:', '').strip()
        
        try:
            closing_date = datetime.datetime.strptime(closing_date_str, '%d %B %Y').date()
            if closing_date < current_date:
                continue  # Skip jobs that have already closed
            closing_date_str = closing_date.strftime('%d/%m/%Y')
            days_until_closing = (closing_date - current_date).days
        except ValueError:
            print(f"Warning: Unable to parse closing date for job {title}. Skipping.")
            continue
        
        posting_date_str = job.find('li', {'data-test': 'search-result-publicationDate'}).text.strip().replace('Date posted:', '').strip()
        
        try:
            posting_date = datetime.datetime.strptime(posting_date_str, '%d %B %Y').date()
            posting_date_str = posting_date.strftime('%d/%m/%Y')
        except ValueError:
            print(f"Warning: Unable to parse posting date for job {title}. Using current date.")
            posting_date_str = current_date.strftime('%d/%m/%Y')
        
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
    
    return jobs

def main():
    print("Starting NHS job scraper...")
    jobs = fetch_nhs_jobs()
    
    print("\nSample of scraped jobs:")
    for job in jobs[:5]:  # Print only the first 5 jobs as a sample
        print(f"Title: {job['title']}")
        print(f"URL: {job['url']}")
        print(f"Employer: {job['employer']}")
        print(f"Location: {job['location']}")
        print(f"Salary: {job['salary']}")
        print(f"Closing Date: {job['closing_date']}")
        print(f"Scraped Date: {job['scraped_date']}")
        print("---")
    
    print(f"\nTotal jobs scraped and processed: {len(jobs)}")

if __name__ == "__main__":
    main()