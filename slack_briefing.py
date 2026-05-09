import os
import json
import html
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from slack_sdk import WebClient
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from linear_service import get_linear_issues
from calendar_service import get_todays_events
from github_service import get_pull_requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))

PRIORITY_LABELS = {1: "🔴 Urgent", 2: "🟠 High", 3: "🟡 Medium", 4: "🔵 Low", 0: "⚪"}

def build_member_briefing(member: dict) -> str:
    now = datetime.now()
    date_str = now.strftime(f"%A, %B {now.day}")

    # Linear tasks
    issues = get_linear_issues(api_key=member["linear_key"])
    tasks_text = f"*📋 Linear Tasks*\n"
    if issues:
        for issue in issues:
            priority = PRIORITY_LABELS.get(issue.get("priority", 0), "⚪")
            tasks_text += f"  · {priority} {issue['title']} — _{issue['state']['name']}_\n"
    else:
        tasks_text += "  _All clear!_ ✅\n"

    # Calendar
    events = get_todays_events(token_path=os.path.join(BASE_DIR, member["google_token_path"]))
    calendar_text = "*📅 Today's Meetings*\n"
    if events:
        for event in events:
            time = event['start'].get('dateTime', 'All day')
            if 'T' in time:
                time = time[11:16]
            calendar_text += f"  · `{time}` {event['summary']}\n"
    else:
        calendar_text += "  _Free schedule!_ 🎉\n"

    # GitHub PRs
    prs = get_pull_requests(username=member["github_username"])
    pr_text = "*🔀 Pull Requests*\n"
    if prs:
        for pr in prs:
            pr_text += f"  · <{pr['url']}|{pr['title']}> _({pr['repo']})_\n"
    else:
        pr_text += "  _No open PRs_ 🎯\n"

    return (
        f"🌅 *Good morning, {member['name']}!*\n"
        f"_{date_str}_\n\n"
        f"{tasks_text}\n"
        f"{calendar_text}\n"
        f"{pr_text}\n"
        f"_Make it count today! 💪_"
    )

def send_team_summary():
    with open(os.path.join(BASE_DIR, 'members.json')) as f:
        members = json.load(f)

    now = datetime.now()
    date_str = now.strftime(f"%A, %B {now.day}")
    
    summary = f"🌅 *Team Briefing — {date_str}*\n"
    summary += "━━━━━━━━━━━━━━━━━━━━━\n\n"

    for member in members:
        try:
            issues = get_linear_issues(api_key=member["linear_key"])
            in_progress = [i for i in issues if i['state']['name'] == 'In Progress']
            todo = [i for i in issues if i['state']['name'] == 'Todo']
            prs = get_pull_requests(username=member["github_username"])

            summary += f"*{member['name']}* — _{member['role'].upper()}_\n"
            
            if in_progress:
                summary += f"  🔨 In Progress: {', '.join([i['title'] for i in in_progress[:2]])}\n"
            if todo:
                summary += f"  📋 Todo: {len(todo)} task{'s' if len(todo) > 1 else ''}\n"
            if prs:
                summary += f"  🔀 PRs: {len(prs)} open\n"
            
            summary += "\n"
        except Exception as e:
            summary += f"*{member['name']}* — ⚠️ Could not fetch data\n\n"

    client.chat_postMessage(
        channel=os.getenv("SLACK_CHANNEL_ID"),
        text=summary,
        mrkdwn=True
    )
    print("✅ Team summary sent to channel")

def send_all_briefings():
    # Send personal briefings
    with open(os.path.join(BASE_DIR, 'members.json')) as f:
        members = json.load(f)

    for member in members:
        try:
            message = build_member_briefing(member)
            client.chat_postMessage(
                channel=member["slack_id"],
                text=message,
                mrkdwn=True
            )
            print(f"✅ Sent briefing to {member['name']}")
        except Exception as e:
            print(f"❌ Failed for {member['name']}: {e}")

    # Send team summary to global channel
    send_team_summary()

def start_scheduler():
    scheduler = AsyncIOScheduler(timezone="Africa/Douala")
    scheduler.add_job(
        send_all_briefings,
        trigger='cron',
        day_of_week='mon-fri',
        hour=7,
        minute=0,
    )
    scheduler.start()
    print("Slack scheduler started")

    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    start_scheduler()