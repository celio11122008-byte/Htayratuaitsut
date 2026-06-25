# ---------------- IMPORTS ---------------- #

import telebot
import json
import os
import base64
import time
import threading
import traceback

# ---------------- CONFIG ---------------- #

TOKEN = "8772869279:AAHuxhvC6kpeEjsjspUjtbBvIXkmp9Z54iQ"
ADMIN_ID = 8758830915

bot = telebot.TeleBot(
    TOKEN,
    threaded=True,
    num_threads=20
)

# ---------------- DATABASE FILES ---------------- #

DB_FILE = "files.json"
USERS_DB_FILE = "users.json"

CHANNEL_USERNAME = "@Burmese_Anime"
CHANNEL_LINK = "https://t.me/Burmese_Anime"

db_lock = threading.Lock()

# ---------------- LOAD DB ---------------- #

def load_json(file_path, default):
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


files_db = load_json(DB_FILE, {})
users_db = set(load_json(USERS_DB_FILE, []))


# ---------------- SAVE SAFE ---------------- #

def save_db():
    with db_lock:
        tmp = DB_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(files_db, f, indent=2, ensure_ascii=False)
        os.replace(tmp, DB_FILE)


def save_users():
    with db_lock:
        tmp = USERS_DB_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(list(users_db), f, indent=2, ensure_ascii=False)
        os.replace(tmp, USERS_DB_FILE)


# ---------------- HELPERS ---------------- #

def normalize(text):
    return str(text).lower().strip().replace(" ", "").replace("-", "").replace("_", "") if text else ""


def encode_data(text):
    return base64.urlsafe_b64encode(text.encode()).decode()


def decode_data(text):
    return base64.urlsafe_b64decode(text.encode()).decode()


def is_joined(user_id):
    try:
        m = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return m.status in ("creator", "administrator", "member")
    except:
        return False


def join_message(chat_id):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)
    )

    bot.send_message(
        chat_id,
        "❌ Join channel first, then use bot again.",
        reply_markup=markup
    )


# ---------------- AUTO DELETE ---------------- #

def auto_delete(chat_id, message_ids):
    time.sleep(300)
    for mid in message_ids:
        try:
            bot.delete_message(chat_id, mid)
        except:
            pass


# ---------------- FAST COPY SEND ---------------- #

def send_single(chat_id, data, sent_list):
    try:
        msg = bot.copy_message(
            chat_id,
            data["from_chat_id"],
            data["message_id"]
        )
        sent_list.append(msg.message_id)
    except Exception as e:
        print("Copy Error:", e)


def fast_send(chat_id, files):
    sent = []
    threads = []

    for f in files:
        t = threading.Thread(target=send_single, args=(chat_id, f, sent))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    warn = bot.send_message(
        chat_id,
        f"✅ Sent: {len(sent)} files\n⚠️ Auto delete in 5 min"
    )

    sent.append(warn.message_id)

    threading.Thread(target=auto_delete, args=(chat_id, sent), daemon=True).start()


# ---------------- START ---------------- #

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if user_id not in users_db:
        users_db.add(user_id)
        save_users()

    if not is_joined(user_id):
        return join_message(chat_id)

    args = message.text.split(maxsplit=1)

    if len(args) > 1:
        try:
            keyword = normalize(decode_data(args[1]))
        except:
            return bot.send_message(chat_id, "❌ Invalid link")

        matched = [
            d for d in files_db.values()
            if keyword in normalize(d["name"])
        ]

        if matched:
            return fast_send(chat_id, matched)

        return bot.send_message(chat_id, "❌ Not found")

    bot.send_message(chat_id,
        f"🎬 Anime Bot\n\n👤 ID: {user_id}\n📦 Files: {len(files_db)}"
    )


# ---------------- UPLOAD ---------------- #

@bot.message_handler(content_types=['document', 'video', 'audio'])
def upload(message):

    if message.from_user.id != ADMIN_ID:
        return bot.reply_to(message, "❌ Admin only")

    caption = message.caption or ""

    if message.document:
        file_name = caption or message.document.file_name
    elif message.video:
        file_name = caption or "video"
    elif message.audio:
        file_name = caption or "audio"
    else:
        return

    file_id = getattr(message, message.content_type).file_id

    file_key = str(int(time.time() * 1000))

    files_db[file_key] = {
        "file_id": file_id,
        "name": file_name,
        "type": message.content_type,
        "caption": caption,
        "from_chat_id": message.chat.id,
        "message_id": message.message_id
    }

    save_db()

    bot.reply_to(message, f"✅ Saved\n📦 {file_name}")


# ---------------- DELETE ---------------- #

@bot.message_handler(commands=['delete'])
def delete(message):
    if message.from_user.id != ADMIN_ID:
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return

    key = args[1].strip()

    if key in files_db:
        del files_db[key]
        save_db()
        bot.reply_to(message, "✅ Deleted")
    else:
        bot.reply_to(message, "❌ Not found")


# ---------------- BACKUP ---------------- #

@bot.message_handler(commands=['backup'])
def backup(message):
    if message.from_user.id != ADMIN_ID:
        return

    data = {
        "files": files_db,
        "users": list(users_db)
    }

    with open("backup.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    with open("backup.json", "rb") as f:
        bot.send_document(message.chat.id, f)

    os.remove("backup.json")


# ---------------- ERROR SAFE POLLING ---------------- #

print("Bot Running...")

while True:
    try:
        bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
    except Exception as e:
        print("Polling Error:", e)
        traceback.print_exc()
        time.sleep(5)
