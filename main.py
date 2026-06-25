# ---------------- IMPORTS ---------------- #

import telebot
import json
import os
import base64
import time
import threading
from concurrent.futures import ThreadPoolExecutor

# ---------------- CONFIG ---------------- #

TOKEN = os.getenv("BOT_TOKEN", "8772869279:AAHuxhvC6kpeEjsjspUjtbBvIXkmp9Z54iQ")  # safer
ADMIN_ID = 8758830915

CHANNEL_USERNAME = "@Burmese_Anime"
CHANNEL_LINK = "https://t.me/Burmese_Anime"

bot = telebot.TeleBot(TOKEN, threaded=True, num_threads=10)

# ---------------- FILES ---------------- #

DB_FILE = "files.json"
USERS_DB_FILE = "users.json"

db_lock = threading.Lock()
send_lock = threading.Lock()

# ---------------- LOAD DB ---------------- #

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return default


files_db = load_json(DB_FILE, {})
users_db = set(load_json(USERS_DB_FILE, []))

# ---------------- SAVE (ATOMIC) ---------------- #

def save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    os.replace(tmp, path)


def save_db():
    with db_lock:
        save_json(DB_FILE, files_db)


def save_users():
    with db_lock:
        save_json(USERS_DB_FILE, list(users_db))

# ---------------- HELPERS ---------------- #

def normalize(t):
    return str(t).lower().strip().replace(" ", "").replace("-", "").replace("_", "")


def encode_data(text):
    return base64.urlsafe_b64encode(text.encode()).decode()


def decode_data(text):
    try:
        return base64.urlsafe_b64decode(text.encode()).decode()
    except:
        return None


def is_joined(user_id):
    try:
        m = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return m.status in ["creator", "administrator", "member"]
    except:
        return False


def join_message(chat_id):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)
    )

    bot.send_message(
        chat_id,
        "❌ Please Join Channel First",
        reply_markup=markup
    )

# ---------------- SEND SYSTEM ---------------- #

def send_file(chat_id, data):
    caption = data.get("caption", "")

    try:
        if data["type"] == "document":
            return bot.send_document(chat_id, data["file_id"], caption=caption)

        elif data["type"] == "video":
            return bot.send_video(chat_id, data["file_id"], caption=caption, supports_streaming=True)

        elif data["type"] == "audio":
            return bot.send_audio(chat_id, data["file_id"], caption=caption)

    except Exception as e:
        print("Send Error:", e)

    return None


def fast_send(chat_id, files):
    sent_ids = []

    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(lambda d: send_file(chat_id, d), files))

    for r in results:
        if r:
            sent_ids.append(r.message_id)

    msg = bot.send_message(
        chat_id,
        f"✅ Sent {len(sent_ids)} files\n⚠️ Auto delete in 5 min"
    )

    sent_ids.append(msg.message_id)

    threading.Thread(target=auto_delete, args=(chat_id, sent_ids), daemon=True).start()


def auto_delete(chat_id, msg_ids):
    time.sleep(300)
    for m in msg_ids:
        try:
            bot.delete_message(chat_id, m)
        except:
            pass

# ---------------- START ---------------- #

@bot.message_handler(commands=['start'])
def start(m):
    uid = m.from_user.id
    cid = m.chat.id

    with send_lock:
        if uid not in users_db:
            users_db.add(uid)
            save_users()

    if not is_joined(uid):
        return join_message(cid)

    args = m.text.split(maxsplit=1)

    if len(args) > 1:
        kw = decode_data(args[1])
        if not kw:
            return bot.send_message(cid, "❌ Invalid link")

        kw = normalize(kw)

        matched = [
            d for d in files_db.values()
            if kw in normalize(d["name"])
        ]

        if matched:
            return fast_send(cid, matched)

        return bot.send_message(cid, "❌ Not found")

    bot.send_message(
        cid,
        f"🎬 Anime Bot\nFiles: {len(files_db)}"
    )

# ---------------- UPLOAD ---------------- #

@bot.message_handler(content_types=['document', 'video', 'audio'])
def upload(m):
    if m.from_user.id != ADMIN_ID:
        return

    caption = m.caption or ""

    if m.document:
        fid = m.document.file_id
        name = caption or m.document.file_name
        t = "document"

    elif m.video:
        fid = m.video.file_id
        name = caption or "video"
        t = "video"

    elif m.audio:
        fid = m.audio.file_id
        name = caption or "audio"
        t = "audio"
    else:
        return

    for d in files_db.values():
        if d["file_id"] == fid:
            return bot.reply_to(m, "Already exists")

    key = str(int(time.time() * 1000))

    files_db[key] = {
        "file_id": fid,
        "name": name,
        "type": t,
        "caption": caption,
        "time": time.time()
    }

    save_db()

    bot.reply_to(m, f"✅ Saved\nID: {key}\nTotal: {len(files_db)}")

# ---------------- DELETE ---------------- #

@bot.message_handler(commands=['delete'])
def delete(m):
    if m.from_user.id != ADMIN_ID:
        return

    args = m.text.split(maxsplit=1)
    if len(args) < 2:
        return

    fid = args[1].strip()

    if fid in files_db:
        del files_db[fid]
        save_db()
        bot.reply_to(m, "Deleted")
    else:
        bot.reply_to(m, "Not found")

# ---------------- STATS ---------------- #

@bot.message_handler(commands=['stats'])
def stats(m):
    if m.from_user.id != ADMIN_ID:
        return

    bot.send_message(
        m.chat.id,
        f"Users: {len(users_db)}\nFiles: {len(files_db)}"
    )

# ---------------- RUN ---------------- #

print("Bot Running...")

while True:
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print("Crash:", e)
        time.sleep(5)
