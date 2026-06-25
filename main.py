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

# ---------------- CHANNEL ---------------- #

CHANNEL_USERNAME = "@Burmese_Anime"
CHANNEL_LINK = "https://t.me/Burmese_Anime"

db_lock = threading.Lock()


# ---------------- LOAD DB ---------------- #

def load_json(file_path, default):
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Load Error ({file_path}): {e}")
    return default


files_db = load_json(DB_FILE, {})
users_db = set(load_json(USERS_DB_FILE, []))


def save_db():
    with db_lock:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(files_db, f, indent=4, ensure_ascii=False)


def save_users():
    with db_lock:
        with open(USERS_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(list(users_db), f, indent=4, ensure_ascii=False)


# ---------------- HELPERS ---------------- #

def normalize(text):
    if not text:
        return ""
    return str(text).lower().strip().replace(" ", "").replace("-", "").replace("_", "")


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
        "❌ Please Join Channel First\n\nပြီးမှ Bot ကို ပြန်သုံးပါ",
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


# ---------------- FAST SEND (COPY MODE) ---------------- #

def send_single_file(chat_id, data, sent_messages):
    try:
        msg = bot.copy_message(
            chat_id=chat_id,
            from_chat_id=data["from_chat_id"],
            message_id=data["message_id"]
        )
        sent_messages.append(msg.message_id)

    except Exception as e:
        print(f"Send Error: {e}")


def fast_send(chat_id, files):
    sent_messages = []
    threads = []

    for data in files:
        t = threading.Thread(
            target=send_single_file,
            args=(chat_id, data, sent_messages)
        )
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    warning = bot.send_message(
        chat_id,
        f"✅ {len(sent_messages)} Files Sent\n⚠️ Auto delete in 5 min"
    )

    sent_messages.append(warning.message_id)

    threading.Thread(
        target=auto_delete,
        args=(chat_id, sent_messages),
        daemon=True
    ).start()


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
            return bot.send_message(chat_id, "❌ Invalid Link")

        matched = [
            d for d in files_db.values()
            if keyword in normalize(d["name"])
        ]

        if matched:
            return fast_send(chat_id, matched)

        return bot.send_message(chat_id, "❌ Not Found")

    bot.send_message(chat_id, f"""
🎬 Anime Bot

👤 ID: {user_id}
📦 Files: {len(files_db)}
""")


# ---------------- UPLOAD (IMPORTANT FIX) ---------------- #

@bot.message_handler(content_types=['document', 'video', 'audio'])
def upload_file(message):

    if message.from_user.id != ADMIN_ID:
        return bot.reply_to(message, "❌ Only admin")

    caption = message.caption or ""

    if message.document:
        file_id = message.document.file_id
        file_name = caption or message.document.file_name
        file_type = "document"

    elif message.video:
        file_id = message.video.file_id
        file_name = caption or "video"
        file_type = "video"

    elif message.audio:
        file_id = message.audio.file_id
        file_name = caption or "audio"
        file_type = "audio"

    else:
        return

    file_unique = str(int(time.time() * 1000))

    files_db[file_unique] = {
        "file_id": file_id,
        "name": file_name,
        "type": file_type,
        "caption": caption,

        # ⚡ IMPORTANT FOR COPY SPEED
        "from_chat_id": message.chat.id,
        "message_id": message.message_id
    }

    save_db()

    bot.reply_to(message, f"✅ Saved\n📦 {file_name}")


# ---------------- DELETE ---------------- #

@bot.message_handler(commands=['delete'])
def delete_file(message):
    if message.from_user.id != ADMIN_ID:
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return

    file_id = args[1].strip()

    if file_id in files_db:
        del files_db[file_id]
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

    with open("backup.json", "w") as f:
        json.dump(data, f, indent=4)

    with open("backup.json", "rb") as f:
        bot.send_document(message.chat.id, f)

    os.remove("backup.json")


# ---------------- RUN ---------------- #

print("Bot Running...")

while True:
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print(e)
        time.sleep(5)
