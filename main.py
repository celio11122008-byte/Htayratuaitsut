import telebot
import json
import os
import time
import threading
import re

TOKEN = "8772869279:AAHuxhvC6kpeEjsjspUjtbBvIXkmp9Z54iQ"
ADMIN_ID = 8758830915

MAIN_CHANNEL = "@Burmese_Anime"

bot = telebot.TeleBot(TOKEN, threaded=True)

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
        json.dump(files_db, open(DB_FILE, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

def save_users():
    with lock:
        json.dump(list(users_db), open(USERS_FILE, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

def normalize(t):
    return str(t).lower().replace(" ", "").replace("-", "").replace("_", "")

def get_ep(name):
    m = re.search(r"(?:ep|episode|e)\s*(\d+)", name.lower())
    return int(m.group(1)) if m else 999999

def send_file(cid, f):
    try:
        if f["type"] == "video":
            return bot.send_video(cid, f["file_id"], caption=f.get("caption",""))
        elif f["type"] == "document":
            return bot.send_document(cid, f["file_id"], caption=f.get("caption",""))
        elif f["type"] == "audio":
            return bot.send_audio(cid, f["file_id"], caption=f.get("caption",""))
    except:
        return None

def fast_send(cid, files):
    sent = []

    files = sorted(files, key=lambda x: get_ep(x["name"]))

    def worker(f):
        msg = send_file(cid, f)
        if msg:
            sent.append(msg.message_id)

    threads = []

    for f in files:
        t = threading.Thread(target=worker, args=(f,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    bot.send_message(cid, f"🎬 Sent {len(sent)} Episodes")

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    cid = message.chat.id

    if uid not in users_db:
        users_db.add(uid)
        save_users()

    args = message.text.split(maxsplit=1)

    if len(args) > 1:
        key = args[1]

        if key.startswith("series_"):
            series_id = key.replace("series_", "")

            if series_id in files_db:
                base = files_db[series_id]["name"]

                matched = [
                    f for f in files_db.values()
                    if normalize(base) in normalize(f["name"])
                ]

                return fast_send(cid, matched)

        key = normalize(key)

        matched = [
            f for f in files_db.values()
            if key in normalize(f["name"])
        ]

        if matched:
            return fast_send(cid, matched)

        return bot.send_message(cid, "Anime Not Found")

    bot.send_message(cid, "🎬 Bot Ready")

@bot.message_handler(content_types=['video','document','audio'])
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

    series_id = str(int(time.time()*1000))

    files_db[series_id] = {
        "file_id": file_id,
        "name": name,
        "type": ftype,
        "caption": caption
    }

    save_files()

    link = f"https://t.me/{bot.get_me().username}?start=series_{series_id}"

    bot.send_message(message.chat.id, f"🎬 All Episodes Sent Link:\n{link}")

print("Bot Running...")

while True:
    try:
        bot.infinity_polling(skip_pending=True, timeout=20)
    except Exception as e:
        print("Restarting:", e)
        time.sleep(3)
