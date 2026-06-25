import telebot
import json
import os
import base64
import time
import threading

# ---------------- CONFIG ---------------- #

TOKEN = "8772869279:AAHuxhvC6kpeEjsjspUjtbBvIXkmp9Z54iQ"
ADMIN_ID = 8758830915

bot = telebot.TeleBot(TOKEN, threaded=True, num_threads=10)

DB_FILE = "files.json"
USERS_FILE = "users.json"

CHANNEL_USERNAME = "@Burmese_Anime"
CHANNEL_LINK = "https://t.me/Burmese_Anime"

lock = threading.Lock()

# ---------------- LOAD DB ---------------- #

def load(path, default):
    if os.path.exists(path):
        try:
            return json.load(open(path, "r", encoding="utf-8"))
        except:
            pass
    return default

files_db = load(DB_FILE, {})
users_db = set(load(USERS_FILE, []))

# ---------------- SAVE ---------------- #

def save_files():
    with lock:
        json.dump(files_db, open(DB_FILE, "w", encoding="utf-8"), indent=4, ensure_ascii=False)

def save_users():
    with lock:
        json.dump(list(users_db), open(USERS_FILE, "w", encoding="utf-8"), indent=4, ensure_ascii=False)

# ---------------- HELPERS ---------------- #

def normalize(t):
    return str(t).lower().replace(" ", "").replace("-", "").replace("_", "")

def encode(t):
    return base64.urlsafe_b64encode(t.encode()).decode()

def decode(t):
    return base64.urlsafe_b64decode(t.encode()).decode()

def is_joined(uid):
    try:
        m = bot.get_chat_member(CHANNEL_USERNAME, uid)
        return m.status in ("member", "administrator", "creator")
    except:
        return False

def join_msg(cid):
    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(telebot.types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
    bot.send_message(cid, "❌ Join first", reply_markup=kb)

# ---------------- AUTO DELETE ---------------- #

def auto_delete(cid, mids):
    time.sleep(300)
    for m in mids:
        try:
            bot.delete_message(cid, m)
        except:
            pass

# ---------------- FAST COPY SEND ---------------- #

def send_one(cid, data, sent):
    try:
        msg = bot.copy_message(
            cid,
            from_chat_id=data["from_chat_id"],
            message_id=data["message_id"]
        )
        sent.append(msg.message_id)
    except:
        pass

def fast_send(cid, files):
    sent = []
    threads = []

    for f in files:
        t = threading.Thread(target=send_one, args=(cid, f, sent))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    warn = bot.send_message(cid, f"✅ Sent {len(sent)} files")
    sent.append(warn.message_id)

    threading.Thread(target=auto_delete, args=(cid, sent), daemon=True).start()

# ---------------- START ---------------- #

@bot.message_handler(commands=['start'])
def start(m):
    uid = m.from_user.id
    cid = m.chat.id

    if uid not in users_db:
        users_db.add(uid)
        save_users()

    if not is_joined(uid):
        return join_msg(cid)

    args = m.text.split(maxsplit=1)

    # 🔍 SEARCH MODE
    if len(args) > 1:
        try:
            keyword = normalize(decode(args[1]))
        except:
            return bot.send_message(cid, "❌ Invalid link")

        matched = [
            d for d in files_db.values()
            if keyword in normalize(d["name"])
        ]

        if matched:
            return fast_send(cid, matched)

        return bot.send_message(cid, "❌ Not Found")

    bot.send_message(cid, f"""
🎬 Anime Bot

👤 ID: {uid}
📦 Total: {len(files_db)}
""")

# ---------------- UPLOAD ---------------- #

@bot.message_handler(content_types=['document', 'video', 'audio'])
def upload(m):

    if m.from_user.id != ADMIN_ID:
        return bot.reply_to(m, "❌ Admin only")

    caption = m.caption or ""

    if m.document:
        file_id = m.document.file_id
        name = caption or m.document.file_name
        ftype = "document"

    elif m.video:
        file_id = m.video.file_id
        name = caption or "video"
        ftype = "video"

    elif m.audio:
        file_id = m.audio.file_id
        name = caption or "audio"
        ftype = "audio"

    else:
        return

    # ⚡ IMPORTANT: ONLY ANIME NAME KEY
    anime_key = normalize(name.split("ep")[0].strip())

    file_id_key = str(int(time.time() * 1000))

    files_db[file_id_key] = {
        "file_id": file_id,
        "name": anime_key,
        "type": ftype,
        "caption": caption,
        "from_chat_id": m.chat.id,
        "message_id": m.message_id
    }

    save_files()

    bot_username = bot.get_me().username
    encoded = encode(anime_key)

    link = f"https://t.me/{bot_username}?start={encoded}"

    bot.reply_to(m, f"""
✅ SAVED

🎬 {anime_key}
📦 ID: {file_id_key}
""")

    bot.send_message(m.chat.id, f"🔗 LINK:\n{link}")

# ---------------- DELETE ---------------- #

@bot.message_handler(commands=['delete'])
def delete(m):
    if m.from_user.id != ADMIN_ID:
        return

    args = m.text.split(maxsplit=1)
    if len(args) < 2:
        return

    key = args[1]

    if key in files_db:
        del files_db[key]
        save_files()
        bot.reply_to(m, "✅ Deleted")
    else:
        bot.reply_to(m, "❌ Not found")

# ---------------- RUN ---------------- #

print("BOT RUNNING...")

while True:
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print(e)
        time.sleep(5)
