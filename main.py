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
USERS_DB_FILE = "users.json"

CHANNEL_USERNAME = "@Burmese_Anime"
CHANNEL_LINK = "https://t.me/Burmese_Anime"

db_lock = threading.Lock()

# ---------------- LOAD DB ---------------- #

def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return default

files_db = load_json(DB_FILE, {})
users_db = set(load_json(USERS_DB_FILE, []))

# ---------------- SAVE ---------------- #

def save_db():
    with db_lock:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(files_db, f, indent=4, ensure_ascii=False)

def save_users():
    with db_lock:
        with open(USERS_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(list(users_db), f, indent=4, ensure_ascii=False)

# ---------------- HELPERS ---------------- #

def normalize(t):
    if not t:
        return ""
    return str(t).lower().strip().replace(" ", "").replace("-", "").replace("_", "")

def encode_data(t):
    return base64.urlsafe_b64encode(t.encode()).decode()

def decode_data(t):
    return base64.urlsafe_b64decode(t.encode()).decode()

def is_joined(uid):
    try:
        m = bot.get_chat_member(CHANNEL_USERNAME, uid)
        return m.status in ("creator", "administrator", "member")
    except:
        return False

def join_message(cid):
    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(telebot.types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
    bot.send_message(cid, "❌ Join Channel First", reply_markup=kb)

# ---------------- AUTO DELETE ---------------- #

def auto_delete(chat_id, mids):
    time.sleep(300)
    for m in mids:
        try:
            bot.delete_message(chat_id, m)
        except:
            pass

# ---------------- FAST COPY SEND ---------------- #

def send_single(chat_id, data, sent):
    try:
        msg = bot.copy_message(
            chat_id,
            from_chat_id=data["from_chat_id"],
            message_id=data["message_id"]
        )
        sent.append(msg.message_id)
    except Exception as e:
        print("SEND ERROR:", e)

def fast_send(chat_id, files):
    sent = []
    threads = []

    for d in files:
        t = threading.Thread(target=send_single, args=(chat_id, d, sent))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    warn = bot.send_message(chat_id, f"✅ Sent {len(sent)} Files")
    sent.append(warn.message_id)

    threading.Thread(target=auto_delete, args=(chat_id, sent), daemon=True).start()

# ---------------- START ---------------- #

@bot.message_handler(commands=['start'])
def start(m):
    uid = m.from_user.id
    cid = m.chat.id

    if uid not in users_db:
        users_db.add(uid)
        save_users()

    if not is_joined(uid):
        return join_message(cid)

    args = m.text.split(maxsplit=1)

    # 🔍 SEARCH MODE
    if len(args) > 1:
        try:
            keyword = normalize(decode_data(args[1]))
        except:
            return bot.send_message(cid, "❌ Invalid Link")

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
📦 Files: {len(files_db)}
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

    file_key = str(int(time.time() * 1000))

    # ⚡ IMPORTANT FIX (copy system)
    files_db[file_key] = {
        "file_id": file_id,
        "name": name,
        "type": ftype,
        "caption": caption,
        "from_chat_id": m.chat.id,
        "message_id": m.message_id
    }

    save_db()

    bot_username = bot.get_me().username

    anime_name = normalize(name.split("ep")[0])
    encoded = encode_data(anime_name)

    link = f"https://t.me/{bot_username}?start={encoded}"

    bot.reply_to(m, f"✅ Saved: {name}")

    bot.send_message(m.chat.id, f"🔗 Link:\n{link}")

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
        save_db()
        bot.reply_to(m, "✅ Deleted")
    else:
        bot.reply_to(m, "❌ Not found")

# ---------------- RUN ---------------- #

print("Bot Running...")

while True:
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print(e)
        time.sleep(5)
