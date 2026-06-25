import telebot
import json
import os
import base64
import time

# ---------------- CONFIG ---------------- #

TOKEN = "8772869279:AAHuxhvC6kpeEjsjspUjtbBvIXkmp9Z54iQ"
ADMIN_ID = 8758830915

bot = telebot.TeleBot(TOKEN, threaded=True, num_threads=10)

# ---------------- DB ---------------- #

DB_FILE = "files.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

files_db = load_db()

def save_db():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(files_db, f, indent=4, ensure_ascii=False)

# ---------------- ENCODE / DECODE ---------------- #

def encode(text):
    return base64.urlsafe_b64encode(
        text.encode("utf-8")
    ).decode("utf-8")


def decode(text):
    return base64.urlsafe_b64decode(
        text.encode("utf-8")
    ).decode("utf-8")

# ---------------- NORMALIZE ---------------- #

def normalize(text):
    return str(text).lower()\
        .replace(" ", "")\
        .replace("-", "")\
        .replace("_", "")\
        .replace("ep", "")

# ---------------- SEND ALL ---------------- #

def send_one(chat_id, data, sent):
    try:
        msg = bot.copy_message(
            chat_id,
            data["chat_id"],
            data["message_id"],
            caption=data.get("caption", "")
        )
        sent.append(msg.message_id)
    except:
        pass


def send_all(chat_id, episodes):
    sent = []

    for ep in episodes:
        send_one(chat_id, ep, sent)

    bot.send_message(
        chat_id,
        f"✅ ALL EP SENT ({len(sent)})"
    )

# ---------------- START (DECODE LINK CLICK) ---------------- #

@bot.message_handler(commands=['start'])
def start(message):

    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        return bot.send_message(message.chat.id,
            "🎬 Send Anime Name or Link"
        )

    try:
        # decode link payload
        key = decode(args[1])
        key = normalize(key)

    except:
        return bot.send_message(message.chat.id, "❌ Invalid Link")

    if key in files_db:
        episodes = files_db[key]["episodes"]
        return send_all(message.chat.id, episodes)

    bot.send_message(message.chat.id, "❌ Anime Not Found")

# ---------------- UPLOAD (ADMIN) ---------------- #

@bot.message_handler(content_types=['video', 'document', 'audio'])
def upload(message):

    if message.from_user.id != ADMIN_ID:
        return

    name = message.caption or "Unknown Anime"
    key = normalize(name)

    if key not in files_db:
        files_db[key] = {
            "anime": name,
            "episodes": []
        }

    files_db[key]["episodes"].append({
        "chat_id": message.chat.id,
        "message_id": message.message_id,
        "caption": name
    })

    save_db()

    # ---------------- GENERATE ENCODE LINK ---------------- #

    bot_username = bot.get_me().username

    encoded_key = encode(key)

    link = f"https://t.me/{bot_username}?start={encoded_key}"

    bot.reply_to(message,
        f"""
✅ SAVED

🎬 {name}
📦 EP: {len(files_db[key]['episodes'])}
"""
    )

    bot.send_message(
        message.chat.id,
        f"🔗 ENCODE LINK:\n{link}"
    )

# ---------------- DELETE ---------------- #

@bot.message_handler(commands=['delete'])
def delete(message):

    if message.from_user.id != ADMIN_ID:
        return

    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        return

    key = normalize(args[1])

    if key in files_db:
        del files_db[key]
        save_db()
        bot.reply_to(message, "✅ Deleted")
    else:
        bot.reply_to(message, "❌ Not Found")

# ---------------- RUN ---------------- #

print("🚀 ENCODE LINK BOT RUNNING...")

while True:
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print("Error:", e)
        time.sleep(5)
