import telebot
import json
import os
import time
import threading
import string
import random

TOKEN = "8772869279:AAHuxhvC6kpeEjsjspUjtbBvIXkmp9Z54iQ"
ADMIN_ID = 8758830915

bot = telebot.TeleBot(TOKEN, threaded=True)

DB_FILE = "files.json"
USERS_FILE = "users.json"

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

# ---------------- SHORT ID ---------------- #

def gen_short_id():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))

# ---------------- COPY MESSAGE CORE ---------------- #

def copy_single(chat_id, data, sent):
    try:
        msg = bot.copy_message(
            chat_id=chat_id,
            from_chat_id=data["chat_id"],
            message_id=data["message_id"]
        )
        sent.append(msg.message_id)
    except:
        pass

def fast_send(chat_id, episodes):
    sent = []
    threads = []

    for ep in episodes:
        t = threading.Thread(
            target=copy_single,
            args=(chat_id, ep, sent)
        )
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    warn = bot.send_message(
        chat_id,
        f"🎬 Sent {len(sent)} Episodes (COPY MODE ⚡)"
    )

    sent.append(warn.message_id)

    threading.Thread(
        target=auto_delete,
        args=(chat_id, sent),
        daemon=True
    ).start()

# ---------------- AUTO DELETE ---------------- #

def auto_delete(chat_id, msg_ids):
    time.sleep(300)
    for mid in msg_ids:
        try:
            bot.delete_message(chat_id, mid)
        except:
            pass

# ---------------- START ---------------- #

@bot.message_handler(commands=['start'])
def start(message):

    cid = message.chat.id
    uid = message.from_user.id

    if uid not in users_db:
        users_db.add(uid)
        save_users()

    args = message.text.split(maxsplit=1)

    if len(args) > 1:
        key = args[1]

        if key in files_db:
            return fast_send(cid, files_db[key]["episodes"])

    bot.send_message(cid, "🎬 Send or open anime link")

# ---------------- UPLOAD ---------------- #

@bot.message_handler(content_types=['video','document','audio'])
def upload(message):

    if message.from_user.id != ADMIN_ID:
        return

    caption = message.caption or "Unknown"

    if message.video:
        file_type = "video"
    elif message.document:
        file_type = "document"
    elif message.audio:
        file_type = "audio"
    else:
        return

    # SHORT SERIES ID
    series_id = gen_short_id()

    files_db[series_id] = {
        "name": caption,
        "episodes": []
    }

    files_db[series_id]["episodes"].append({
        "chat_id": message.chat.id,
        "message_id": message.message_id,
        "name": caption,
        "type": file_type
    })

    save_files()

    bot_username = bot.get_me().username

    link = f"https://t.me/{bot_username}?start={series_id}"

    bot.send_message(
        message.chat.id,
        f"🎬 SHORT LINK CREATED\n\n🔗 {link}"
    )

print("🚀 SHORT LINK COPY BOT RUNNING...")

while True:
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print("Restart:", e)
        time.sleep(3)
