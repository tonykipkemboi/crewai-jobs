# CrewAI Jobs Forum Automation

This project automates the process of scraping job listings related to CrewAI and posting them to the CrewAI community forum. It runs automatically every 12 hours via GitHub Actions.

## Features

- 🤖 Automated job scraping from job.zip
- 📊 Maintains a local Excel database of jobs
- 🔄 Tracks job status (Active/Inactive)
- 🎯 Automatic posting to CrewAI community forum
- 🕒 Runs every 12 hours via GitHub Actions
- 🆕 Highlights new job postings

## Requirements

- Python 3.11+
- Chrome/Chromium browser (for Selenium)
- Required Python packages (see `requirements.txt`)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/tonykipkemboi/crewai-jobs.git
cd crewai-jobs
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Add your Discourse API credentials:
```env
DISCOURSE_API_KEY=your_api_key_here
DISCOURSE_USERNAME=your_username
DISCOURSE_URL=your_discourse_url
DISCOURSE_CATEGORY_ID=your_category_id
```

## Usage

### Local Development

1. Run the job scraper:
```bash
python job_scraper.py
```

2. Post jobs to the forum:
```bash
python discourse_poster.py
```

### GitHub Actions

The workflow runs automatically every 12 hours. To run it manually:

1. Go to the Actions tab in your GitHub repository
2. Select the "Update Jobs" workflow
3. Click "Run workflow"

## Project Structure

```
crewai-jobs/
├── .github/
│   └── workflows/
│       └── update-jobs.yml    # GitHub Actions workflow
├── requirements.txt           # Python dependencies
├── job_scraper.py            # Job scraping script
├── discourse_poster.py        # Forum posting script
└── README.md                 # This file
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DISCOURSE_API_KEY` | Your Discourse API key |
| `DISCOURSE_USERNAME` | Your Discourse username |
| `DISCOURSE_URL` | Discourse forum URL |
| `DISCOURSE_CATEGORY_ID` | Category ID for job posts |

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [CrewAI Community](https://community.crewai.com)
- [job.zip](https://job.zip) for job listings
- Contributors and maintainers

Last updated: 2025-01-03
