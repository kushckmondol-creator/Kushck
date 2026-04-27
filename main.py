from telegram import *
from telegram.ext import *
import sqlite3

TOKEN = "
8653553246:AAFJUKy4CpSH8G2bSzQro2_WrI8m9IbT-AI"
ADMIN_ID = 8653553246

conn = sqlite3.connect("bot.db", check_same_thread=False)
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, balance INTEGER)")
conn.commit()

game_queue = {50: [], 100: [], 200: [], 300: []}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.effective_user.first_name

    c.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?)", (uid, name, 0))
    conn.commit()

    keyboard = [
        ["💰 Deposit", "💳 Withdraw"],
        ["🎯 Play Game", "📊 Account"],
        ["🆘 Support"]
    ]

    await update.message.reply_text("Welcome", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

async def account(update: Update, context):
    uid = update.effective_user.id
    c.execute("SELECT balance FROM users WHERE id=?", (uid,))
    bal = c.fetchone()[0]
    await update.message.reply_text(f"ID: {uid}\nBalance: {bal}")

async def deposit(update: Update, context):
    keyboard = [["100","200","300","500"]]
    await update.message.reply_text("Amount?", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

async def deposit_amount(update: Update, context):
    context.user_data["deposit"] = update.message.text
    await update.message.reply_text(
        "PAYMENT 💳\nBKASH - 01618259253\nNAGAD - 01759439760\n\nSend TRXID"
    )

async def trx(update: Update, context):
    uid = update.effective_user.id
    trxid = update.message.text
    amt = context.user_data.get("deposit")

    keyboard = [[
        InlineKeyboardButton("Approve", callback_data=f"dep_ok_{uid}_{amt}"),
        InlineKeyboardButton("Reject", callback_data=f"dep_no_{uid}_{amt}")
    ]]

    await context.bot.send_message(
        ADMIN_ID,
        f"Deposit Request\nUser:{uid}\nAmount:{amt}\nTRX:{trxid}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await update.message.reply_text("Waiting for admin approval")

async def withdraw(update: Update, context):
    keyboard = [["100","300","500"]]
    await update.message.reply_text("Withdraw amount?", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

async def withdraw_amount(update: Update, context):
    context.user_data["withdraw"] = update.message.text
    await update.message.reply_text("Send your number")

async def withdraw_number(update: Update, context):
    uid = update.effective_user.id
    num = update.message.text
    amt = context.user_data.get("withdraw")

    keyboard = [[
        InlineKeyboardButton("Approve", callback_data=f"wd_ok_{uid}_{amt}"),
        InlineKeyboardButton("Reject", callback_data=f"wd_no_{uid}_{amt}")
    ]]

    await context.bot.send_message(
        ADMIN_ID,
        f"Withdraw Request\nUser:{uid}\nAmount:{amt}\nNumber:{num}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await update.message.reply_text("Request sent to admin")

async def game(update: Update, context):
    keyboard = [["50","100","200","300"]]
    await update.message.reply_text("Select bet", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

async def join_game(update: Update, context):
    uid = update.effective_user.id
    amt = int(update.message.text)

    c.execute("SELECT balance FROM users WHERE id=?", (uid,))
    bal = c.fetchone()[0]

    if bal < amt:
        await update.message.reply_text("Not enough balance")
        return

    c.execute("UPDATE users SET balance=balance-? WHERE id=?", (amt, uid))
    conn.commit()

    game_queue[amt].append(uid)

    await update.message.reply_text("Waiting for players...")

    if len(game_queue[amt]) == 6:
        players = game_queue[amt]

        msg = "✅ 6 Players Ready\n"
        for i, p in enumerate(players):
            msg += f"Player {i+1}: {p}\n"

        await context.bot.send_message(ADMIN_ID, msg)
        game_queue[amt] = []

async def admin(update: Update, context):
    query = update.callback_query
    await query.answer()

    data = query.data.split("_")

    uid = int(data[2])
    amt = int(data[3])

    if data[0] == "dep":
        if data[1] == "ok":
            c.execute("UPDATE users SET balance=balance+? WHERE id=?", (amt, uid))
            conn.commit()
            await context.bot.send_message(uid, f"🎉 Deposit Success\nBalance: {amt}")
        else:
            await context.bot.send_message(uid, "Deposit Rejected")

    elif data[0] == "wd":
        if data[1] == "ok":
            c.execute("UPDATE users SET balance=balance-? WHERE id=?", (amt, uid))
            conn.commit()
            await context.bot.send_message(uid, "Withdraw Success 🎉")
        else:
            await context.bot.send_message(uid, "Withdraw Rejected")

async def broadcast(update: Update, context):
    if update.effective_user.id != ADMIN_ID:
        return

    msg = " ".join(context.args)

    c.execute("SELECT id FROM users")
    all_users = c.fetchall()

    for u in all_users:
        try:
            await context.bot.send_message(u[0], msg)
        except:
            pass

    await update.message.reply_text("Broadcast Sent")

async def handle(update: Update, context):
    text = update.message.text

    if text == "💰 Deposit":
        await deposit(update, context)

    elif text in ["100","200","300","500"]:
        await deposit_amount(update, context)

    elif text == "💳 Withdraw":
        await withdraw(update, context)

    elif text in ["100","300","500"]:
        await withdraw_amount(update, context)

    elif text == "🎯 Play Game":
        await game(update, context)

    elif text in ["50","100","200","300"]:
        await join_game(update, context)

    elif text == "📊 Account":
        await account(update, context)

    elif text == "🆘 Support":
        await update.message.reply_text("Support: @TeamLordAdmin")

    else:
        if "withdraw" in context.user_data:
            await withdraw_number(update, context)
        else:
            await trx(update, context)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(CallbackQueryHandler(admin))
app.add_handler(MessageHandler(filters.TEXT, handle))

app.run_polling()