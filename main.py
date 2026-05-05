import os
import logging
from dotenv import load_dotenv
from telegram import Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from linear import get_linear_issues
from calendar_service import get_todays_events

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
YOUR_CHAT_ID = os.getenv("CHAT_ID")

logging.basicConfig(level=logging.WARNING)

async def build_briefing_message():
    # Linear tasks
    issues = get_linear_issues()
    tasks_text = "📋 *Your Linear Tasks*\n"
    if issues:
        for issue in issues:
            tasks_text += f"• {issue['title']} — {issue['state']['name']}\n"
    else:
        tasks_text += "No tasks assigned\n"

    # Calendar events
    events = get_todays_events()
    calendar_text = "\n📅 *Today's Meetings*\n"
    if events:
        for event in events:
            time = event['start'].get('dateTime', 'All day')
            if 'T' in time:
                time = time[11:16]
            calendar_text += f"• {time} — {event['summary']}\n"
    else:
        calendar_text += "No meetings today\n"

    return f"🌅 *Good morning Joshua!*\n\n{tasks_text}{calendar_text}"

async def send_scheduled_briefing(bot: Bot):
    message = await build_briefing_message()
    await bot.send_message(
        chat_id=YOUR_CHAT_ID,
        text=message,
        parse_mode='Markdown'
    )

async def briefing(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Fetching your briefing...")
    message = await build_briefing_message()
    await update.message.reply_text(message, parse_mode='Markdown')

async def start(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello Joshua! 👋\nSend /briefing to get your morning briefing.")

async def post_init(application):
    scheduler = AsyncIOScheduler(timezone="Africa/Douala")
    scheduler.add_job(
        send_scheduled_briefing,
        trigger='cron',
        hour=7,
        minute=00,
        args=[application.bot]
    )
    scheduler.start()
    

app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("briefing", briefing))
app.run_polling()