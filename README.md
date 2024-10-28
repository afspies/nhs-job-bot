# NHS Job Alert Bot 🏥 

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue?logo=telegram)](https://telegram.org/)

A Telegram bot that automatically scrapes and notifies users about relevant NHS job postings in London. The bot checks for new positions every 5 minutes and sends notifications when new jobs are found.

## Currently Tracked Positions 👨‍⚕️

The bot currently monitors for the following positions within 20 miles of London:
- Assistant Psychologist positions
- Research Assistant positions

## Features ✨

- 🔍 Automatic job scraping from NHS Jobs website
- 🚨 Real-time notifications for new positions
- 📍 Focused on London area (20-mile radius)
- 📅 Includes key job details like salary, employer, and closing dates
- 🤖 Easy-to-use Telegram interface

## How to Use 🚀

1. Open Telegram and search for `NHSJobs` (or use this link: [https://t.me/NHSJobBot](https://t.me/NHSJobBot))
2. Click "Start" or send the `/start` command to subscribe to notifications
3. You'll receive notifications whenever new relevant positions are posted
4. Use `/check` to manually check for new jobs
5. Use `/help` to see available commands

## Want Other Job Types Added? 💡

If you'd like the bot to track other NHS positions:
- Open an issue in this repository describing the job types you're interested in
- Fork the repository and modify the `RELEVANT_TERMS` in `src/nhs_scraper.py` to include additional job types

## Technical Details 🛠️

The bot is built using:
- Python 3
- python-telegram-bot
- BeautifulSoup4 for web scraping
- Google Sheets API for job storage
- Rate limiting to respect NHS Jobs website

## Setup for Development 💻

1. Clone the repository
2. Install requirements:
```
pip install -r requirements.txt
```
3. Set up the required secrets:
   - Create a `secrets` directory
   - Add `telegram_bot_token.txt` with your Telegram bot token
   - Add `service_account.json` for Google Sheets API access
   - Add `sheet_ids.json` with your Google Sheet IDs for both the NHS Jobs sheet, and bot user sheet

## Contributing 🤝

Contributions are welcome! Feel free to:
- Open issues for bugs or feature requests
- Submit pull requests with improvements
- Fork the project for your own use

## License 📝

MIT License

Copyright (c) 2024 Alexander F. Spies

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.