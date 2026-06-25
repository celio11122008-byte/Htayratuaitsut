import telebot
import json
import os
import base64
import time
import threading

TOKEN = "8772869279:AAFPJXR3lWQtCqTiP535o1zn3kVLj3n7cE0"
ADMIN_ID = 8758830915

bot = telebot.TeleBot(TOKEN, threaded=True)

DB_FILE = "files.json"
USERS_DB_FILE = "users.json"

CHANNEL_USERNAME = "@Burmese_Anime"
CHANNEL_LINK = "https://t.me/Burmese_Anime"

lock = threading.Lock()

# ---------------- LOAD ---------------- #

def load_json(file, default):
    if os.path.exists(file):
        try:
            with open(file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default
    return default


files_db = load_json(DB_FILE, {})
users_db = set(load_json(USERS_DB_FILE, []))


def save_db():
    with lock:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(files_db, f, indent=4, ensure_ascii=False)


def save_users():
    with lock:
        with open(USERS_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(list(users_db), f, indent=4)


# ---------------- HELPERS ---------------- #

def normalize(text):
    return text.lower().replace(" ", "").replace("-", "").replace("_", "")


def encode_data(text):
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def decode_data(text):
    try:
        return base64.urlsafe_b64decode(text + "==").decode()
    except:
        return None


def is_joined(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["creator", "administrator", "member"]
    except:
        return False


def join_message(chat_id):
    bot.send_message(
        chat_id,
        f"""
❌ Please Join Channel First

📢 {CHANNEL_LINK}

ပြီးမှ Bot ကိုပြန်သုံးပါ။
"""
    )


# ---------------- AUTO DELETE ---------------- #

def auto_delete(chat_id, message_ids):
    time.sleep(300)
    for msg_id in message_ids:
        try:
            bot.delete_message(chat_id, msg_id)
        except:
            pass


# ---------------- FAST SEND ---------------- #

def fast_send(chat_id, files):
    sent_messages = []

    for data in files:
        try:
            caption = data.get("caption", "")

            if data["type"] == "document":
                msg = bot.send_document(chat_id, data["file_id"], caption=caption)

            elif data["type"] == "video":
                msg = bot.send_video(chat_id, data["file_id"], caption=caption, supports_streaming=True)

            elif data["type"] == "audio":
                msg = bot.send_audio(chat_id, data["file_id"], caption=caption)

            sent_messages.append(msg.message_id)

        except:
            pass

    warning = bot.send_message(
        chat_id,
        f"""
✅ {len(sent_messages)} File Sent Successfully

🎬 Thank You For Using Our Anime Bot

⚠️ 5 မိနစ်ကြာရင်
(မူပိုင်ခွင့်ပြဿနာများကြောင့်)
အလိုအလျောက် ဖျက်ပါမည်။

📌 ကျေးဇူးပြု၍ ဤဖိုင်များအားလုံးကို
Saved Messages သို့ Forward လုပ်ထားပါ။
"""
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

    users_db.add(user_id)
    save_users()

    if not is_joined(user_id):
        join_message(message.chat.id)
        return

    args = message.text.split(maxsplit=1)

    if len(args) > 1:
        keyword = decode_data(args[1])

        if not keyword:
            bot.send_message(message.chat.id, "❌ Invalid Link")
            return

        keyword = normalize(keyword)

        matched_files = []

        for file_id, data in files_db.items():
            if keyword in normalize(data["name"]):
                matched_files.append(data)

        if matched_files:
            fast_send(message.chat.id, matched_files)
        else:
            bot.send_message(message.chat.id, "❌ Anime Not Found")

        return

    bot.send_message(
        message.chat.id,
        f"""
🎬 Anime Bot

📢 Join Channel
{CHANNEL_LINK}
"""
    )


# ---------------- UPLOAD ---------------- #

@bot.message_handler(content_types=['document', 'video', 'audio'])
def upload_file(message):

    if message.from_user.id != ADMIN_ID:
        return bot.reply_to(message, "❌ Only admin can upload.")

    file_unique = str(message.message_id)
    caption_text = message.caption if message.caption else ""

    if message.document:
        file_id = message.document.file_id
        file_name = message.document.file_name
        file_type = "document"

    elif message.video:
        file_id = message.video.file_id
        file_name = message.caption if message.caption else "AnimeVideo"
        file_type = "video"

    elif message.audio:
        file_id = message.audio.file_id
        file_name = message.caption if message.caption else "AnimeAudio"
        file_type = "audio"

    files_db[file_unique] = {
        "file_id": file_id,
        "name": file_name,
        "type": file_type,
        "caption": caption_text
    }

    save_db()

    bot_username = bot.get_me().username

    anime_only = file_name
    if "ep" in anime_only.lower():
        anime_only = anime_only.lower().split("ep")[0].strip()

    encoded = encode_data(normalize(anime_only))

    link = f"https://t.me/{bot_username}?start={encoded}"

    bot.reply_to(message, f"""
✅ ANIME SAVED

🎬 {file_name}

🆔 {file_unique}
""")

    bot.send_message(message.chat.id, link)


# ---------------- DELETE ---------------- #

@bot.message_handler(commands=['delete'])
def delete_file(message):
    if message.from_user.id != ADMIN_ID:
        return

    args = message.text.split()

    if len(args) < 2:
        return bot.reply_to(message, "Usage:\n/delete ID")

    file_key = args[1]

    if file_key not in files_db:
        return bot.reply_to(message, "❌ File not found.")

    del files_db[file_key]
    save_db()

    bot.reply_to(message, "✅ Deleted")


# ---------------- DELETE ALL ---------------- #

@bot.message_handler(commands=['deleteall'])
def delete_all(message):
    if message.from_user.id != ADMIN_ID:
        return

    files_db.clear()
    save_db()

    bot.reply_to(message, "✅ All Files Deleted.")


# ---------------- DELETE BY NAME ---------------- #

@bot.message_handler(commands=['delname'])
def delete_by_name(message):
    if message.from_user.id != ADMIN_ID:
        return

    anime_name = message.text.replace("/delname ", "").lower()

    if not anime_name:
        return bot.reply_to(message, "Usage:\n/delname anime name")

    deleted = 0

    for file_id, data in list(files_db.items()):
        if anime_name in data["name"].lower():
            del files_db[file_id]
            deleted += 1

    save_db()

    if deleted:
        bot.reply_to(message, f"✅ Deleted {deleted} Files.")
    else:
        bot.reply_to(message, "❌ File not found.")


# ---------------- BACKUP ---------------- #

@bot.message_handler(commands=['backup'])
def backup_files(message):
    if message.from_user.id != ADMIN_ID:
        return

    backup_file = "backup.json"

    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(files_db, f, indent=4, ensure_ascii=False)

    with open(backup_file, "rb") as f:
        bot.send_document(message.chat.id, f, caption="📦 Backup Completed")

    os.remove(backup_file)


# ---------------- STATS ---------------- #

@bot.message_handler(commands=['stats'])
def stats(message):
    if message.from_user.id != ADMIN_ID:
        return

    bot.send_message(
        message.chat.id,
        f"""
📊 Bot Statistics

👥 Total Users: {len(users_db)}
🎬 Total Files: {len(files_db)}
"""
    )


# ---------------- RUN ---------------- #

print("🤖 Anime Bot Running...")

while True:
    try:
        bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
    except Exception as e:
        print("Error:", e)
        time.sleep(5)
