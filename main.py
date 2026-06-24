import telebot
import json
import os
import time
import threading
import base64
import re

# ---------------- CONFIG ---------------- #

TOKEN = "8772869279:AAHo18Q2T_UohwQSE-wj1EXfpo66O2_Zk84"
ADMIN_ID = 8758830915

UPLOAD_CHANNEL = "@tuukqutwulsiliysiluysgksilut"
MAIN_CHANNEL = "@Burmese_Anime"

bot = telebot.TeleBot(TOKEN)

DB_FILE = "files.json"
USERS_FILE = "users.json"

db_lock = threading.Lock()

# ---------------- LOAD DB ---------------- #

def load(file, default):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

files_db = load(DB_FILE, {})
users_db = set(load(USERS_FILE, []))

def save_files():
    with db_lock:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(files_db, f, indent=2, ensure_ascii=False)

def save_users():
    with db_lock:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(users_db), f, indent=2, ensure_ascii=False)

# ---------------- HELPERS ---------------- #

def normalize(text):
    return str(text).lower().replace(" ", "").replace("-", "").replace("_", "")

def encode(text):
    return base64.urlsafe_b64encode(text.encode()).decode()

def decode(text):
    return base64.urlsafe_b64decode(text.encode()).decode()

def get_ep(name):
    match = re.search(r"(?:ep|episode|e)\s*(\d+)", name.lower())
    return int(match.group(1)) if match else 999999

# ---------------- CHANNEL CHECK ---------------- #

def is_joined(user_id):
    try:
        m = bot.get_chat_member(MAIN_CHANNEL, user_id)
        return m.status in ["member", "creator", "administrator"]
    except:
        return False

# ---------------- FAST SEND ---------------- #

def send_file(chat_id, data):
    if data["type"] == "video":
        return bot.send_video(chat_id, data["file_id"], caption=data.get("caption", ""))
    elif data["type"] == "document":
        return bot.send_document(chat_id, data["file_id"], caption=data.get("caption", ""))
    elif data["type"] == "audio":
        return bot.send_audio(chat_id, data["file_id"], caption=data.get("caption", ""))

def fast_send(chat_id, files):
    sent = []

    # EP ORDER
    files = sorted(files, key=lambda x: get_ep(x["name"]))

    for f in files:
        try:
            msg = send_file(chat_id, f)
            sent.append(msg.message_id)
        except:
            pass

    warn = bot.send_message(chat_id, f"✅ Sent {len(sent)} episodes\n⏳ Auto delete in 5 min")
    sent.append(warn.message_id)

    threading.Thread(target=auto_delete, args=(chat_id, sent), daemon=True).start()

def auto_delete(chat_id, msg_ids):
    time.sleep(300)
    for i in msg_ids:
        try:
            bot.delete_message(chat_id, i)
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
        return bot.send_message(cid, "❌ Join channel first")

    args = message.text.split(maxsplit=1)

    if len(args) > 1:
        try:
            key = normalize(decode(args[1]))
        except:
            return bot.send_message(cid, "❌ Invalid link")

        matched = [
            f for f in files_db.values()
            if key in normalize(f["name"])
        ]

        if matched:
            return fast_send(cid, matched)

        return bot.send_message(cid, "❌ Not found")

    bot.send_message(cid, "🎬 Anime Bot Ready")

# ---------------- UPLOAD ---------------- #

@bot.message_handler(content_types=['video', 'document', 'audio'])
def upload(message):
    if message.from_user.id != ADMIN_ID:
        return

    caption = message.caption or ""

    if message.video:
        file_id = message.video.file_id
        ftype = "video"
        name = caption or "video"

    elif message.document:
        file_id = message.document.file_id
        ftype = "document"
        name = caption or message.document.file_name

    elif message.audio:
        file_id = message.audio.file_id
        ftype = "audio"
        name = caption or "audio"

    file_id_key = str(int(time.time()*1000))

    files_db[file_id_key] = {
        "file_id": file_id,
        "name": name,
        "type": ftype,
        "caption": caption
    }

    save_files()

    link = encode(normalize(name.split("ep")[0].strip()))
    bot.send_message(message.chat.id, f"🔗 https://t.me/{bot.get_me().username}?start={link}")

# ---------------- STABLE RUN (FIX 409) ---------------- #

print("Bot running...")

while True:
    try:
        bot.infinity_polling(
            skip_pending=True,
            timeout=20,
            long_polling_timeout=20
        )
    except Exception as e:
        print("Restarting bot:", e)
        time.sleep(5)
