import os
import json
import httpx
import asyncio
from datetime import datetime, timezone
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
    
def send_end_of_day_summary():
    with open(os.path.join(BASE_DIR, 'members.json')) as f:
        members = json.load(f)

    now = datetime.now()
    date_str = now.strftime(f"%A, %B {now.day}")

    for member in members:
        try:
            issues = get_linear_issues(api_key=member["linear_key"])
            
            completed = [i for i in issues if i['state']['name'] == 'Done']
            in_progress = [i for i in issues if i['state']['name'] == 'In Progress']
            todo = [i for i in issues if i['state']['name'] == 'Todo']

            message = (
                f"📊 *End of Day — {date_str}*\n\n"
                f"Here's how your day went, {member['name']}!\n\n"
                f"✅ *Completed:* {len(completed)} task{'s' if len(completed) != 1 else ''}\n"
                f"🔄 *Still in progress:* {len(in_progress)} task{'s' if len(in_progress) != 1 else ''}\n"
                f"📋 *Still todo:* {len(todo)} task{'s' if len(todo) != 1 else ''}\n\n"
            )

            if in_progress:
                message += "*Still in progress:*\n"
                for issue in in_progress:
                    message += f"  · {issue['title']}\n"
                message += "\n"

            if completed:
                message += "*Completed today:*\n"
                for issue in completed[:5]:
                    message += f"  · ✅ {issue['title']}\n"

            message += "\n_Great work today! Rest well. 🌙_"

            client.chat_postMessage(
                channel=member["slack_id"],
                text=message,
                mrkdwn=True
            )
            print(f"✅ End of day summary sent to {member['name']}")
        except Exception as e:
            print(f"❌ Failed for {member['name']}: {e}")
            
def send_pre_meeting_briefing():
    with open(os.path.join(BASE_DIR, 'members.json')) as f:
        members = json.load(f)

    now = datetime.now()
    date_str = now.strftime(f"%A, %B {now.day}")

    blocked_items = []
    pr_items = []
    total_tasks = 0
    completed_tasks = 0

    for member in members:
        try:
            issues = get_linear_issues(api_key=member["linear_key"])
            prs = get_pull_requests(username=member["github_username"])

            total_tasks += len(issues)
            completed_tasks += len([i for i in issues if i['state']['name'] == 'Done'])

            # Find blocked or long running in-progress tasks
            for issue in issues:
                if issue['state']['name'] == 'In Progress':
                    blocked_items.append({
                        "name": member["name"],
                        "title": issue["title"]
                    })

            # Find PRs older than 1 day
            for pr in prs:
                pr_items.append({
                    "name": member["name"],
                    "title": pr["title"],
                    "url": pr["url"],
                    "repo": pr["repo"]
                })

        except Exception as e:
            print(f"❌ Failed for {member['name']}: {e}")

    progress = f"{completed_tasks}/{total_tasks}"
    percent = int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0

    message = (
        f"⏰ *Daily Tech in 15 minutes!*\n"
        f"_{date_str}_\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    if blocked_items:
        message += "🔴 *Items in progress (needs discussion):*\n"
        for item in blocked_items[:5]:
            message += f"  · *{item['name']}* — {item['title']}\n"
        message += "\n"
    else:
        message += "✅ *No blocked items!*\n\n"

    if pr_items:
        message += "🔀 *PRs needing review:*\n"
        for pr in pr_items[:5]:
            message += f"  · <{pr['url']}|{pr['title']}> by *{pr['name']}*\n"
        message += "\n"
    else:
        message += "🎯 *No open PRs!*\n\n"

    message += (
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *Sprint progress:* {progress} tasks done ({percent}%)\n"
        f"_Let's have a great meeting! 💪_"
    )

    client.chat_postMessage(
        channel=os.getenv("SLACK_CHANNEL_ID"),
        text=message,
        mrkdwn=True
    )
    print("✅ Pre-meeting briefing sent to channel")
    
def send_sprint_reminder():
    with open(os.path.join(BASE_DIR, 'members.json')) as f:
        members = json.load(f)

    now = datetime.now()
    date_str = now.strftime(f"%A, %B {now.day}")

    message = (
        f"🏃 *New Sprint Week — {date_str}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Here's what everyone is working on this week:\n\n"
    )

    for member in members:
        try:
            issues = get_linear_issues(api_key=member["linear_key"])
            urgent = [i for i in issues if i.get("priority") == 1]
            high = [i for i in issues if i.get("priority") == 2]
            in_progress = [i for i in issues if i['state']['name'] == 'In Progress']

            message += f"*{member['name']}* — _{member['role'].upper()}_\n"

            if in_progress:
                message += f"  🔨 In progress: {len(in_progress)} task{'s' if len(in_progress) != 1 else ''}\n"
            if urgent:
                message += f"  🔴 Urgent: {len(urgent)} task{'s' if len(urgent) != 1 else ''}\n"
            if high:
                message += f"  🟠 High priority: {len(high)} task{'s' if len(high) != 1 else ''}\n"
            if not in_progress and not urgent and not high:
                message += f"  ✅ No urgent tasks\n"

            message += "\n"

        except Exception as e:
            message += f"*{member['name']}* — ⚠️ Could not fetch data\n\n"

    message += "━━━━━━━━━━━━━━━━━━━━━\n_Let's crush it this week! 💪_"

    client.chat_postMessage(
        channel=os.getenv("SLACK_CHANNEL_ID"),
        text=message,
        mrkdwn=True
    )
    print("✅ Sprint reminder sent")


def send_weekly_report():
    with open(os.path.join(BASE_DIR, 'members.json')) as f:
        members = json.load(f)

    now = datetime.now()
    date_str = now.strftime(f"%A, %B {now.day}")

    total_completed = 0
    total_in_progress = 0
    total_prs = 0
    most_productive = None
    max_completed = 0
    member_stats = []

    for member in members:
        try:
            issues = get_linear_issues(api_key=member["linear_key"])
            prs = get_pull_requests(username=member["github_username"])

            completed = len([i for i in issues if i['state']['name'] == 'Done'])
            in_progress = len([i for i in issues if i['state']['name'] == 'In Progress'])

            total_completed += completed
            total_in_progress += in_progress
            total_prs += len(prs)

            if completed > max_completed:
                max_completed = completed
                most_productive = member["name"]

            member_stats.append({
                "name": member["name"],
                "role": member["role"],
                "completed": completed,
                "in_progress": in_progress,
                "prs": len(prs)
            })

        except Exception as e:
            print(f"❌ Failed for {member['name']}: {e}")

    message = (
        f"📈 *Weekly Team Report — {date_str}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"*Team Overview:*\n"
        f"  ✅ Tasks completed: {total_completed}\n"
        f"  🔄 Still in progress: {total_in_progress}\n"
        f"  🔀 Open PRs: {total_prs}\n"
    )

    if most_productive:
        message += f"  🏆 Most productive: *{most_productive}* ({max_completed} tasks)\n"

    message += "\n*Individual Stats:*\n"
    for stat in member_stats:
        message += (
            f"  · *{stat['name']}* — _{stat['role'].upper()}_\n"
            f"    ✅ {stat['completed']} completed · "
            f"🔄 {stat['in_progress']} in progress · "
            f"🔀 {stat['prs']} PRs\n"
        )

    message += "\n━━━━━━━━━━━━━━━━━━━━━\n_Great work this week everyone! See you Monday. 🎉_"

    # Send to channel and boss DM
    client.chat_postMessage(
        channel=os.getenv("SLACK_CHANNEL_ID"),
        text=message,
        mrkdwn=True
    )

    # Also send to boss DM
    boss = next((m for m in members if m["role"] == "po"), None)
    if boss:
        client.chat_postMessage(
            channel=boss["slack_id"],
            text=message,
            mrkdwn=True
        )

    print("✅ Weekly report sent")
    
def send_pr_review_reminders():
    with open(os.path.join(BASE_DIR, 'members.json')) as f:
        members = json.load(f)

    github_token = os.getenv("GITHUB_TOKEN")
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json"
    }

    for member in members:
        try:
            # Get PRs assigned to this member for review
            response = httpx.get(
                f"https://api.github.com/search/issues?q=is:pr+is:open+review-requested:{member['github_username']}",
                headers=headers
            )
            prs = response.json().get("items", [])

            if not prs:
                continue

            message = f"👀 *PR Review Reminder*\n\n"
            message += f"Hey {member['name']}, these PRs are waiting for your review:\n\n"

            for pr in prs:
                created_at = datetime.strptime(pr["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                age = datetime.now(timezone.utc) - created_at
                days = age.days
                hours = age.seconds // 3600

                age_str = f"{days}d {hours}h" if days > 0 else f"{hours}h"
                urgency = "🔴" if days >= 2 else "🟠" if days >= 1 else "🟡"

                repo = pr["repository_url"].split("/repos/")[1]
                message += f"  {urgency} <{pr['html_url']}|{pr['title']}>\n"
                message += f"    _{repo} · Open for {age_str}_\n\n"

            message += "_Please review when you get a chance! 🙏_"

            client.chat_postMessage(
                channel=member["slack_id"],
                text=message,
                mrkdwn=True
            )
            print(f"✅ PR reminder sent to {member['name']}")

        except Exception as e:
            print(f"❌ Failed for {member['name']}: {e}")

def start_scheduler():
    scheduler = AsyncIOScheduler(timezone="Africa/Douala")
    scheduler.add_job(
        send_all_briefings,
        trigger='cron',
        day_of_week='mon-fri',
        hour=7,
        minute=0,
    )
    scheduler.add_job(
        send_end_of_day_summary,
        trigger='cron',
        day_of_week='mon-fri',
        hour=18,
        minute=0,
    )
    scheduler.add_job(
        send_pre_meeting_briefing,
        trigger='cron',
        day_of_week='mon-fri',
        hour=9,
        minute=45,
    )
    scheduler.add_job(
        send_sprint_reminder,
        trigger='cron',
        day_of_week='mon',
        hour=7,
        minute=30,
    )
    scheduler.add_job(
        send_weekly_report,
        trigger='cron',
        day_of_week='fri',
        hour=17,
        minute=30,
    )
    for hour in [9, 13, 17]:
        scheduler.add_job(
            send_pr_review_reminders,
            trigger='cron',
            day_of_week='mon-fri',
            hour=hour,
            minute=0,
        )
    scheduler.start()

    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    start_scheduler()