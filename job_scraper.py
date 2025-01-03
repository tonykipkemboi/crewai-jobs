#!/usr/bin/env python3
"""
Job scraper for CrewAI job listings.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import time
import pandas as pd
import os
from datetime import datetime, timezone
import hashlib
import logging
import sys
import platform
from webdriver_manager.chrome import ChromeDriverManager

# URL of the job listing site
URL = "https://job.zip/jobs/crewai"
FILE_NAME = "job_listings.xlsx"

def generate_job_id(job_data):
    """Generate a unique ID for a job based on its content."""
    # Combine title, company, and location to create a unique identifier
    unique_string = f"{job_data['Title']}{job_data['Company']}{job_data['Location']}"
    # Create a hash of the string to use as ID
    return hashlib.md5(unique_string.encode()).hexdigest()

def setup_driver():
    """Set up and configure the Chrome WebDriver with appropriate options."""
    logging.info("Setting up Chrome WebDriver...")
    
    # Set up Chrome options
    chrome_options = webdriver.ChromeOptions()
    
    # Add required arguments for container environment
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--ignore-ssl-errors=yes')
    chrome_options.add_argument('--ignore-certificate-errors')
    
    try:
        # Connect to Selenium standalone container
        selenium_url = os.getenv('SELENIUM_URL', 'http://localhost:4444/wd/hub')
        logging.info(f"Connecting to Selenium at: {selenium_url}")
        
        driver = webdriver.Remote(
            command_executor=selenium_url,
            options=chrome_options
        )
        
        logging.info("Chrome WebDriver setup completed successfully")
        return driver
    except Exception as e:
        logging.error(f"Failed to set up Chrome WebDriver: {str(e)}")
        logging.error("System information:")
        logging.error(f"Python version: {sys.version}")
        logging.error(f"Operating system: {platform.platform()}")
        logging.error(f"Selenium URL: {selenium_url}")
        raise

def safe_find_element(element, by, selector):
    """Safely find an element, returning None if not found."""
    try:
        return element.find_element(by, selector)
    except Exception:
        return None

def extract_job_details(job_element):
    """Extract job details with error handling for each field."""
    try:
        # Required fields
        title_elem = safe_find_element(job_element, By.XPATH, ".//h3[contains(@class, 'font-bold')]")
        company_elem = safe_find_element(job_element, By.XPATH, ".//div[contains(@class, 'text-orange-600')]")
        
        # Time is in the absolute-positioned paragraph
        time_elem = safe_find_element(job_element, By.XPATH, ".//p[contains(@class, 'hidden sm:flex absolute right-2')]")
        
        # Location is in the div's paragraph
        location_elem = safe_find_element(job_element, By.XPATH, ".//div[2]/div[2]/div/p")
        
        # Job type in separate paragraph
        job_type_elem = safe_find_element(job_element, By.XPATH, ".//div[2]/div[2]/p")
        
        # If any required field is missing, skip this job
        if not all([title_elem, company_elem]):
            return None

        # Create job details dictionary
        job_details = {
            "Title": title_elem.text.strip(),
            "Company": company_elem.text.strip(),
            "Location": location_elem.text.strip() if location_elem else "Location not specified",
            "Job Type": job_type_elem.text.strip() if job_type_elem else "Not specified",
            "Time_Posted": time_elem.text.strip() if time_elem else "",
            "Link": job_element.get_attribute("href"),
            "First Seen": datetime.now(timezone.utc).strftime('%Y-%m-%d'),
            "Last Seen": datetime.now(timezone.utc).strftime('%Y-%m-%d'),
            "Status": "Active"
        }
        
        # Debug print
        print(f"Extracted job: {job_details['Title']}")
        print(f"Location: {job_details['Location']}")
        print(f"Job Type: {job_details['Job Type']}")
        print(f"Time Posted: {job_details['Time_Posted']}")
        print("-" * 50)
        
        # Generate unique ID
        job_details["Job ID"] = generate_job_id(job_details)
        
        return job_details
        
    except Exception as e:
        print(f"Error extracting job details for title: {title_elem.text if title_elem else 'Unknown'}")
        print(f"Full error: {str(e)}")
        return None

def fetch_jobs():
    """Scrape job entries from the website using Selenium."""
    driver = setup_driver()
    jobs = []
    page_num = 1
    
    try:
        driver.get(URL)
        time.sleep(2)  # Initial page load

        while True:
            print(f"Scraping page {page_num}...")
            
            # Wait for job elements to be present
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, "//a[contains(@class, 'flex flex-col') and contains(@rel, 'noopener noreferrer')]")
                )
            )
            
            job_elements = driver.find_elements(
                By.XPATH, 
                "//a[contains(@class, 'flex flex-col') and contains(@rel, 'noopener noreferrer')]"
            )
            
            # Track existing job IDs before processing new ones
            existing_ids = {job['Job ID'] for job in jobs}
            
            page_jobs = []
            for job_element in job_elements:
                job_details = extract_job_details(job_element)
                if job_details and job_details['Job ID'] not in existing_ids:
                    page_jobs.append(job_details)
                    existing_ids.add(job_details['Job ID'])
            
            jobs.extend(page_jobs)
            print(f"Found {len(page_jobs)} new unique jobs on page {page_num} (Total unique jobs: {len(jobs)})")
            
            # Try to find and click the "Load more jobs" button
            try:
                load_more = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[contains(text(), 'Load more jobs')]")
                    )
                )
                driver.execute_script("arguments[0].scrollIntoView();", load_more)
                time.sleep(1)
                load_more.click()
                time.sleep(3)  # Wait for new content to load
                page_num += 1
            except Exception as e:
                print("No more pages to load")
                break
                
    except Exception as e:
        print(f"Error during scraping: {e}")
    finally:
        driver.quit()
        
    return jobs

def load_existing_jobs():
    """Load existing jobs from the spreadsheet."""
    try:
        if os.path.exists(FILE_NAME):
            df = pd.read_excel(FILE_NAME)
            # Ensure all required columns exist
            required_columns = ['Job ID', 'Title', 'Company', 'Location', 'Job Type', 
                              'Link', 'First Seen', 'Last Seen', 'Status']
            for col in required_columns:
                if col not in df.columns:
                    df[col] = ''
            return df
        return pd.DataFrame(columns=['Job ID', 'Title', 'Company', 'Location', 'Job Type', 
                                   'Link', 'First Seen', 'Last Seen', 'Status'])
    except Exception as e:
        print(f"Error loading existing jobs: {e}")
        return pd.DataFrame(columns=['Job ID', 'Title', 'Company', 'Location', 'Job Type', 
                                   'Link', 'First Seen', 'Last Seen', 'Status'])

def update_job_listings(existing_df, new_jobs):
    """Update existing job listings with new data."""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    # Convert new jobs to DataFrame
    new_df = pd.DataFrame(new_jobs)
    
    # Mark all existing jobs as not seen today
    existing_df['Status'] = 'Inactive'
    
    # Process each new job
    for _, new_job in new_df.iterrows():
        # Check if job already exists
        existing_job = existing_df[existing_df['Job ID'] == new_job['Job ID']]
        
        if len(existing_job) > 0:
            # Update existing job
            existing_df.loc[existing_job.index, 'Last Seen'] = today
            existing_df.loc[existing_job.index, 'Status'] = 'Active'
        else:
            # Add new job
            existing_df = pd.concat([existing_df, pd.DataFrame([new_job])], ignore_index=True)
    
    # Sort by First Seen date (newest first) and Status (Active first)
    existing_df['First Seen'] = pd.to_datetime(existing_df['First Seen'])
    existing_df = existing_df.sort_values(['Status', 'First Seen'], 
                                        ascending=[True, False]).reset_index(drop=True)
    
    return existing_df

def save_jobs(df):
    """Save jobs to the spreadsheet with error handling."""
    try:
        # Convert datetime back to string format for Excel
        df['First Seen'] = df['First Seen'].dt.strftime('%Y-%m-%d')
        
        # Save to Excel
        df.to_excel(FILE_NAME, index=False)
        print(f"Successfully saved {len(df)} jobs to {FILE_NAME}")
        
        # Print summary
        active_jobs = len(df[df['Status'] == 'Active'])
        inactive_jobs = len(df[df['Status'] == 'Inactive'])
        print(f"\nSummary:")
        print(f"Active jobs: {active_jobs}")
        print(f"Inactive jobs: {inactive_jobs}")
        print(f"Total jobs tracked: {len(df)}")
        
    except Exception as e:
        print(f"Error saving jobs: {e}")

def main():
    print(f"Starting job scraper at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    # Load existing jobs
    existing_df = load_existing_jobs()
    print(f"Loaded {len(existing_df)} existing jobs")
    
    # Fetch new jobs
    new_jobs = fetch_jobs()
    print(f"Fetched {len(new_jobs)} jobs from website")
    
    # Update job listings
    updated_df = update_job_listings(existing_df, new_jobs)
    
    # Save updated data
    save_jobs(updated_df)

if __name__ == "__main__":
    main()
