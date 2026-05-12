# Morning Agent 🌅

A team productivity bot that sends daily briefings via Telegram and Slack.

## Services
- `main.py` — Telegram personal bot
- `slack_briefing.py` — Slack team briefings
- `setup_app.py` — Web onboarding page for teammates

## Environment Variables
Create a `.env` file with:
TELEGRAM_TOKEN=
CHAT_ID=
LINEAR_API_KEY=
GITHUB_TOKEN=
GITHUB_USERNAME=
GROQ_API_KEY=
SLACK_BOT_TOKEN=
SLACK_CHANNEL_ID=
## Setup
```bash
pip install -r requirements.txt
python main.py        # Telegram bot
python slack_briefing.py  # Slack briefings
python setup_app.py   # Onboarding page
```

## Google Calendar
Each team member needs a `tokens/name.json` file generated via the setup page.
`credentials.json` is required from Google Cloud Console.
