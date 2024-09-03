import sys
import os

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from nhs_scraper import fetch_nhs_jobs, parse_jobs
from bs4 import BeautifulSoup

def test_fetch_nhs_jobs():
    jobs = fetch_nhs_jobs()
    print("Fetch NHS Jobs Test:")
    print(f"Number of jobs found: {len(jobs)}")
    if jobs:
        print("First job details:")
        for key, value in jobs[0].items():
            print(f"{key}: {value}")
    else:
        print("No jobs found.")
    print("---")

def test_parse_jobs():
    # Create a sample HTML content for testing
    sample_html = '''
    <li class="search-result">
        <a data-test="search-result-job-title" href="/job/example">Sample Job</a>
        <h3 class="nhsuk-u-font-weight-bold">Sample Employer</h3>
        <div class="location-font-size">London</div>
        <li data-test="search-result-salary">Salary: £30,000 - £40,000 a year</li>
        <li data-test="search-result-closingDate">Closing date: 31/12/2023</li>
    </li>
    '''
    soup = BeautifulSoup(sample_html, 'html.parser')
    jobs = parse_jobs(soup)
    
    print("Parse Jobs Test:")
    print(f"Number of jobs found: {len(jobs)}")
    if jobs:
        print("Job details:")
        for key, value in jobs[0].items():
            print(f"{key}: {value}")
    else:
        print("No jobs found.")
    print("---")

if __name__ == "__main__":
    test_fetch_nhs_jobs()
    test_parse_jobs()
