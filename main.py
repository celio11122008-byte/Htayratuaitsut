# ---------------- IMPORTS ---------------- #
import telebot
import json
import os
import base64
import time
import threading
from concurrent.futures import ThreadPoolExecutor

# ---------------- CONFIG ---------------- #
TOKEN = "8772869279:AAHuxhvC6kpeEjsjspUjtbBvIXkmp9Z54iQ"
ADMIN_ID = 8758830915

bot = telebot.TeleBot(TOKEN, threaded=False)

# ---------------- FILES ---------------- #
DB_FILE = "files.json"
USERS_FILE = "users.json"

CHANNEL_USERNAME = "@Burmese_Anime"
CHANNEL_LINK = "https://t.me/Burmese_Anime"

lock = threading.Lock()

# ---------------- LOAD ---------------- #
def load(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default
    return default

files_db = load(DB_FILE, {})
users_db = set(load(USERS_FILE, []))

# ---------------- SAVE ---------------- #
def save(path, data):
    tmp = path + ".tmp"
    with lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)

# ---------------- HELPERS ---------------- #
def normalize(t):
    return str(t or "").lower().strip().replace(" ", "").replace("-", "").replace("_", "")

def encode(t):
    return base64.urlsafe_b64encode(t.encode()).decode()

def decode(t):
    try:
        return base64.urlsafe_b64decode(t + "==").decode()
    except:
        return None

# ---------------- CHANNEL CHECK ---------------- #
def is_joined(uid):
    try:
        m = bot.get_chat_member(CHANNEL_USERNAME, uid)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

def join_msg(cid):
    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(telebot.types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
    bot.send_message(cid, "❌ Please join channel first", reply_markup=kb)

# ---------------- FAST SEND ---------------- #
def send_file(cid, data):
    try:
        cap = data.get("caption", "")

        if data["type"] == "document":
            m = bot.send_document(cid, data["file_id"], caption=cap)
        elif data["type"] == "video":
            m = bot.send_video(cid, data["file_id"], caption=cap, supports_streaming=True)
        elif data["type"] == "audio":
            m = bot.send_audio(cid, data["file_id"], caption=cap)
        else:
            return None

        return m.message_id
    except:
        return None


def fast_send(cid, files):
    sent = []

    with ThreadPoolExecutor(max_workers=5) as ex:
        results = ex.map(lambda f: send_file(cid, f), files)

    for r in results:
        if r:
            sent.append(r)

    bot.send_message(cid, f"✅ Sent {len(sent)} files")

    def auto_del():
        time.sleep(300)
        for i in sent:
            try:
                bot.delete_message(cid, i)
            except:
                pass

    threading.Thread(target=auto_del, daemon=True).start()

# ---------------- START ---------------- #
@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id
    cid = m.chat.id

    if uid not in users_db:
        users_db.add(uid)
        save(USERS_FILE, list(users_db))

    if not is_joined(uid):
        return join_msg(cid)

    args = m.text.split(maxsplit=1)

    if len(args) > 1:
        key = normalize(decode(args[1]) or "")

        matched = [
            v for v in files_db.values()
            if key in normalize(v["name"])
        ]

        if matched:
            return fast_send(cid, matched)

        return bot.send_message(cid, "❌ Not found")

    bot.send_message(cid,
        f"🎬 Anime Bot\nFiles: {len(files_db)}"
    )

# ---------------- UPLOAD ---------------- #
@bot.message_handler(content_types=["document", "video", "audio"])
def upload(m):

    if m.from_user.id != ADMIN_ID:
        return bot.reply_to(m, "Admin only")

    cap = m.caption or ""

    if m.document:
        fid = m.document.file_id
        name = cap or m.document.file_name
        t = "document"

    elif m.video:
        fid = m.video.file_id
        name = cap or "video"
        t = "video"

    elif m.audio:
        fid = m.audio.file_id
        name = cap or "audio"
        t = "audio"
    else:
        return

    for v in files_db.values():
        if v["file_id"] == fid:
            return bot.reply_to(m, "Already exists")

    key = str(int(time.time() * 1000))

    files_db[key] = {
        "file_id": fid,
        "name": name,
        "type": t,
        "caption": cap,
        "time": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    save(DB_FILE, files_db)

    link = f"https://t.me/{bot.get_me().username}?start={encode(normalize(name))}"

    bot.reply_to(m, f"Saved ✅\n{name}")
    bot.send_message(m.chat.id, f"🔗 {link}")

# ---------------- DELETE ---------------- #
@bot.message_handler(commands=["delete"])
def delete(m):
    if m.from_user.id != ADMIN_ID:
        return

    args = m.text.split(maxsplit=1)
    if len(args) < 2:
        return

    key = args[1]

    if key in files_db:
        del files_db[key]
        save(DB_FILE, files_db)
        bot.reply_to(m, "Deleted")
    else:
        bot.reply_to(m, "Not found")

# ---------------- DELETE ALL ---------------- #
@bot.message_handler(commands=["deleteall"])
def delete_all(m):
    if m.from_user.id != ADMIN_ID:
        return

    files_db.clear()
    save(DB_FILE, files_db)

    bot.reply_to(m, "All deleted")

# ---------------- DELETE BY NAME ---------------- #
@bot.message_handler(commands=["delname"])
def delname(m):
    if m.from_user.id != ADMIN_ID:
        return

    name = normalize(m.text.split(maxsplit=1)[1])

    removed = 0
    for k in list(files_db.keys()):
        if name in normalize(files_db[k]["name"]):
            del files_db[k]
            removed += 1

    save(DB_FILE, files_db)
    bot.reply_to(m, f"Deleted {removed}")

# ---------------- STATS ---------------- #
@bot.message_handler(commands=["stats"])
def stats(m):
    if m.from_user.id != ADMIN_ID:
        return

    bot.send_message(m.chat.id,
        f"""
📊 Stats

👥 Users: {len(users_db)}
🎬 Files: {len(files_db)}
"""
    )

# ---------------- BACKUP ---------------- #
@bot.message_handler(commands=["backup"])
def backup(m):
    if m.from_user.id != ADMIN_ID:
        return

    data = {
        "files": files_db,
        "users": list(users_db)
    }

    with open("backup.json", "w") as f:
        json.dump(data, f, indent=2)

    with open("backup.json", "rb") as f:
        bot.send_document(m.chat.id, f)

    os.remove("backup.json")

# ---------------- RUN ---------------- #
print("BOT RUNNING...")

while True:
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print("ERROR:", e)
        time.sleep(3)
