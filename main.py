import telebot
import json
import os
import time
import re
import threading

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

# ---------------- SMART NORMALIZE ---------------- #

def normalize(text):
    return str(text).lower()\
        .replace(" ", "")\
        .replace("-", "")\
        .replace("_", "")\
        .replace("ep", "")

def smart_match(q, k):
    return q in k or k in q

# ---------------- EP SORT ---------------- #

def extract_ep(text):
    m = re.search(r'(\d+)', text)
    return int(m.group()) if m else 0


def sort_eps(episodes):
    return sorted(episodes, key=lambda x: extract_ep(x.get("caption", "")))

# ---------------- AUTO DELETE ---------------- #

def auto_delete(chat_id, msg_ids, delay):
    time.sleep(delay)
    for mid in msg_ids:
        try:
            bot.delete_message(chat_id, mid)
        except:
            pass

# ---------------- COPY SEND ---------------- #

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

# ---------------- SMART SEND ENGINE ---------------- #

def send_all(chat_id, episodes):

    episodes = sort_eps(episodes)

    sent = []

    for ep in episodes:
        send_one(chat_id, ep, sent)

    # CLEAN FINAL MESSAGE ONLY
    final = bot.send_message(
        chat_id,
        f"✅ ALL EP SENT ({len(sent)})"
    )

    sent.append(final.message_id)

    # AUTO DELETE TIME ADJUST
    if len(sent) <= 5:
        delay = 120
    elif len(sent) <= 20:
        delay = 300
    else:
        delay = 600

    threading.Thread(
        target=auto_delete,
        args=(chat_id, sent, delay),
        daemon=True
    ).start()

# ---------------- START ---------------- #

@bot.message_handler(commands=['start'])
def start(message):

    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        return bot.send_message(message.chat.id,
            "🎬 Send Anime Name\nExample: /start Naruto"
        )

    query = normalize(args[1])

    matched = None

    for key, data in files_db.items():
        if smart_match(query, key):
            matched = data["episodes"]
            break

    if matched:
        return send_all(message.chat.id, matched)

    bot.send_message(message.chat.id, "❌ Not Found")

# ---------------- UPLOAD ---------------- #

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

    bot.reply_to(message,
        f"✅ Saved\n🎬 {name}\n📦 EP: {len(files_db[key]['episodes'])}"
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

# ---------------- STATS ---------------- #

@bot.message_handler(commands=['stats'])
def stats(message):

    if message.from_user.id != ADMIN_ID:
        return

    total_anime = len(files_db)
    total_eps = sum(len(v["episodes"]) for v in files_db.values())

    bot.send_message(message.chat.id,
        f"""
📊 BOT STATS

🎬 Anime: {total_anime}
📦 Episodes: {total_eps}

⚡ Mode: SMART CLEAN
"""
    )

# ---------------- RUN ---------------- #

print("🚀 CLEAN SMART BOT RUNNING...")

while True:
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print("Error:", e)
        time.sleep(5)
