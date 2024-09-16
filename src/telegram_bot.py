import logging
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from nhs_scraper import fetch_nhs_jobs
from google_sheets import get_user_chat_ids, add_user_chat_id, batch_update_jobs, get_most_recent_job
from datetime import datetime

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Telegram Bot Token
BOT_TOKEN = open('./secrets/telegram_bot_token.txt', 'r').read().strip()

# Set DEBUG_MODE
DEBUG_MODE = False  # Set this to False for production

def format_date(date_str):
    date_obj = datetime.strptime(date_str, '%d/%m/%Y')
    return date_obj.strftime('%d{} %B %Y').format(
        'th' if 11 <= date_obj.day <= 13 else 
        {1: 'st', 2: 'nd', 3: 'rd'}.get(date_obj.day % 10, 'th')
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    add_user_chat_id(chat_id)
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! You've been added to the job notification list.",
        reply_markup=ForceReply(selective=True),
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("This bot will notify you about new NHS job postings. Use /start to subscribe to notifications.")

async def check_jobs(context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Checking for new jobs...")
    new_jobs = fetch_nhs_jobs()
    truly_new_jobs = batch_update_jobs(new_jobs)
    
    if truly_new_jobs:
        message = "🚨 New job postings found!\n\n"
        for job in truly_new_jobs:
            message += format_job_message(job)
        
        user_chat_ids = get_user_chat_ids()
        for chat_id, is_debug in user_chat_ids:
            if not DEBUG_MODE or (DEBUG_MODE and is_debug):
                await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
    else:
        logger.info("No new jobs were added to the sheet.")
    
    if DEBUG_MODE:
        most_recent_job = get_most_recent_job()
        if most_recent_job:
            debug_message = f"Most recent job in the sheet:\n{format_job_message(most_recent_job)}"
            for chat_id, is_debug in get_user_chat_ids():
                if is_debug:
                    await context.bot.send_message(chat_id=chat_id, text=debug_message, parse_mode='HTML')

async def manual_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Manually checking for new jobs...")
    await check_jobs(context)
    await update.message.reply_text("Job check completed.")

def format_job_message(job):
    return (
        f"<b>{job['title']}</b>\n"
        f"Employer: {job['employer']}\n"
        f"Location: {job['location']}\n"
        f"Closing Date: {format_date(job['closing_date'])}\n"
        f"<a href='{job['url']}'>View Job</a>\n\n"
    )

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("check", manual_check))

    # Schedule the job to run every 5 minutes
    job_queue = application.job_queue
    job_queue.run_repeating(check_jobs, interval=300, first=10)

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()