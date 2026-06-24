import telebot
import json
import os
import time
import threading
import re
import base64

TOKEN = "8772869279:AAHuxhvC6kpeEjsjspUjtbBvIXkmp9Z54iQ"
ADMIN_ID = 8758830915

MAIN_CHANNEL = "@Burmese_Anime"

bot = telebot.TeleBot(TOKEN)

DB_FILE = "files.json"
USERS_FILE = "users.json"

BACKUP_DIR = "backup"
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
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(files_db, f, indent=2, ensure_ascii=False)

def save_users():
    with lock:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(users_db), f, indent=2, ensure_ascii=False)

def encode_data(text):
    return base64.urlsafe_b64encode(text.encode()).decode()

def decode_data(text):
    return base64.urlsafe_b64decode(text.encode()).decode()

def make_backup():
    try:
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)

        ts = time.strftime("%Y%m%d_%H%M%S")

        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r", encoding="utf-8") as f:
                open(f"{BACKUP_DIR}/files_{ts}.json", "w", encoding="utf-8").write(f.read())

        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                open(f"{BACKUP_DIR}/users_{ts}.json", "w", encoding="utf-8").write(f.read())

        print("Backup created:", ts)

    except Exception as e:
        print("Backup error:", e)

def backup_loop():
    while True:
        make_backup()
        time.sleep(600)

threading.Thread(target=backup_loop, daemon=True).start()

def normalize(t):
    return str(t).lower().replace(" ", "").replace("-", "").replace("_", "")

def get_ep(name):
    m = re.search(r"(?:ep|episode|e)\s*(\d+)", name.lower())
    return int(m.group(1)) if m else 999999

def is_joined(uid):
    try:
        m = bot.get_chat_member(MAIN_CHANNEL, uid)
        return m.status in ["member", "creator", "administrator"]
    except:
        return False

def send_file(cid, f):
    if f["type"] == "video":
        return bot.send_video(cid, f["file_id"], caption=f.get("caption",""))
    elif f["type"] == "document":
        return bot.send_document(cid, f["file_id"], caption=f.get("caption",""))
    elif f["type"] == "audio":
        return bot.send_audio(cid, f["file_id"], caption=f.get("caption",""))

def auto_delete(cid, ids):
    time.sleep(300)
    for i in ids:
        try:
            bot.delete_message(cid, i)
        except:
            pass

def send_all_episodes(cid, files):
    sent = []

    files = sorted(files, key=lambda x: get_ep(x["name"]))

    for f in files:
        try:
            msg = send_file(cid, f)
            sent.append(msg.message_id)
        except:
            pass

    warn = bot.send_message(cid, f"Sent {len(sent)} Episodes\nAuto delete in 5 min")
    sent.append(warn.message_id)

    threading.Thread(target=auto_delete, args=(cid, sent), daemon=True).start()

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    cid = message.chat.id

    if uid not in users_db:
        users_db.add(uid)
        save_users()

    if not is_joined(uid):
        return bot.send_message(cid, "Please join channel first")

    args = message.text.split(maxsplit=1)

    if len(args) > 1:
        key = args[1]

        if key.startswith("series_"):
            try:
                series_id = decode_data(key.replace("series_", ""))

                if series_id in files_db:
                    base = files_db[series_id]["name"]

                    matched = [
                        f for f in files_db.values()
                        if normalize(base) in normalize(f["name"])
                    ]

                    return send_all_episodes(cid, matched)

            except:
                return bot.send_message(cid, "Invalid Link")

        key = normalize(key)

        matched = [
            f for f in files_db.values()
            if key in normalize(f["name"])
        ]

        if matched:
            return send_all_episodes(cid, matched)

        return bot.send_message(cid, "Anime Not Found")

    bot.send_message(cid, "Anime Bot Ready")

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

    file_key = str(int(time.time()*1000))

    files_db[file_key] = {
        "file_id": file_id,
        "name": name,
        "type": ftype,
        "caption": caption
    }

    save_files()

    encoded = encode_data(file_key)

    link = f"https://t.me/{bot.get_me().username}?start=series_{encoded}"

    bot.send_message(message.chat.id, f"All Episodes Link:\n{link}")

print("Bot Running...")

while True:
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print("Restarting bot:", e)
        time.sleep(5)
