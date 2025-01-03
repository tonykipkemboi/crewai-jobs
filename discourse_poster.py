#!/usr/bin/env python3
"""
Script to post job listings to the CrewAI Discourse forum.
"""

import requests
import pandas as pd
from datetime import datetime, timezone
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Discourse API configuration
DISCOURSE_URL = os.getenv('DISCOURSE_URL')
API_KEY = os.getenv('DISCOURSE_API_KEY')
API_USERNAME = os.getenv('DISCOURSE_USERNAME')
CATEGORY_ID = int(os.getenv('DISCOURSE_CATEGORY_ID'))

if not API_KEY:
    raise ValueError("DISCOURSE_API_KEY environment variable is not set")

class DiscourseJobPoster:
    def __init__(self, discourse_url, api_key, api_username, category_id):
        self.base_url = discourse_url
        self.api_key = api_key
        self.api_username = api_username
        self.category_id = category_id
        self.csrf_token = None
        
    def get_csrf_token(self):
        """Get CSRF token from Discourse."""
        session = requests.Session()
        response = session.get(f"{self.base_url}/session/csrf.json")
        if response.status_code == 200:
            self.csrf_token = response.json()['csrf']
            return session
        raise Exception("Failed to get CSRF token")

    def get_headers(self, with_csrf=False):
        """Get headers for API requests."""
        headers = {
            'Api-Key': self.api_key,
            'Api-Username': self.api_username,
            'Content-Type': 'application/json'
        }
        if with_csrf and self.csrf_token:
            headers['X-CSRF-Token'] = self.csrf_token
        return headers

    def format_job_post_content(self, jobs_df):
        """Format jobs into a nice Discourse post."""
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        content = [
            "# 🤖 CrewAI Job Listings\n",
            f"*Last Updated: {today}*\n\n",
            "Looking for roles in the CrewAI ecosystem? Here are the latest opportunities:\n\n"
        ]

        # Group jobs by company and sort by company name
        jobs_df = jobs_df.sort_values('Company')
        companies = jobs_df[jobs_df['Status'] == 'Active'].groupby('Company')
        
        for company, jobs in companies:
            content.append(f"### {company}\n")
            # Sort jobs by date (newest first)
            jobs = jobs.sort_values('First Seen', ascending=False)
            
            for _, job in jobs.iterrows():
                is_new = job['First Seen'] == today
                new_badge = " 🆕" if is_new else ""
                
                location = job['Location'] if pd.notna(job['Location']) else 'Location not specified'
                job_type = job['Job Type'] if pd.notna(job['Job Type']) else 'Not specified'
                
                content.extend([
                    f"**[{job['Title']}]({job['Link']})**{new_badge}\n",
                    f"📍 {location}" + 
                    (f" | 💼 {job_type}" if job_type != "Not specified" else "") + 
                    f" | ⏰ Posted {job['Time_Posted']}\n\n"
                ])

        content.extend([
            "---\n\n",
            "### Summary\n",
            f"- 📊 Total Active Jobs: {len(jobs_df[jobs_df['Status'] == 'Active'])}\n",
            f"- 🆕 New Today: {len(jobs_df[jobs_df['First Seen'] == today])}\n",
            "\n",
            "If you're interested in contributing to CrewAI, check out our [contributing guide](https://docs.crewai.com/Contributing/)\n\n",
            "*This post is automatically updated daily. Last refresh: " + 
            f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC*\n\n",
            "ℹ️ Having trouble with a job link? Let us know in the comments below."
        ])
        
        return ''.join(content)

    def create_or_update_post(self, title, content):
        """Create a new post or update existing one."""
        try:
            print("Starting post creation/update process...")
            
            # Get CSRF token and session
            session = self.get_csrf_token()
            print("Got CSRF token successfully")
            
            # Create new topic
            create_url = f"{self.base_url}/posts.json"
            create_data = {
                'title': title,
                'raw': content,
                'category': self.category_id,
                'tags': ['jobs', 'crewai', 'automated'],
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            print(f"\nAttempting to create post...")
            print(f"URL: {create_url}")
            print(f"Category ID: {self.category_id}")
            
            response = session.post(
                create_url,
                headers=self.get_headers(with_csrf=True),
                json=create_data
            )
            
            print(f"Response Status: {response.status_code}")
            
            try:
                response_data = response.json()
                print(f"Response Data: {json.dumps(response_data, indent=2)}")
                
                if response.status_code == 200:
                    topic_id = response_data.get('topic_id')
                    print(f"\n✅ Successfully created post!")
                    print(f"🔗 View at: {self.base_url}/t/{topic_id}")
                    return True
                else:
                    print(f"❌ Failed to create post: {response_data}")
                    return False
                    
            except Exception as e:
                print(f"Error parsing response: {str(e)}")
                print(f"Raw response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False

def post_jobs_to_discourse(excel_file='job_listings.xlsx'):
    """Main function to read jobs and post to Discourse."""
    try:
        # Read jobs from Excel
        df = pd.read_excel(excel_file)
        print(f"📊 Read {len(df)} jobs from Excel file")
        
        # Initialize Discourse poster
        poster = DiscourseJobPoster(
            DISCOURSE_URL,
            API_KEY,
            API_USERNAME,
            CATEGORY_ID
        )
        
        # Format content and post
        content = poster.format_job_post_content(df)
        title = "CrewAI Job Listings - Updated Daily"
        
        success = poster.create_or_update_post(title, content)
        
        if success:
            print("\n🎉 Jobs successfully posted/updated on Discourse!")
            print(f"📊 Active Jobs: {len(df[df['Status'] == 'Active'])}")
            print(f"🆕 New Today: {len(df[df['First Seen'] == datetime.now(timezone.utc).strftime('%Y-%m-%d')])}")
        else:
            print("\n❌ Failed to post/update jobs on Discourse")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    print("🚀 Starting job poster...")
    post_jobs_to_discourse()