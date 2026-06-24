import telebot
import json
import os
import time
import threading
import re

# ---------------- CONFIG ---------------- #

TOKEN = "8772869279:AAHo18Q2T_UohwQSE-wj1EXfpo66O2_Zk84"
ADMIN_ID = 8758830915

UPLOAD_CHANNEL = "tuukqutwulsiliysiluysgksilut"
MAIN_CHANNEL = "@Burmese_Anime"

bot = telebot.TeleBot(TOKEN, threaded=True, num_threads=30)

DB_FILE = "files.json"
USERS_FILE = "users.json"

db_lock = threading.Lock()

# ---------------- LOAD DB ---------------- #

def load(file, default):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


files_db = load(DB_FILE, {})
users_db = set(load(USERS_FILE, []))


def save_db():
    with db_lock:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(files_db, f, indent=4, ensure_ascii=False)


def save_users():
    with db_lock:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(users_db), f, indent=4, ensure_ascii=False)

# ---------------- HELPERS ---------------- #

def normalize(text):
    return str(text).lower().replace(" ", "").replace("-", "").replace("_", "")


def get_ep(name):
    m = re.search(r'(?:ep|episode|e)\s*(\d+)', name.lower())
    return int(m.group(1)) if m else 999999

# ---------------- FORCE JOIN (MAIN CHANNEL) ---------------- #

def is_joined(user_id):
    try:
        m = bot.get_chat_member(MAIN_CHANNEL, user_id)
        return m.status in ["creator", "administrator", "member"]
    except:
        return False


def join_msg(chat_id):
    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(
        telebot.types.InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{MAIN_CHANNEL.replace('@','')}")
    )

    bot.send_message(
        chat_id,
        "❌ Please join channel first",
        reply_markup=kb
    )

# ---------------- AUTO DELETE ---------------- #

def auto_delete(chat_id, ids):
    time.sleep(300)
    for i in ids:
        try:
            bot.delete_message(chat_id, i)
        except:
            pass

# ---------------- SEND SINGLE (COPY MESSAGE) ---------------- #

def send_single(chat_id, data, sent):
    try:
        msg = bot.copy_message(
            chat_id=chat_id,
            from_chat_id=data["channel"],
            message_id=data["message_id"]
        )
        sent.append(msg.message_id)

    except Exception as e:
        print("Copy Error:", e)

# ---------------- FAST SEND ---------------- #

def fast_send(chat_id, files):
    sent = []

    files = sorted(files, key=lambda x: get_ep(x["name"]))

    for f in files:
        send_single(chat_id, f, sent)

    warn = bot.send_message(chat_id, f"✅ Sent {len(sent)} Episodes")
    sent.append(warn.message_id)

    threading.Thread(target=auto_delete, args=(chat_id, sent), daemon=True).start()

# ---------------- START ---------------- #

@bot.message_handler(commands=["start"])
def start(msg):
    uid = msg.from_user.id
    chat_id = msg.chat.id

    if uid not in users_db:
        users_db.add(uid)
        save_users()

    # FORCE JOIN MAIN CHANNEL
    if not is_joined(uid):
        return join_msg(chat_id)

    args = msg.text.split(maxsplit=1)

    if len(args) > 1:
        key = normalize(args[1])

        matched = [
            v for v in files_db.values()
            if key in normalize(v["name"])
        ]

        if matched:
            return fast_send(chat_id, matched)

        return bot.send_message(chat_id, "❌ Not Found")

    bot.send_message(chat_id, "🎬 Send Anime Link")

# ---------------- UPLOAD (ADMIN ONLY) ---------------- #

@bot.message_handler(content_types=["video", "document", "audio"])
def upload(msg):
    if msg.from_user.id != ADMIN_ID:
        return

    caption = msg.caption or "Anime"

    file_id = None
    ftype = None

    if msg.video:
        file_id = msg.video.file_id
        ftype = "video"

    elif msg.document:
        file_id = msg.document.file_id
        ftype = "document"

    elif msg.audio:
        file_id = msg.audio.file_id
        ftype = "audio"

    # STEP 1 → POST TO UPLOAD CHANNEL
    posted = bot.send_video(
        UPLOAD_CHANNEL,
        file_id,
        caption=caption
    ) if ftype == "video" else None

    # STEP 2 → SAVE MESSAGE ID FROM UPLOAD CHANNEL
    files_db[str(time.time())] = {
        "name": caption,
        "channel": UPLOAD_CHANNEL,
        "message_id": posted.message_id,
        "type": ftype,
        "caption": caption
    }

    save_db()

    bot.reply_to(msg, "✅ Saved to Upload System")

# ---------------- RUN ---------------- #

print("Bot Running...")

while True:
    try:
        bot.infinity_polling()
    except Exception as e:
        print("Error:", e)
        time.sleep(3)
