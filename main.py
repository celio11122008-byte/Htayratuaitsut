# ---------------- IMPORTS ---------------- #

import telebot
import json
import os
import time
import threading

# ---------------- CONFIG ---------------- #

TOKEN = "8772869279:AAHuxhvC6kpeEjsjspUjtbBvIXkmp9Z54iQ"
ADMIN_ID = 8758830915

bot = telebot.TeleBot(TOKEN, threaded=True, num_threads=10)

# ---------------- DATABASE ---------------- #

DB_FILE = "files.json"
USERS_FILE = "users.json"

db_lock = threading.Lock()

def load_json(file, default):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


files_db = load_json(DB_FILE, {})
users_db = set(load_json(USERS_FILE, []))


def save_files():
    with db_lock:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(files_db, f, indent=4, ensure_ascii=False)


def save_users():
    with db_lock:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(users_db), f, indent=4, ensure_ascii=False)


# ---------------- HELPERS ---------------- #

def normalize(text):
    return str(text).lower().replace(" ", "").replace("-", "").replace("_", "")


def is_joined(user_id):
    return True  # optional channel check disable (simplified)


# ---------------- AUTO DELETE ---------------- #

def auto_delete(chat_id, msg_ids):
    time.sleep(300)
    for mid in msg_ids:
        try:
            bot.delete_message(chat_id, mid)
        except:
            pass


# ---------------- SEND (COPY MESSAGE) ---------------- #

def send_single(chat_id, data, sent):
    try:
        msg = bot.copy_message(
            chat_id=chat_id,
            from_chat_id=data["chat_id"],
            message_id=data["message_id"],
            caption=data.get("caption", "")
        )
        sent.append(msg.message_id)
    except Exception as e:
        print("Copy error:", e)


def fast_send(chat_id, files):
    sent = []
    threads = []

    for f in files:
        t = threading.Thread(target=send_single, args=(chat_id, f, sent))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    warn = bot.send_message(chat_id, f"✅ Sent {len(sent)} files\n⏳ Auto delete in 5 min")
    sent.append(warn.message_id)

    threading.Thread(target=auto_delete, args=(chat_id, sent), daemon=True).start()


# ---------------- START ---------------- #

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    users_db.add(user_id)
    save_users()

    args = message.text.split(maxsplit=1)

    if len(args) > 1:
        keyword = normalize(args[1])

        matched = [
            f for f in files_db.values()
            if keyword in normalize(f["name"])
        ]

        if matched:
            return fast_send(chat_id, matched)

        return bot.send_message(chat_id, "❌ Not found")

    bot.send_message(chat_id,
        f"🎬 Anime Bot Ready\nFiles: {len(files_db)}"
    )


# ---------------- UPLOAD (ADMIN ONLY) ---------------- #

@bot.message_handler(content_types=['document', 'video', 'audio'])
def upload(message):
    if message.from_user.id != ADMIN_ID:
        return bot.reply_to(message, "❌ Admin only")

    caption = message.caption or "Anime"

    file_data = {
        "chat_id": message.chat.id,
        "message_id": message.message_id,
        "name": caption,
        "caption": caption,
        "added": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    file_id = str(int(time.time() * 1000))
    files_db[file_id] = file_data
    save_files()

    bot.reply_to(message, f"✅ Saved\nID: {file_id}")


# ---------------- DELETE ---------------- #

@bot.message_handler(commands=['delete'])
def delete(message):
    if message.from_user.id != ADMIN_ID:
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return bot.reply_to(message, "Use /delete id")

    fid = args[1]

    if fid in files_db:
        del files_db[fid]
        save_files()
        bot.reply_to(message, "✅ Deleted")
    else:
        bot.reply_to(message, "❌ Not found")


# ---------------- STATS ---------------- #

@bot.message_handler(commands=['stats'])
def stats(message):
    if message.from_user.id != ADMIN_ID:
        return

    bot.send_message(message.chat.id,
        f"""
📊 Stats
Users: {len(users_db)}
Files: {len(files_db)}
"""
    )


# ---------------- RUN ---------------- #

print("Bot running...")

while True:
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print("Error:", e)
        time.sleep(5)
