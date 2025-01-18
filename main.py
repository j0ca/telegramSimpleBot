import requests
import logging
import json
import asyncio
import yaml
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# strings and url
noActiveOfferString = "Não temos nenhuma campanha especial, de momento."
url = "https://www.wizink.pt/public/campanha-especial"

# subscribers users storage
SUBSCRIFERS_FILE="subscribers.json"
# subscribers = set() # set to store unique IDs

def load_config(filename):
    with open(filename, "r") as file:
        return yaml.safe_load(file)

# Load subscriptors from file
def load_subscribers():
    try:
        with open(SUBSCRIFERS_FILE, "r") as file:
            return set(json.load(file))
    except FileNotFoundError:
        return set()

# save subscribers to file
def save_subscribers(subscribers):
    with open (SUBSCRIFERS_FILE, "w") as file:
        json.dump(list(subscribers),file)

# initialize subscribers
subscribers = load_subscribers()


# Handle non recognized commands
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry. Command not found!")

# start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Hi! I'll let you know the active offers in Wizink PT website.\nUse /subscribe to be added to the list.\nUse /unsubscribe to be removed from the list.\nUse /offers to check current offers.\nTry them!")

# Subscribe command
async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    if user_id not in subscribers:
        subscribers.add(user_id)
        save_subscribers(subscribers)
        await context.bot.send_message(chat_id=user_id, text="You have subscribed to the offer notifications!")
    else:
        await context.bot.send_message(chat_id=user_id, text="You are already subscrived.")

# Unsubscribe command
async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    if user_id in subscribers:
        subscribers.remove(user_id)
        save_subscribers(subscribers)
        await context.bot.send_message(chat_id=user_id, text="You have unsubscribed to the offer notifications.")
    else:
        await context.bot.send_message(chat_id=user_id, text="You are not subscribed")

# Check subscription status command
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    if user_id in subscribers:
        await context.bot.send_message(chat_id=user_id, text="You are subscribed to offer notifications!")
    else:
        await context.bot.send_message(chat_id=user_id, text="You are not subscribed to offer notifications.")


# Check and notify subscribers about offers
async def offers(context: ContextTypes.DEFAULT_TYPE):
    data = requests.get(url)
    message = check_offer(data)
    for user_id in subscribers:
        try:
            await context.bot.send_message(chat_id=user_id,text=message)
        except Exception as e:
            logging.warning(f"Failed to send message to {user_id}: {e}")

async def offers_scheduled(bot):
    data = requests.get(url)
    message = check_offer(data) 
    for user_id in subscribers:
        try:
            await bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            logging.warning(f"Failed to send message to {user_id}: {e}")


def check_offer(data):
    if data.status_code == requests.status_codes.codes.ok:
        if noActiveOfferString in data.text:
            return "[!] No Active Offers"
        else:
            return f"[:)] There's an active offer. Please visit {url}"
        
    else:
        return f"[!] Non expected reponse. Status code: {data.status_code}"

# Function to schedule the job
def schedule_job(application):
    async def scheduled_offers():
        await offers_scheduled(application.bot)

    def job_function():
        asyncio.run(scheduled_offers())

    # Initialize and configure the scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(job_function, 'cron', hour=8, minute=30)  # Run daily at 08:00 AM
    scheduler.start()


def main():
    #data = requests.get(url)
    config = load_config(filename)
    TOKEN = config["settings"]["token"]
    name = config["settings"]["name"]
    botName = config["settings"]["botName"]
    SUBSCRIFERS_FILE=config["settings"]["subscribersFile"]

    application = ApplicationBuilder().token(TOKEN).build()

    # Commands
    start_handler = CommandHandler("Start", start)
    subscribe_handler = CommandHandler("subscribe", subscribe)
    unsubscribe_handler = CommandHandler("unsubscribe", unsubscribe)
    status_handler = CommandHandler("Status", status)
    offers_handler = CommandHandler("offers", lambda update, context: context.application.create_task(offers(context)))

    application.add_handler(start_handler)
    application.add_handler(subscribe_handler)
    application.add_handler(unsubscribe_handler)
    application.add_handler(status_handler)
    application.add_handler(offers_handler)

    # Other handlers
    # Needs to be the last handler
    unknown_handler = MessageHandler(filters.COMMAND, unknown)
    application.add_handler(unknown_handler)

    # Schedule the daily job
    schedule_job(application)

    # start bot
    application.run_polling()
    
if __name__ == "__main__":
    main()