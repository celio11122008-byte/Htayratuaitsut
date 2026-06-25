import telebot
import json
import os
import time
import threading
import hashlib

# ---------------- CONFIG ---------------- #

TOKEN = "8772869279:AAHuxhvC6kpeEjsjspUjtbBvIXkmp9Z54iQ"
ADMIN_ID = 8758830915

bot = telebot.TeleBot(TOKEN, threaded=True, num_threads=10)

# ---------------- DB ---------------- #

DB_FILE = "files.json"
USERS_FILE = "users.json"

lock = threading.Lock()

def load(file, default):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


files_db = load(DB_FILE, {})
users_db = set(load(USERS_FILE, []))


def save_files():
    with lock:
        json.dump(files_db, open(DB_FILE, "w", encoding="utf-8"), indent=4, ensure_ascii=False)


def save_users():
    with lock:
        json.dump(list(users_db), open(USERS_FILE, "w", encoding="utf-8"), indent=4, ensure_ascii=False)

# ---------------- SHORT CODE ---------------- #

def short_code(text):
    return hashlib.md5(text.encode()).hexdigest()[:7]

# ---------------- SEND COPY ---------------- #

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


def send_all(chat_id, files):
    sent = []
    threads = []

    for f in files:
        t = threading.Thread(target=send_one, args=(chat_id, f, sent))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    bot.send_message(
        chat_id,
        f"""
✅ ALL EPISODES SENT SUCCESSFULLY

📦 Total Sent: {len(sent)}

⚠️ Auto delete in 5 min
Saved Messages ထဲ forward လုပ်ပါ
"""
    )


# ---------------- START ---------------- #

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    users_db.add(user_id)
    save_users()

    args = message.text.split(maxsplit=1)

    if len(args) > 1:
        code = args[1]

        matched = [f for f in files_db.values() if f.get("code") == code]

        if matched:
            return send_all(chat_id, matched)

        return bot.send_message(chat_id, "❌ Not found")

    bot.send_message(chat_id,
        f"""
🎬 Anime Bot Ready
📦 Files: {len(files_db)}
"""
    )


# ---------------- UPLOAD (ADMIN) ---------------- #

@bot.message_handler(content_types=['document', 'video', 'audio'])
def upload(message):
    if message.from_user.id != ADMIN_ID:
        return

    caption = message.caption or "Anime"

    code = short_code(caption)

    file_id = str(int(time.time() * 1000))

    files_db[file_id] = {
        "chat_id": message.chat.id,
        "message_id": message.message_id,
        "name": caption,
        "caption": caption,
        "code": code,
        "time": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    save_files()

    bot.reply_to(message,
        f"""
✅ SAVED

🎬 {caption}
🔑 Code: {code}
"""
    )

    bot.send_message(
        message.chat.id,
        f"🔗 Link:\nhttps://t.me/{bot.get_me().username}?start={code}"
    )


# ---------------- DELETE ---------------- #

@bot.message_handler(commands=['delete'])
def delete(message):
    if message.from_user.id != ADMIN_ID:
        return

    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        return

    fid = args[1]

    if fid in files_db:
        del files_db[fid]
        save_files()
        bot.reply_to(message, "✅ Deleted")


# ---------------- STATS ---------------- #

@bot.message_handler(commands=['stats'])
def stats(message):
    if message.from_user.id != ADMIN_ID:
        return

    bot.send_message(message.chat.id,
        f"""
📊 BOT STATS

👥 Users: {len(users_db)}
🎬 Files: {len(files_db)}
"""
    )


# ---------------- RUN ---------------- #

print("Bot Running...")

while True:
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print("Error:", e)
        time.sleep(5)
