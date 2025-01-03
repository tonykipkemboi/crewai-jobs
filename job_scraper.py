#!/usr/bin/env python3
"""
Job scraper for CrewAI job listings.
"""

import asyncio
from playwright.async_api import async_playwright
import time
import pandas as pd
import os
import json
import hashlib
import logging
import sys
import platform
from datetime import datetime, timezone

# URL of the job listing site
URL = "https://job.zip/jobs/crewai"
FILE_NAME = "job_listings.xlsx"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)

async def setup_browser():
    """Set up and configure the browser with Playwright."""
    logging.info("Setting up browser...")
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        logging.info("Browser setup completed successfully")
        return playwright, browser, context, page
    except Exception as e:
        logging.error(f"Failed to set up browser: {str(e)}")
        logging.error("System information:")
        logging.error(f"Python version: {sys.version}")
        logging.error(f"Operating system: {platform.platform()}")
        raise

async def safe_click(page, selector, timeout=5000):
    """Safely click an element with timeout."""
    try:
        await page.click(selector, timeout=timeout)
        return True
    except Exception as e:
        logging.warning(f"Failed to click element {selector}: {str(e)}")
        return False

async def safe_get_text(page, selector, timeout=5000):
    """Safely get text from an element with timeout."""
    try:
        element = await page.wait_for_selector(selector, timeout=timeout)
        if element:
            return await element.text_content()
    except Exception as e:
        logging.warning(f"Failed to get text from element {selector}: {str(e)}")
    return ""

async def extract_job_details(job_element):
    """Extract job details with error handling for each field."""
    try:
        # Required fields
        title_elem = await safe_get_text(job_element, ".//h3[contains(@class, 'font-bold')]")
        company_elem = await safe_get_text(job_element, ".//div[contains(@class, 'text-orange-600')]")
        
        # Time is in the absolute-positioned paragraph
        time_elem = await safe_get_text(job_element, ".//p[contains(@class, 'hidden sm:flex absolute right-2')]")
        
        # Location is in the div's paragraph
        location_elem = await safe_get_text(job_element, ".//div[2]/div[2]/div/p")
        
        # Job type in separate paragraph
        job_type_elem = await safe_get_text(job_element, ".//div[2]/div[2]/p")
        
        # If any required field is missing, skip this job
        if not all([title_elem, company_elem]):
            return None

        # Create job details dictionary
        job_details = {
            "Title": title_elem.strip(),
            "Company": company_elem.strip(),
            "Location": location_elem.strip() if location_elem else "Location not specified",
            "Job Type": job_type_elem.strip() if job_type_elem else "Not specified",
            "Time_Posted": time_elem.strip() if time_elem else "",
            "Link": await job_element.get_attribute("href"),
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
        job_details["Job ID"] = hashlib.md5(f"{job_details['Title']}{job_details['Company']}{job_details['Location']}".encode()).hexdigest()
        
        return job_details
        
    except Exception as e:
        print(f"Error extracting job details for title: {title_elem if title_elem else 'Unknown'}")
        print(f"Full error: {str(e)}")
        return None

async def fetch_jobs():
    """Fetch job entries from the website using Playwright."""
    playwright, browser, context, page = await setup_browser()
    jobs = []
    page_num = 1
    
    try:
        await page.goto(URL)
        await page.wait_for_load_state('networkidle')
        
        while True:
            print(f"Scraping page {page_num}...")
            
            # Wait for job elements to be present
            job_elements = await page.query_selector_all("//a[contains(@class, 'flex flex-col') and contains(@rel, 'noopener noreferrer')]")
            
            # Track existing job IDs before processing new ones
            existing_ids = {job['Job ID'] for job in jobs}
            
            page_jobs = []
            for job_element in job_elements:
                job_details = await extract_job_details(job_element)
                if job_details and job_details['Job ID'] not in existing_ids:
                    page_jobs.append(job_details)
                    existing_ids.add(job_details['Job ID'])
            
            jobs.extend(page_jobs)
            print(f"Found {len(page_jobs)} new unique jobs on page {page_num} (Total unique jobs: {len(jobs)})")
            
            # Try to find and click the "Load more jobs" button
            try:
                load_more = await page.query_selector("//button[contains(text(), 'Load more jobs')]")
                if load_more:
                    await load_more.click()
                    await page.wait_for_load_state('networkidle')
                    page_num += 1
                else:
                    break
            except Exception as e:
                print("No more pages to load")
                break
                
    except Exception as e:
        print(f"Error during scraping: {e}")
    finally:
        await context.close()
        await browser.close()
        await playwright.stop()
        
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

async def main():
    """Main function."""
    logging.info(f"Starting job scraper at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    # Load existing jobs
    existing_df = load_existing_jobs()
    print(f"Loaded {len(existing_df)} existing jobs")
    
    # Fetch new jobs
    new_jobs = await fetch_jobs()
    print(f"Fetched {len(new_jobs)} jobs from website")
    
    # Update job listings
    updated_df = update_job_listings(existing_df, new_jobs)
    
    # Save updated data
    save_jobs(updated_df)

if __name__ == "__main__":
    asyncio.run(main())
