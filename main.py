# ---------------- IMPORTS ---------------- #

import telebot
import json
import os
import base64
import time
import threading
import re


# ---------------- CONFIG ---------------- #

TOKEN = "8772869279:AAEu5CEhxUGxOcrv_btL1RqNDmnSMbL6U3Y"
ADMIN_ID = 8758830915


# ---------------- BOT ---------------- #

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

# ---------------- DATABASE ---------------- #

db_lock = threading.Lock()


def load_json(file_path, default):
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Load Error ({file_path}): {e}")

    return default


files_db = load_json(DB_FILE, {})

users_data = load_json(USERS_DB_FILE, [])
users_db = set(users_data)


def save_db():
    try:
        with db_lock:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    files_db,
                    f,
                    indent=4,
                    ensure_ascii=False
                )
    except Exception as e:
        print(f"Save DB Error: {e}")


def save_users():
    try:
        with db_lock:
            with open(USERS_DB_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    list(users_db),
                    f,
                    indent=4,
                    ensure_ascii=False
                )
    except Exception as e:
        print(f"Save Users Error: {e}")

# ---------------- HELPERS ---------------- #

def get_episode_number(name):
    try:
        match = re.search(
            r'(?:ep|episode)\s*(\d+)',
            name.lower()
        )

        if match:
            return int(match.group(1))

    except Exception:
        pass

    return 999999

def normalize(text):
    if not text:
        return ""

    return (
        str(text)
        .lower()
        .strip()
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
    )


def encode_data(text):
    try:
        return base64.urlsafe_b64encode(
            text.encode("utf-8")
        ).decode("utf-8")
    except Exception as e:
        print(f"Encode Error: {e}")
        return ""


def decode_data(text):
    try:
        return base64.urlsafe_b64decode(
            text.encode("utf-8")
        ).decode("utf-8")
    except Exception as e:
        print(f"Decode Error: {e}")
        return None


def is_joined(user_id):
    try:
        member = bot.get_chat_member(
            CHANNEL_USERNAME,
            user_id
        )

        return member.status in (
            "creator",
            "administrator",
            "member"
        )

    except Exception as e:
        print(f"Join Check Error: {e}")
        return False


def join_message(chat_id):
    markup = telebot.types.InlineKeyboardMarkup()

    markup.add(
        telebot.types.InlineKeyboardButton(
            "📢 Join Channel",
            url=CHANNEL_LINK
        )
    )

    bot.send_message(
        chat_id,
        """
❌ Please Join Our Channel First

📢 Join the channel using the button below.

ပြီးမှ Bot ကို ပြန်အသုံးပြုပါ။
""",
        reply_markup=markup
    )

# ---------------- SEND FILES ---------------- #

def auto_delete(chat_id, message_ids):
    time.sleep(300)  # 5 Minutes

    for msg_id in message_ids:
        try:
            bot.delete_message(chat_id, msg_id)
        except Exception as e:
            print(f"Delete Error: {e}")


def send_single_file(chat_id, data, sent_messages):
    try:
        caption = data.get("caption", "")

        if data["type"] == "document":
            msg = bot.send_document(
                chat_id,
                data["file_id"],
                caption=caption
            )

        elif data["type"] == "video":
            msg = bot.send_video(
                chat_id,
                data["file_id"],
                caption=caption,
                supports_streaming=True
            )

        elif data["type"] == "audio":
            msg = bot.send_audio(
                chat_id,
                data["file_id"],
                caption=caption
            )

        else:
            return

        sent_messages.append(msg.message_id)

    except Exception as e:
        print(f"File Send Error: {e}")


def fast_send(chat_id, files):
    sent_messages = []
    threads = []

    for data in files:
        thread = threading.Thread(
            target=send_single_file,
            args=(chat_id, data, sent_messages)
        )

        thread.start()
        threads.append(thread)

    # Wait until all files are sent
    for thread in threads:
        thread.join()

    try:
        warning = bot.send_message(
            chat_id,
            f"""
✅ {len(sent_messages)} File Sent Successfully

🎬 Thank You For Using Our Anime Bot

⚠️ 5 မိနစ်ကြာရင်
(မူပိုင်ခွင့်ပြဿနာများကြောင့်)
အလိုအလျောက် ဖျက်ပါမည်။

📌 ကျေးဇူးပြု၍ File များကို
Saved Messages သို့ Forward လုပ်ထားပါ။
"""
        )

        sent_messages.append(warning.message_id)

        threading.Thread(
            target=auto_delete,
            args=(chat_id, sent_messages),
            daemon=True
        ).start()

    except Exception as e:
        print(f"Warning Message Error: {e}")
        
# ---------------- START ---------------- #

@bot.message_handler(commands=['start'])
def start(message):

    try:
        user_id = message.from_user.id
        chat_id = message.chat.id

        # Track new users only
        if user_id not in users_db:
            users_db.add(user_id)
            save_users()

        # Check channel join
        if not is_joined(user_id):
            join_message(chat_id)
            return

        args = message.text.split(maxsplit=1)

        # Start with anime link
        if len(args) > 1:
            try:
                keyword = normalize(decode_data(args[1]))
            except Exception:
                return bot.send_message(
                    chat_id,
                    "❌ Invalid Anime Link"
                )

            matched_files = [
                data for data in files_db.values()
                if keyword in normalize(data["name"])
                or normalize(data["name"]) in keyword
            ]

            # Start with anime link
if len(args) > 1:
    try:
        keyword = normalize(decode_data(args[1]))
    except Exception:
        return bot.send_message(
            chat_id,
            "❌ Invalid Anime Link"
        )

    matched_files = [
        data for data in files_db.values()
        if keyword in normalize(data["name"])
        or normalize(data["name"]) in keyword
    ]

    if matched_files:
        matched_files.sort(
            key=lambda x: get_episode_number(x["name"])
        )

        return fast_send(chat_id, matched_files)

    return bot.send_message(
        chat_id,
        "❌ Anime Not Found"
    )

        # Normal start message
        bot.send_message(
            chat_id,
            f"""
🎬 Welcome To Anime Bot

👤 User ID: {user_id}

📚 Available Anime:
{len(files_db)} Files

📢 Join Channel:
{CHANNEL_LINK}

🔍 Send Anime Link To Watch Episodes
"""
        )

    except Exception as e:
        print(f"Start Error: {e}")
        bot.send_message(
            message.chat.id,
            "❌ Something went wrong. Please try again."
        )

# ---------------- UPLOAD ---------------- #

@bot.message_handler(content_types=['document', 'video', 'audio'])
def upload_file(message):

    if message.from_user.id != ADMIN_ID:
        return bot.reply_to(message, "❌ Only admin can upload.")

    try:
        caption_text = message.caption or ""

        if message.document:
            file_id = message.document.file_id
            file_name = caption_text or message.document.file_name
            file_type = "document"

        elif message.video:
            file_id = message.video.file_id
            file_name = caption_text or "AnimeVideo"
            file_type = "video"

        elif message.audio:
            file_id = message.audio.file_id
            file_name = caption_text or "AnimeAudio"
            file_type = "audio"

        else:
            return

        # Duplicate Check
        for data in files_db.values():
            if data["file_id"] == file_id:
                return bot.reply_to(
                    message,
                    "⚠️ This file already exists in database."
                )

        # Unique ID
        file_unique = str(int(time.time() * 1000))

        files_db[file_unique] = {
            "file_id": file_id,
            "name": file_name,
            "type": file_type,
            "caption": caption_text,
            "added_time": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        save_db()

        bot_username = bot.get_me().username

        anime_only = file_name
        if "ep" in anime_only.lower():
            anime_only = anime_only.lower().split("ep")[0].strip()

        encoded = encode_data(normalize(anime_only))
        link = f"https://t.me/{bot_username}?start={encoded}"

        bot.reply_to(
            message,
            f"""
✅ ANIME SAVED SUCCESSFULLY

🎬 Name: {file_name}
📂 Type: {file_type}
🆔 ID: {file_unique}

📊 Total Files: {len(files_db)}
"""
        )

        bot.send_message(
            message.chat.id,
            f"""
🔗 Anime Link

{link}
"""
        )

    except Exception as e:
        bot.reply_to(
            message,
            f"❌ Upload Failed\n\n{e}"
        )

# ---------------- DELETE ---------------- #

@bot.message_handler(commands=['delete'])
def delete_file(message):

    if message.from_user.id != ADMIN_ID:
        return

    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        return bot.reply_to(
            message,
            "❌ Usage:\n/delete FILE_ID"
        )

    file_key = args[1].strip()

    if file_key not in files_db:
        return bot.reply_to(
            message,
            "❌ File ID Not Found."
        )

    file_name = files_db[file_key]["name"]

    del files_db[file_key]
    save_db()

    bot.reply_to(
        message,
        f"""
✅ File Deleted Successfully

🎬 Name: {file_name}
🆔 ID: {file_key}
"""
    )


@bot.message_handler(commands=['deleteall'])
def delete_all(message):

    if message.from_user.id != ADMIN_ID:
        return

    total_files = len(files_db)

    if total_files == 0:
        return bot.reply_to(
            message,
            "❌ Database is already empty."
        )

    files_db.clear()
    save_db()

    bot.reply_to(
        message,
        f"""
🗑 All Files Deleted Successfully

🎬 Total Deleted: {total_files}
"""
    )

# ---------------- DEL BY NAME ---------------- #

@bot.message_handler(commands=['delname'])
def delete_by_name(message):

    if message.from_user.id != ADMIN_ID:
        return

    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        return bot.reply_to(
            message,
            "❌ Usage:\n/delname anime name"
        )

    anime_name = normalize(args[1])

    deleted = 0
    deleted_names = []

    for file_id, data in list(files_db.items()):
        if anime_name in normalize(data["name"]):
            deleted_names.append(data["name"])
            del files_db[file_id]
            deleted += 1

    if deleted:
        save_db()

        preview = "\n".join(
            f"• {name}" for name in deleted_names[:10]
        )

        more = ""
        if deleted > 10:
            more = f"\n...and {deleted - 10} more"

        bot.reply_to(
            message,
            f"""
✅ Deleted Successfully

🗑 Deleted Files: {deleted}

📂 Removed:
{preview}{more}
"""
        )

    else:
        bot.reply_to(
            message,
            "❌ Anime Not Found"
        )

# ---------------- BACKUP ---------------- #

@bot.message_handler(commands=['backup'])
def backup_files(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:
        backup_data = {
            "files": files_db,
            "users": list(users_db),
            "total_files": len(files_db),
            "total_users": len(users_db),
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        backup_file = "anime_bot_backup.json"

        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(
                backup_data,
                f,
                indent=4,
                ensure_ascii=False
            )

        with open(backup_file, "rb") as f:
            bot.send_document(
                message.chat.id,
                f,
                caption=f"""
📦 Backup Completed ✅

👥 Users: {len(users_db)}
🎬 Files: {len(files_db)}
🕒 Time: {backup_data["created_at"]}
"""
            )

        os.remove(backup_file)

    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"❌ Backup Failed\n\n{e}"
        )

# ---------------- STATS ---------------- #

@bot.message_handler(commands=['stats'])
def stats(message):

    if message.from_user.id != ADMIN_ID:
        return

    files_size = round(
        os.path.getsize(DB_FILE) / 1024,
        2
    ) if os.path.exists(DB_FILE) else 0


    bot.send_message(
        message.chat.id,
        f"""
📊 Bot Statistics

👥 Total Users: {len(users_db)}
🎬 Total Files: {len(files_db)}

💾 Database Size: {files_size} KB

🤖 Bot Status: Online ✅
"""
    )

# ---------------- RUN ---------------- #

print("🤖 Anime Bot Running...")

while True:
    try:
        bot.infinity_polling(
            skip_pending=True,
            timeout=30,
            long_polling_timeout=30
        )

    except Exception as e:
        print(f"Bot Error: {e}")
        time.sleep(5)
