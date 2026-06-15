import asyncio, sqlite3, uuid, os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = "7037415424"
BOT_USERNAME = "TMBD0_BOT"
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

JOIN_CHANNEL = "-1004394875788"
JOIN_CHANNEL_LINK = "https://t.me/+efq1n13g-vlkNTZl"
JOIN_CHANNEL = "-1004394875788"
JOIN_CHANNEL_LINK = "https://t.me/+efq1n13g-vlkNTZl"

print("JOIN_CHANNEL =", JOIN_CHANNEL)
print("JOIN_CHANNEL_LINK =", JOIN_CHANNEL_LINK)

batch_mode = {}
batch_mode = {}

conn = sqlite3.connect("files.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS batches (batch_id TEXT PRIMARY KEY, msg_ids TEXT)")
conn.commit()

async def set_menu(app):
    await app.bot.set_my_commands([
        BotCommand("start", "Start"),
        BotCommand("batchstart", "Start batch upload"),
        BotCommand("batchend", "End batch and get link"),
        BotCommand("help", "Help"),
    ])

def join_btn(batch_id=None):
    buttons = [[InlineKeyboardButton("📢 Join Channel", url=JOIN_CHANNEL_LINK)]]
    if batch_id:
        buttons.append([InlineKeyboardButton("✅ Joined - Try Again", url=f"https://t.me/{BOT_USERNAME}?start=batch_{batch_id}")])
    return InlineKeyboardMarkup(buttons)

async def is_joined(context, user_id):
    try:
        m = await context.bot.get_chat_member(JOIN_CHANNEL, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

async def delete_later(context, chat_id, msg_id):
    await asyncio.sleep(300)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
    except:
        pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args and context.args[0].startswith("batch_"):
        batch_id = context.args[0].replace("batch_", "")

        if not await is_joined(context, update.effective_user.id):
            await update.message.reply_text(
                "🔒 File locked.\n\nFirst join channel, then click Try Again.",
                reply_markup=join_btn(batch_id)
            )
            return

        cur.execute("SELECT msg_ids FROM batches WHERE batch_id=?", (batch_id,))
        row = cur.fetchone()

        if not row:
            await update.message.reply_text("❌ Batch expired / not found.")
            return

        msg_ids = row[0].split(",")

        info = await update.message.reply_text(f"✅ Sending {len(msg_ids)} files...\n⏳ Files delete in 5 minutes.")

        for mid in msg_ids:
            sent = await context.bot.copy_message(
                chat_id=update.effective_chat.id,
                from_chat_id=CHANNEL_ID,
                message_id=int(mid)
            )
            asyncio.create_task(delete_later(context, update.effective_chat.id, sent.message_id))

        asyncio.create_task(delete_later(context, update.effective_chat.id, info.message_id))
        return

    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Access denied.")
        return

    await update.message.reply_text(
        "👑 Owner Mode\n\n/batchstart - bulk upload start\n/batchend - link get"
    )

async def batchstart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Access denied.")
        return

    batch_mode[OWNER_ID] = []
    await update.message.reply_text("✅ Batch started.\n\nNow send all files/photos/videos.\nFinish with /batchend")

async def batchend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Access denied.")
        return

    ids = batch_mode.get(OWNER_ID, [])

    if not ids:
        await update.message.reply_text("❌ No files added.")
        return

    batch_id = uuid.uuid4().hex[:10]
    cur.execute("INSERT INTO batches VALUES (?, ?)", (batch_id, ",".join(map(str, ids))))
    conn.commit()

    link = f"https://t.me/{BOT_USERNAME}?start=batch_{batch_id}"

    batch_mode.pop(OWNER_ID, None)

    await update.message.reply_text(
        f"✅ Batch ready\n\n📦 Files: {len(ids)}\n🔗 Link:\n{link}"
    )

async def save_any(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Access denied.")
        return

    try:
        copied = await update.message.copy(chat_id=CHANNEL_ID)

        if OWNER_ID in batch_mode:
            batch_mode[OWNER_ID].append(copied.message_id)
            await update.message.reply_text(f"✅ Added to batch: {len(batch_mode[OWNER_ID])}")
        else:
            batch_id = uuid.uuid4().hex[:10]
            cur.execute("INSERT INTO batches VALUES (?, ?)", (batch_id, str(copied.message_id)))
            conn.commit()
            link = f"https://t.me/{BOT_USERNAME}?start=batch_{batch_id}"
            await update.message.reply_text(f"✅ Saved\n\n🔗 Link:\n{link}")

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/batchstart\nSend files\n/batchend")

app = Application.builder().token(TOKEN).post_init(set_menu).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("batchstart", batchstart))
app.add_handler(CommandHandler("batchend", batchend))
app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, save_any))

print("Batch File Store Bot Running...")
app.run_polling()
