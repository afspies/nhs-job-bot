import logging
import sys
import asyncio
import signal
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from nhs_scraper import fetch_nhs_jobs
from google_sheets import get_all_job_urls, get_user_chat_ids, add_user_chat_id, batch_update_jobs, get_most_recent_job
from datetime import datetime
from gspread.exceptions import APIError

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Telegram Bot Token
BOT_TOKEN = open('./secrets/telegram_bot_token.txt', 'r').read().strip()

def format_date(date_str):
    date_obj = datetime.strptime(date_str, '%d/%m/%Y')
    return date_obj.strftime('%d{} %B %Y').format(
        'th' if 11 <= date_obj.day <= 13 else 
        {1: 'st', 2: 'nd', 3: 'rd'}.get(date_obj.day % 10, 'th')
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    try:
        add_user_chat_id(chat_id)
        await update.message.reply_html(
            rf"Hi {user.mention_html()}! You've been added to the job notification list.",
            reply_markup=ForceReply(selective=True),
        )
    except APIError as e:
        logger.error(f"Error adding user to chat list: {e}")
        await update.message.reply_text("Sorry, there was an error adding you to the notification list. Please try again later.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("This bot will notify you about new NHS job postings. Use /start to subscribe to notifications.")

async def check_for_new_jobs(context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Checking for new jobs...")
    try:
        new_jobs = fetch_nhs_jobs()
    except Exception as e:
        logger.error(f"Error fetching new jobs: {e}")
        return

    try:
        batch_update_jobs(new_jobs)
    except APIError as e:
        logger.error(f"Error updating jobs in Google Sheets: {e}")

    try:
        existing_urls = set(get_all_job_urls())
    except APIError as e:
        logger.error(f"Error fetching existing job URLs: {e}")
        return

    truly_new_jobs = [job for job in new_jobs if job['url'] not in existing_urls]
    
    message = "🚨 New job postings found!\n\n" if truly_new_jobs else "No new jobs found.\n\n"
    
    if truly_new_jobs:
        for job in truly_new_jobs:
            message += format_job_message(job)
    
    most_recent_job = get_most_recent_job()
    debug_message = message + "\nMost recent job scraped:\n" + format_job_message(most_recent_job) if most_recent_job else message
    
    try:
        user_chat_ids = get_user_chat_ids()
    except APIError as e:
        logger.error(f"Error fetching user chat IDs: {e}")
        return

    for chat_id, is_debug in user_chat_ids:
        try:
            if is_debug or truly_new_jobs:
                await context.bot.send_message(
                    chat_id=chat_id, 
                    text=debug_message if is_debug else message, 
                    parse_mode='HTML'
                )
        except Exception as e:
            logger.error(f"Error sending message to {chat_id}: {e}")

def format_job_message(job):
    return (
        f"<b>{job['title']}</b>\n"
        f"Employer: {job['employer']}\n"
        f"Location: {job['location']}\n"
        f"Closing Date: {format_date(job['closing_date'])}\n"
        f"<a href='{job['url']}'>View Job</a>\n\n"
    )

async def notify_debug_users(context: ContextTypes.DEFAULT_TYPE, message: str) -> None:
    try:
        user_chat_ids = get_user_chat_ids()
        for chat_id, is_debug in user_chat_ids:
            if is_debug:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='HTML'
                )
    except Exception as e:
        logger.error(f"Error notifying debug users: {e}")

def main() -> None:
    # Create the Application and pass it your bot's token
    application = Application.builder().token(BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Set up job to run periodically
    application.job_queue.run_repeating(check_for_new_jobs, interval=900, first=10)  # Run every 15 minutes, with a 10-second initial delay

    # Set up error handler
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error("Exception while handling an update:", exc_info=context.error)
        await notify_debug_users(context, f"🚨 Bot crashed with error: {context.error}")

    application.add_error_handler(error_handler)

    # Notify debug users on startup
    application.job_queue.run_once(
        lambda ctx: notify_debug_users(ctx, "🟢 Bot has started"),
        when=0
    )

    async def shutdown(signal, loop):
        logger.info(f"Received exit signal {signal.name}...")
        await notify_debug_users(application, "🔴 Bot is shutting down")
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        [task.cancel() for task in tasks]
        await asyncio.gather(*tasks, return_exceptions=True)
        loop.stop()

    # Run the bot until the user presses Ctrl-C
    try:
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(s, loop)))

        logger.info("Starting bot...")
        loop.run_until_complete(application.run_polling(allowed_updates=Update.ALL_TYPES))
    finally:
        logger.info("Bot stopped.")

if __name__ == "__main__":
    main()