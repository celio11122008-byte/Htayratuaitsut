import telebot
import json
import os
import base64
import time
import threading
import re

# ---------------- CONFIG ---------------- #

TOKEN = "8772869279:AAGubBxoOeB2NI6zke8YbuYGDGZ4_9ibLE0"
ADMIN_ID = 8758830915

bot = telebot.TeleBot(TOKEN, threaded=True, num_threads=10)

DB_FILE = "files.json"
USERS_DB_FILE = "users.json"

CHANNEL_USERNAME = "@Burmese_Anime"
CHANNEL_LINK = "https://t.me/Burmese_Anime"

db_lock = threading.Lock()

# ---------------- LOAD DB ---------------- #

def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return default


files_db = load_json(DB_FILE, {})
users_db = set(load_json(USERS_DB_FILE, []))

# ---------------- SAVE ---------------- #

def save_files():
    with db_lock:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(files_db, f, indent=4, ensure_ascii=False)

def save_users():
    with db_lock:
        with open(USERS_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(list(users_db), f, indent=4, ensure_ascii=False)

# ---------------- HELPERS ---------------- #

def normalize(text):
    return str(text).lower().replace(" ", "").replace("-", "").replace("_", "")

def decode_data(text):
    try:
        return base64.urlsafe_b64decode(text.encode()).decode()
    except:
        return None

def encode_data(text):
    return base64.urlsafe_b64encode(text.encode()).decode()

# ✅ SAFE EPISODE SORT (IMPORTANT FIX)
def get_episode_number(name):
    name = str(name).lower()

    match = re.search(r'(?:ep|episode|e)\s*0*(\d+)', name)
    if match:
        return int(match.group(1))

    return 999999

# ---------------- CHANNEL CHECK ---------------- #

def is_joined(user_id):
    try:
        m = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

def join_message(chat_id):
    bot.send_message(
        chat_id,
        "❌ Please join channel first:\n" + CHANNEL_LINK
    )

# ---------------- SEND FILE ---------------- #

def send_single(chat_id, data, out):
    try:
        msg = None

        if data["type"] == "document":
            msg = bot.send_document(chat_id, data["file_id"], caption=data.get("caption",""))

        elif data["type"] == "video":
            msg = bot.send_video(chat_id, data["file_id"], caption=data.get("caption",""), supports_streaming=True)

        elif data["type"] == "audio":
            msg = bot.send_audio(chat_id, data["file_id"], caption=data.get("caption",""))

        if msg:
            out.append(msg.message_id)

    except Exception as e:
        print("SEND ERROR:", e)

def fast_send(chat_id, files):
    sent = []
    threads = []

    for f in files:
        t = threading.Thread(target=send_single, args=(chat_id, f, sent))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    bot.send_message(chat_id, f"✅ Sent {len(sent)} files")

# ---------------- START ---------------- #

@bot.message_handler(commands=['start'])
def start(message):
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id

        users_db.add(user_id)
        save_users()

        if not is_joined(user_id):
            join_message(chat_id)
            return

        args = message.text.split(maxsplit=1)

        # ---------------- SEARCH MODE ---------------- #
        if len(args) > 1:
            decoded = decode_data(args[1])

            if not decoded:
                return bot.send_message(chat_id, "❌ Invalid Link")

            keyword = normalize(decoded)

            matched = []

            for data in files_db.values():
                name = normalize(data["name"])

                if keyword in name or name in keyword:
                    matched.append(data)

            if not matched:
                return bot.send_message(chat_id, "❌ Not Found")

            matched.sort(key=lambda x: get_episode_number(x["name"]))

            return fast_send(chat_id, matched)

        # ---------------- NORMAL START ---------------- #
        bot.send_message(chat_id,
            f"""🎬 Anime Bot

👤 ID: {user_id}
📦 Files: {len(files_db)}

Send anime link to get episodes
"""
        )

    except Exception as e:
        print("START ERROR:", e)

# ---------------- UPLOAD ---------------- #

@bot.message_handler(content_types=['document','video','audio'])
def upload(message):
    if message.from_user.id != ADMIN_ID:
        return

    caption = message.caption or "Anime"

    if message.document:
        file_id = message.document.file_id
        ftype = "document"
        name = caption

    elif message.video:
        file_id = message.video.file_id
        ftype = "video"
        name = caption

    elif message.audio:
        file_id = message.audio.file_id
        ftype = "audio"
        name = caption

    file_id_key = str(int(time.time()*1000))

    files_db[file_id_key] = {
        "file_id": file_id,
        "type": ftype,
        "name": name,
        "caption": caption
    }

    save_files()

    link = f"https://t.me/{bot.get_me().username}?start={encode_data(name)}"

    bot.reply_to(message, f"✅ Saved\n\n🔗 {link}")

# ---------------- RUN ---------------- #

print("BOT RUNNING...")

while True:
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print("BOT CRASH:", e)
        time.sleep(5)
