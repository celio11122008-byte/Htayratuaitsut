# ---------------- IMPORTS ---------------- #

import telebot
import json
import os
import base64
import time
import threading

# ---------------- CONFIG ---------------- #

TOKEN = "8772869279:AAHuxhvC6kpeEjsjspUjtbBvIXkmp9Z54iQ"
ADMIN_ID = 8758830915

bot = telebot.TeleBot(
    TOKEN,
    threaded=True,
    num_threads=10
)

# ---------------- DATABASE FILES ---------------- #

DB_FILE = "files.json"
USERS_DB_FILE = "users.json"

CHANNEL_USERNAME = "@Burmese_Anime"
CHANNEL_LINK = "https://t.me/Burmese_Anime"

db_lock = threading.Lock()

# ---------------- LOAD DB ---------------- #

def load_json(file_path, default):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

files_db = load_json(DB_FILE, {})
users_db = set(load_json(USERS_DB_FILE, []))

# ---------------- SAVE ---------------- #

def save_db():
    with db_lock:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(files_db, f, indent=2, ensure_ascii=False)

def save_users():
    with db_lock:
        with open(USERS_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(list(users_db), f, indent=2, ensure_ascii=False)

# ---------------- HELPERS ---------------- #

def normalize(text):
    return str(text).lower().strip().replace(" ", "").replace("-", "").replace("_", "")

def encode_data(text):
    return base64.urlsafe_b64encode(text.encode()).decode()

def decode_data(text):
    return base64.urlsafe_b64decode(text.encode()).decode()

# ---------------- COPY MESSAGE CORE ---------------- #

def copy_single(chat_id, data, sent_list):
    try:
        msg = bot.copy_message(
            chat_id=chat_id,
            from_chat_id=data["chat_id"],
            message_id=data["message_id"]
        )
        sent_list.append(msg.message_id)
    except Exception as e:
        print("Copy Error:", e)

def fast_send(chat_id, files):
    sent = []
    threads = []

    for data in files:
        t = threading.Thread(
            target=copy_single,
            args=(chat_id, data, sent)
        )
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    warning = bot.send_message(
        chat_id,
        f"🎬 {len(sent)} Episodes Sent Successfully\n⚡ COPY MODE FAST"
    )

    sent.append(warning.message_id)

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

    uid = message.from_user.id
    cid = message.chat.id

    if uid not in users_db:
        users_db.add(uid)
        save_users()

    if not is_joined(uid):
        return join_message(cid)

    args = message.text.split(maxsplit=1)

    if len(args) > 1:
        try:
            key = normalize(decode_data(args[1]))
        except:
            return bot.send_message(cid, "❌ Invalid Link")

        matched = [
            f for f in files_db.values()
            if key in normalize(f["name"])
            or normalize(f["name"]) in key
        ]

        if matched:
            return fast_send(cid, matched)

        return bot.send_message(cid, "❌ Anime Not Found")

    bot.send_message(cid, "🎬 Send Anime Link")

# ---------------- UPLOAD (COPY SYSTEM FIX) ---------------- #

@bot.message_handler(content_types=['video', 'document', 'audio'])
def upload(message):

    if message.from_user.id != ADMIN_ID:
        return

    caption = message.caption or ""

    # file detect
    if message.video:
        file_type = "video"
    elif message.document:
        file_type = "document"
    elif message.audio:
        file_type = "audio"
    else:
        return

    file_unique = str(int(time.time() * 1000))

    # IMPORTANT: store message_id (NOT file_id)
    files_db[file_unique] = {
        "chat_id": message.chat.id,
        "message_id": message.message_id,
        "name": caption,
        "type": file_type
    }

    save_db()

    bot_username = bot.get_me().username

    encoded = encode_data(normalize(caption or file_unique))

    link = f"https://t.me/{bot_username}?start={encoded}"

    bot.send_message(
        message.chat.id,
        f"🎬 Saved Successfully\n\n🔗 {link}"
    )

# ---------------- JOIN CHECK ---------------- #

def is_joined(uid):
    try:
        m = bot.get_chat_member(CHANNEL_USERNAME, uid)
        return m.status in ["member", "creator", "administrator"]
    except:
        return False

def join_message(cid):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("Join Channel", url=CHANNEL_LINK)
    )

    bot.send_message(
        cid,
        "❌ Please join channel first",
        reply_markup=markup
    )

# ---------------- RUN ---------------- #

print("🚀 COPY MESSAGE BOT RUNNING...")

while True:
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print("Restart:", e)
        time.sleep(3)
