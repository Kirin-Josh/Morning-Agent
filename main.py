import os
import logging
import html
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from github_service import get_pull_requests
from linear_service import get_linear_issues
from calendar_service import get_todays_events
from ai_service import ask_ai

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
YOUR_CHAT_ID = os.getenv("CHAT_ID")

logging.basicConfig(level=logging.WARNING)

SEP = "━━━━━━━━━━━━━━━━━━━━━"
PRIORITY_LABELS = {1: "🔴 Urgent", 2: "🟠 High", 3: "🟡 Medium", 4: "🔵 Low", 0: "⚪"}
PRIORITY_ICONS  = {1: "🔴", 2: "🟠"}

def escape_md(text: str) -> str:
    for char in ['_', '*', '[', ']', '`']:
        text = text.replace(char, f'\\{char}')
    return text

async def build_briefing_message():
    now = datetime.now()
    date_str = now.strftime(f"%A, %B {now.day}")

    issues = get_linear_issues()
    task_label = f"{len(issues)} task{'s' if len(issues) != 1 else ''}" if issues else "none"
    tasks_text = f"📋 <b>Linear Tasks</b> — <i>{task_label}</i>\n"
    if issues:
        for issue in issues:
            priority = PRIORITY_LABELS.get(issue.get("priority", 0), "⚪")
            state = issue['state']['name']
            tasks_text += f"  · {priority}  {escape_md(issue['title'])}\n    ↳ <i>{escape_md(state)}</i>\n"
    else:
        tasks_text += "  _All clear!_ ✅\n"

    events = get_todays_events()
    event_label = f"{len(events)} event{'s' if len(events) != 1 else ''}" if events else "none"
    calendar_text = f"📅 <b>Today's Meetings</b> — <i>{event_label}</i>\n"
    if events:
        for event in events:
            time = event['start'].get('dateTime', 'All day')
            if 'T' in time:
                time = time[11:16]
            calendar_text += f"  · <code>{time}</code>  {escape_md(event['summary'])}\n"
    else:
        calendar_text += "  <i>Free schedule!</i> 🎉\n"

    prs = get_pull_requests()
    pr_label = f"{len(prs)} open" if prs else "none"
    pr_text = f"🔀 <b>Open Pull Requests</b> — <i>{pr_label}</i>\n"
    if prs:
        for pr in prs:
            pr_text += f"  · <a href='{pr['url']}'>{html.escape(pr['title'])}</a> <i>({html.escape(pr['repo'])})</i>\n"
    else:
        pr_text += "  <i>No open PRs</i> 🎯\n"

    return (
        f"🌅 <b>Good morning, Joshua!</b>\n"
        f"<i>{date_str}</i>\n\n"
        f"{SEP}\n\n"
        f"{tasks_text}\n"
        f"{SEP}\n\n"
        f"{calendar_text}\n"
        f"{SEP}\n\n"
        f"{pr_text}\n"
        f"{SEP}\n"
        f"<i>Make it count today! 💪</i>"
    )

async def send_scheduled_briefing(bot: Bot):
    message = await build_briefing_message()
    await bot.send_message(chat_id=YOUR_CHAT_ID, text=message, parse_mode='HTML')

async def briefing(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ <i>Fetching your briefing...</i>", parse_mode='HTML')
    message = await build_briefing_message()
    await update.message.reply_text(message, parse_mode='HTML')

async def start(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"👋 <b>Hey Joshua!</b>\n\n"
        f"I'm your morning briefing bot. Here's what I can do:\n\n"
        f"  · /briefing — Full morning briefing\n"
        f"  · /calendars — List your calendars\n\n"
        f"<i>Briefings are sent automatically at 7:00 AM.</i> ☀️",
        parse_mode='HTML'
    )

async def send_nudge(bot: Bot):
    issues = get_linear_issues()
    prs = get_pull_requests()

    pending_tasks = [
        i for i in issues
        if i['state']['name'] in ['In Progress', 'Todo'] and i.get('priority', 0) in [1, 2]
    ]
    pending_prs = [pr for pr in prs if pr['author'] != os.getenv("GITHUB_USERNAME")]

    if not pending_tasks and not pending_prs:
        return

    nudge_text = f"👀 <b>Hey Joshua, checking in...</b>\n<i>{SEP}</i>\n\n"

    if pending_tasks:
        nudge_text += "⚠️ <b>Still pending:</b>\n"
        for issue in pending_tasks[:3]:
            icon = PRIORITY_ICONS.get(issue.get("priority", 0), "·")
            nudge_text += f"  · {icon} {escape_md(issue['title'])}\n"

    if pending_prs:
        nudge_text += "\n🔀 <b>Awaiting your review:</b>\n"
        for pr in pending_prs[:3]:
            nudge_text += f"  · <a href='{pr['url']}'>{html.escape(pr['title'])}</a> <i>({html.escape(pr['repo'])})</i>\n"

    nudge_text += f"\n<i>{SEP}</i>\n<i>Stay focused! 🎯</i>"
    await bot.send_message(chat_id=YOUR_CHAT_ID, text=nudge_text, parse_mode='HTML')

async def handle_message(update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text:
        await update.message.reply_text("⚠️ I can only handle text messages for now!", parse_mode='HTML')
        return
    await update.message.reply_text("🤔 <i>Thinking...</i>", parse_mode='HTML')
    issues = get_linear_issues()
    events = get_todays_events()
    prs = get_pull_requests()
    day_context = f"""
Tasks: {[i['title'] + ' (' + i['state']['name'] + ')' for i in issues]}
Meetings today: {[e['summary'] for e in events]}
Open PRs: {[pr['title'] for pr in prs]}
"""
    response = ask_ai(update.message.text, context=day_context)
    await update.message.reply_text(response, parse_mode='HTML')

async def calendars(update, context: ContextTypes.DEFAULT_TYPE):
    from calendar_service import get_calendar_service
    service = get_calendar_service()
    all_calendars = []
    page_token = None
    while True:
        response = service.calendarList().list(pageToken=page_token).execute()
        all_calendars.extend(response['items'])
        page_token = response.get('nextPageToken')
        if not page_token:
            break
    count_label = f"{len(all_calendars)} calendar{'s' if len(all_calendars) != 1 else ''}"
    text = f"📅 <b>Your Calendars</b> — <i>{count_label}</i>\n\n"
    for cal in all_calendars:
        text += f"  · {cal['summary']}\n"
    await update.message.reply_text(text, parse_mode='HTML')
    
async def post_init(application):
    scheduler = AsyncIOScheduler(timezone="Africa/Douala")

    scheduler.add_job(
        send_scheduled_briefing,
        trigger='cron',
        hour=7,
        minute=0,
        args=[application.bot]
    )

    for hour in [10, 12, 15]:
        scheduler.add_job(
            send_nudge,
            trigger='cron',
            hour=hour,
            minute=0,
            args=[application.bot]
        )

    scheduler.start()

app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()

app.add_handler(CommandHandler("calendars", calendars))
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("briefing", briefing))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.run_polling()