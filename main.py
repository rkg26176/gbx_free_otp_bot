import os
import sqlite3
import threading
import time
import requests
import telebot
from flask import Flask
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
    BotCommand,
)

BOT_NAME = "⚡ GBX PANEL BOT ⚡"
BOT_TOKEN = os.environ.get(
    "BOT_TOKEN", "7741642090:AAFzpuefQ4CHG10xy88RiYPqP1LVvt79_Ns"
)
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", 8053042225))

# Naya GitHub Mini App Link updated here
MINI_APP_URL = "https://rkg26176.github.io/gbx_free_otp_bot/"

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

user_states = {}
DB_NAME = "bot_panel_database.db"


def init_db():
  try:
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY,"
        " is_blocked INTEGER DEFAULT 0)"
    )
    conn.commit()
    conn.close()
  except Exception as e:
    print("DB Error:", e)


init_db()


def get_db_connection():
  conn = sqlite3.connect(DB_NAME, check_same_thread=False)
  conn.row_factory = sqlite3.Row
  return conn


def register_or_get_user(user_id):
  try:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
      cursor.execute("INSERT OR IGNORE INTO users (user_id, is_blocked) VALUES (?, 0)", (user_id,))
      conn.commit()
      cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
      user = cursor.fetchone()
    conn.close()
    
    if user:
      return dict(user)
    return {"user_id": user_id, "is_blocked": 0}
  except Exception as e:
    print("User register error:", e)
    return {"user_id": user_id, "is_blocked": 0}


def update_user_data(user_id, field, value):
  try:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, is_blocked) VALUES (?, 0)", (user_id,))
    cursor.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
    conn.close()
  except Exception as e:
    print("Update error:", e)


def get_all_users():
  try:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE is_blocked = 0")
    rows = cursor.fetchall()
    conn.close()
    return [row["user_id"] for row in rows]
  except Exception:
    return []


def is_user_blocked(user_id):
  if user_id == ADMIN_CHAT_ID:
    return False
  user_data = register_or_get_user(user_id)
  return int(user_data.get("is_blocked", 0)) == 1


CHANNELS = {
    "-1003332858806": {
        "name": "📢 JOIN GBX LOOT",
        "url": "https://t.me/+6ByfGDRBKgsxMjZl",
    },
    "-1003630519339": {
        "name": "📢 JOIN GBX EARN",
        "url": "https://t.me/+OWrCoeF-JutmNjg1",
    },
    "-1003197501531": {
        "name": "📢 JOIN GBX ZONE",
        "url": "https://t.me/+f2mWfDs6EUIxYTBl",
    },
    "-1003862251237": {
        "name": "💬 JOIN GROUP CHAT",
        "url": "https://t.me/+O_-kEF2f5f1kMjdl",
    },
}


@app.route("/")
def home():
  return "⚡ GBX Panel Bot is Running Live!"


def get_user_status_map(user_id):
  status_map = {}
  for channel_id in CHANNELS:
    try:
      member = bot.get_chat_member(chat_id=int(channel_id), user_id=user_id)
      status_map[channel_id] = member.status not in [
          "left",
          "kicked",
          "restricted",
      ]
    except Exception:
      status_map[channel_id] = False
  return status_map


def show_dynamic_force_join(chat_id, user_name, status_map, message_id=None):
  text = (
      f"⚠️ **ACCESS DENIED, {user_name} !**\n\n"
      "🔒 Bot ko use karne ke liye aapko niche diye gaye sabhi official channels & chat group ko join karna zaroori hai.\n\n"
      "👇 **Sabhi par click karke join karein:**"
  )
  markup = InlineKeyboardMarkup(row_width=1)
  for ch_id, ch_info in CHANNELS.items():
    if not status_map[ch_id]:
      markup.add(
          InlineKeyboardButton(text=ch_info["name"], url=ch_info["url"])
      )
  markup.add(
      InlineKeyboardButton(
          text="🔄 CHECK JOINED STATUS & VERIFY", callback_data="verify_join"
      )
  )
  try:
    if message_id:
      bot.edit_message_text(
          text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown"
      )
    else:
      bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")
  except Exception:
    pass


def show_main_menu(chat_id, user_name):
  text = (
      f"👑 **WELCOME TO GBX PANEL, {user_name} !**\n\n"
      "✨ Aapka Web Panel fully **UNLOCKED** hai!\n"
      "🚀 Yahan aapko direct access milta hai.\n\n"
      "👇 Niche diye gaye button par click karke apna panel open karein:"
  )
  markup = InlineKeyboardMarkup(row_width=1)
  markup.add(
      InlineKeyboardButton(
          text="🌐 OPEN WEB MINI APP PANEL",
          web_app=WebAppInfo(url=MINI_APP_URL),
      )
  )

  bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")


def check_join_and_block(user_id, chat_id, user_name):
  if is_user_blocked(user_id):
    try:
      bot.send_message(chat_id, "❌ **Aapko Admin dwara bot se block kar diya gaya hai.**", parse_mode="Markdown")
    except Exception:
      pass
    return False

  status_map = get_user_status_map(user_id)
  if not all(status_map.values()):
    show_dynamic_force_join(chat_id, user_name, status_map)
    return False
  return True


@bot.message_handler(commands=["start"])
def start_command(message):
  if message.chat.type != "private":
    return
  user_id = message.from_user.id
  user_name = message.from_user.first_name
  user_states.pop(user_id, None)

  register_or_get_user(user_id)

  if is_user_blocked(user_id):
    bot.reply_to(message, "❌ **Aapko Admin dwara bot se block kar diya gaya hai.**", parse_mode="Markdown")
    return

  status_map = get_user_status_map(user_id)
  if all(status_map.values()):
    show_main_menu(message.chat.id, user_name)
  else:
    show_dynamic_force_join(message.chat.id, user_name, status_map)


@bot.message_handler(commands=["panel"])
def panel_command(message):
  if message.chat.type != "private":
    return
  user_id = message.from_user.id
  user_name = message.from_user.first_name

  if not check_join_and_block(user_id, message.chat.id, user_name):
    return

  show_main_menu(message.chat.id, user_name)


@bot.message_handler(commands=["admin"])
def admin_command(message):
  if message.chat.type != "private":
    return
  
  if message.chat.id != ADMIN_CHAT_ID:
    bot.reply_to(message, "❌ **Access Denied!** Yeh command sirf Admin ke liye hai.", parse_mode="Markdown")
    return
  
  markup = InlineKeyboardMarkup(row_width=1)
  markup.add(
      InlineKeyboardButton(text="📬 Broadcast Message", callback_data="admin_broadcast_mode"),
      InlineKeyboardButton(text="👥 Active Users List", callback_data="admin_userlist_menu"),
      InlineKeyboardButton(text="🚫 Block User", callback_data="block_user_prompt"),
      InlineKeyboardButton(text="✅ Unblock User", callback_data="unblock_user_prompt")
  )
  bot.send_message(
      message.chat.id,
      "🛠️ **ADMIN MASTER DASHBOARD**\n\n"
      "Apne controls yahan se manage karein:",
      reply_markup=markup,
      parse_mode="Markdown"
  )


def generate_userlist_text(page=0):
  active_users = get_all_users()
  per_page = 10
  text = f"📋 **ACTIVE USERS DATABASE**\n\n"
  
  if active_users:
    start_idx = page * per_page
    end_idx = start_idx + per_page
    current_slice = active_users[start_idx:end_idx]
    
    if not current_slice and page > 0:
      return None, 0
      
    for idx, uid in enumerate(current_slice, start_idx + 1):
      text += f"{idx}. User ID: `{uid}`\n"
      
    total_pages = (len(active_users) - 1) // per_page
    has_next = page < total_pages
  else:
    text += "No active users found.\n"
    has_next = False
    
  return text, has_next


@bot.message_handler(commands=["userlist"])
def userlist_command(message):
  if message.chat.type != "private":
    return
    
  if message.chat.id != ADMIN_CHAT_ID:
    bot.reply_to(message, "❌ **Access Denied!**", parse_mode="Markdown")
    return
  
  text, has_next = generate_userlist_text(0)
  markup = InlineKeyboardMarkup(row_width=2)
  
  if has_next:
    markup.add(InlineKeyboardButton(text="➡️ Next Page", callback_data="ul_page:1"))

  bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("ul_page:"))
def handle_userlist_pagination(call):
  if call.from_user.id != ADMIN_CHAT_ID:
    return
  try:
    page = int(call.data.split(":")[1])
  except Exception:
    page = 0
    
  text, has_next = generate_userlist_text(page)
  markup = InlineKeyboardMarkup(row_width=2)
  
  if has_next:
    markup.add(InlineKeyboardButton(text="➡️ Next", callback_data=f"ul_page:{page + 1}"))
  if page > 0:
    markup.add(InlineKeyboardButton(text="⬅️ Prev", callback_data=f"ul_page:{page - 1}"))
  
  try:
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
  except Exception:
    pass
  try:
    bot.answer_callback_query(call.id)
  except Exception:
    pass


@bot.callback_query_handler(func=lambda call: call.data == "admin_userlist_menu")
def handle_admin_menu_callbacks(call):
  if call.from_user.id != ADMIN_CHAT_ID:
    return
  userlist_command(call.message)


@bot.callback_query_handler(func=lambda call: call.data in ["block_user_prompt", "unblock_user_prompt"])
def handle_block_prompts(call):
  if call.from_user.id != ADMIN_CHAT_ID:
    return
  try:
    bot.answer_callback_query(call.id)
  except Exception:
    pass

  if call.data == "block_user_prompt":
    user_states[ADMIN_CHAT_ID] = "waiting_for_block_user"
    bot.send_message(call.message.chat.id, "👉 Jise block karna hai uski **User ID** bhejein:\n\n❌ Cancel: `/cancel`")
  elif call.data == "unblock_user_prompt":
    user_states[ADMIN_CHAT_ID] = "waiting_for_unblock_user"
    bot.send_message(call.message.chat.id, "👉 Jise unblock karna hai uski **User ID** bhejein:\n\n❌ Cancel: `/cancel`")


@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast_mode")
def admin_broadcast_callback(call):
  if call.from_user.id != ADMIN_CHAT_ID:
    return
  user_states[ADMIN_CHAT_ID] = "waiting_for_broadcast"
  bot.answer_callback_query(call.id, "Broadcast mode activated!")
  bot.send_message(
      call.message.chat.id,
      "✍️ **Ab jo bhi message bhejenge vah sabhi active users ko broadcast ho jayega.**\n\n❌ Cancel: `/cancel`",
      parse_mode="Markdown"
  )


@bot.message_handler(commands=["cancel"])
def cancel_command(message):
  if message.chat.id != ADMIN_CHAT_ID:
    return
  user_states.pop(ADMIN_CHAT_ID, None)
  bot.send_message(message.chat.id, "❌ Action successfully cancelled.")


@bot.callback_query_handler(func=lambda call: call.data == "verify_join")
def handle_verification(call):
  if call.message.chat.type != "private":
    return
  user_id = call.from_user.id
  
  if is_user_blocked(user_id):
    bot.answer_callback_query(call.id, "❌ Aapko block kar diya gaya hai!", show_alert=True)
    return

  status_map = get_user_status_map(user_id)
  if all(status_map.values()):
    bot.answer_callback_query(call.id, "🎉 Verified Successfully!")
    try:
      bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
      pass
    show_main_menu(call.message.chat.id, call.from_user.first_name)
  else:
    bot.answer_callback_query(
        call.id, "❌ Kripya pehle sabhi required channels join karein!", show_alert=True
    )
    show_dynamic_force_join(
        call.message.chat.id,
        call.from_user.first_name,
        status_map,
        call.message.message_id,
    )


@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'sticker', 'audio', 'animation'])
def handle_all_messages(message):
  if message.chat.type != "private":
    return
  user_id = message.from_user.id
  user_name = message.from_user.first_name

  register_or_get_user(user_id)

  if not check_join_and_block(user_id, message.chat.id, user_name):
    return

  if user_id == ADMIN_CHAT_ID and user_states.get(ADMIN_CHAT_ID) == "waiting_for_broadcast":
    user_states.pop(ADMIN_CHAT_ID, None)
    users = get_all_users()
    success = 0
    fail = 0
    
    status_msg = bot.send_message(ADMIN_CHAT_ID, "🚀 Broadcasting message to all active users...")

    for uid in users:
      try:
        bot.copy_message(chat_id=uid, from_chat_id=ADMIN_CHAT_ID, message_id=message.message_id)
        success += 1
        time.sleep(0.04)
      except Exception:
        fail += 1

    bot.edit_message_text(
        f"✅ **Broadcast Completed!**\n\nSuccess: `{success}`\nFailed: `{fail}`",
        ADMIN_CHAT_ID,
        status_msg.message_id,
        parse_mode="Markdown"
    )
    return

  if user_id == ADMIN_CHAT_ID and user_states.get(ADMIN_CHAT_ID) == "waiting_for_block_user":
    user_states.pop(ADMIN_CHAT_ID, None)
    try:
      target_id = int(message.text.strip())
      update_user_data(target_id, "is_blocked", 1)
      bot.reply_to(message, f"✅ Success! User `{target_id}` ko bot se block kar diya gaya hai.", parse_mode="Markdown")
      try:
        bot.send_message(target_id, "❌ **Aapko Admin dwara bot se block kar diya gaya hai.**")
      except Exception:
        pass
    except ValueError:
      bot.reply_to(message, "❌ Invalid ID. Sirf numbers bhejein.")
    return

  if user_id == ADMIN_CHAT_ID and user_states.get(ADMIN_CHAT_ID) == "waiting_for_unblock_user":
    user_states.pop(ADMIN_CHAT_ID, None)
    try:
      target_id = int(message.text.strip())
      update_user_data(target_id, "is_blocked", 0)
      bot.reply_to(message, f"✅ Success! User `{target_id}` ko unblock kar diya gaya hai.", parse_mode="Markdown")
      try:
        bot.send_message(target_id, "✅ **Aapko Admin dwara unblock kar diya gaya hai! Ab aap bot use kar sakte hain.**")
      except Exception:
        pass
    except ValueError:
      bot.reply_to(message, "❌ Invalid ID.")
    return


def set_bot_commands(bot_instance):
  commands = [
      BotCommand("start", "Start the bot"),
      BotCommand("panel", "Open Web Panel Menu"),
      BotCommand("admin", "Admin Dashboard"),
      BotCommand("userlist", "View Active Users List")
  ]
  try:
    bot_instance.set_my_commands(commands)
  except Exception as e:
    print("Set commands error:", e)


def run_bot():
  while True:
    try:
      bot.remove_webhook()
      time.sleep(1)
      set_bot_commands(bot)
      print("Bot Polling Active...")
      bot.infinity_polling(
          timeout=30, long_polling_timeout=30, skip_pending=True
      )
    except Exception as e:
      print("Polling error:", e)
      time.sleep(5)


if __name__ == "__main__":
  t = threading.Thread(target=run_bot, daemon=True)
  t.start()

  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
