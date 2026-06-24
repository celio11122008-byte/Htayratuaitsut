import telebot
import json
import os
import time
import threading
import re

TOKEN = "8772869279:AAHuxhvC6kpeEjsjspUjtbBvIXkmp9Z54iQ"
ADMIN_ID = 8758830915

bot = telebot.TeleBot(TOKEN, threaded=True)

DB_FILE = "files.json"
USERS_FILE = "users.json"
BACKUP_DIR = "backup"

lock = threading.Lock()

# ---------------- LOAD ---------------- #

def load(file, default):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

files_db = load(DB_FILE, {})
users_db = set(load(USERS_FILE, []))

# ---------------- SAVE ---------------- #

def save_files():
    with lock:
        json.dump(files_db, open(DB_FILE, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

def save_users():
    with lock:
        json.dump(list(users_db), open(USERS_FILE, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

# ---------------- SERIES NAME FROM CAPTION ---------------- #

def normalize(t):
    return str(t).lower().replace(" ", "").replace("-", "").replace("_", "")

def get_series_name(caption):
    if not caption:
        return "unknown"

    text = caption.lower()
    text = re.sub(r"(ep|episode|e|s\d+)\s*\d+", "", text)
    text = re.sub(r"[^a-z0-9 ]", "", text)

    return normalize(text.strip())

# ---------------- COPY MESSAGE SEND (FAST) ---------------- #

def send_all(cid, series_id):
    if series_id not in files_db:
        return bot.send_message(cid, "❌ Not Found")

    episodes = files_db[series_id]["episodes"]

    sent = []

    for ep in sorted(episodes, key=lambda x: x["name"]):
        try:
            msg = bot.copy_message(
                chat_id=cid,
                from_chat_id=ep["chat_id"],
                message_id=ep["message_id"]
            )
            sent.append(msg.message_id)
        except:
            pass

    bot.send_message(cid, f"🎬 Sent {len(sent)} Episodes")

# ---------------- BACKUP SYSTEM ---------------- #

def make_backup():
    try:
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)

        ts = time.strftime("%Y%m%d_%H%M%S")

        with open(f"{BACKUP_DIR}/files_{ts}.json", "w", encoding="utf-8") as f:
            json.dump(files_db, f, indent=2, ensure_ascii=False)

        with open(f"{BACKUP_DIR}/users_{ts}.json", "w", encoding="utf-8") as f:
            json.dump(list(users_db), f, indent=2, ensure_ascii=False)

        return f"✅ Backup Done: {ts}"

    except Exception as e:
        return f"❌ Backup Failed: {e}"

def backup_loop():
    while True:
        make_backup()
        time.sleep(300)

threading.Thread(target=backup_loop, daemon=True).start()

# ---------------- /BACKUP COMMAND ---------------- #

@bot.message_handler(commands=['backup'])
def backup_cmd(message):
    if message.from_user.id != ADMIN_ID:
        return

    result = make_backup()
    bot.send_message(message.chat.id, result)

# ---------------- START ---------------- #

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    cid = message.chat.id

    if uid not in users_db:
        users_db.add(uid)
        save_users()

    args = message.text.split(maxsplit=1)

    if len(args) > 1:
        key = args[1]

        # SAFE LINK MODE (no encode)
        if key in files_db:
            return send_all(cid, key)

    bot.send_message(cid, "🎬 Send Anime Name or Click Link")

# ---------------- UPLOAD ---------------- #

@bot.message_handler(content_types=['video','document','audio'])
def upload(message):
    if message.from_user.id != ADMIN_ID:
        return

    caption = message.caption or ""

    if message.video:
        name = caption or "video"
    elif message.document:
        name = caption or message.document.file_name
    elif message.audio:
        name = caption or "audio"

    series_id = get_series_name(caption)

    if series_id not in files_db:
        files_db[series_id] = {
            "name": caption,
            "episodes": []
        }

    files_db[series_id]["episodes"].append({
        "chat_id": message.chat.id,
        "message_id": message.message_id,
        "name": name
    })

    save_files()

    link = f"https://t.me/{bot.get_me().username}?start={series_id}"

    bot.send_message(message.chat.id, f"🎬 All Episodes Link:\n{link}")

print("🚀 Bot Running...")

while True:
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print("Restarting bot:", e)
        time.sleep(3)
