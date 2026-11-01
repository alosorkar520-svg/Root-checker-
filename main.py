import telebot
import pytesseract
import re
from PIL import Image
import os
import time
from datetime import datetime
from telebot.types import BotCommand, InlineKeyboardMarkup, InlineKeyboardButton, BotCommandScopeChat, BotCommandScopeDefault
from flask import Flask
from threading import Thread
import sqlite3

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

BOT_TOKEN = '8706257660:AAH6XwALZhdGrbog7tBdcAR9g2dUA31KUn8'

telebot.apihelper.CONNECT_TIMEOUT = 30
telebot.apihelper.READ_TIMEOUT = 30

bot = telebot.TeleBot(BOT_TOKEN)

ADMIN_CHAT_ID = 6941124212  

# 📢 FORCE JOIN CHANNEL SETUP
CHANNEL_USERNAME = "@osmanbhaiofficials"
CHANNEL_LINK = "https://t.me/osmanbhaiofficials"

def check_user_joined(user_id):
    """ইউজার চ্যানেলে জয়েন আছে কিনা তা চেক করবে"""
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['creator', 'administrator', 'member']:
            return True
        return False
    except Exception as e:
        print(f"Force Join Check Error: {e}")
        return False

def get_join_keyboard():
    """জয়েন করার ইনলাইন কিবোর্ড তৈরি করবে"""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📢 Join Group / Channel", url=CHANNEL_LINK))
    markup.add(InlineKeyboardButton("✅ Verify / Check Again", callback_data="check_join"))
    return markup

# ==================== DATABASE SETUP ====================

def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY,
            scans_count INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('INSERT OR IGNORE INTO stats (id, scans_count) VALUES (1, 0)')
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def increment_scan_count():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE stats SET scans_count = scans_count + 1 WHERE id = 1')
    conn.commit()
    conn.close()

def get_stats_data():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT scans_count FROM stats WHERE id = 1')
    res = cursor.fetchone()
    total_scans = res[0] if res else 0
    
    conn.close()
    return total_users, total_scans

def get_all_users():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    conn.close()
    return [user[0] for user in users]

init_db()

# ==================== BOT LOGIC ====================

SUPPORTED_BRANDS = [
    "motorola", "moto", "samsung", "xiaomi", "poco", "redmi", "oneplus", 
    "zte", "redmagic", "realme", "oppo", "infinix", "tecno", 
    "itel", "symphony", "walton", "galaxy", "pixel", "narzo", "helio"
]

REALME_UNISOC_SUPPORTED = [
    "realme c11 2021", "c11 2021",
    "realme c21y", "c21y",
    "realme c25y", "c25y",
    "realme c33", "c33",
    "realme c35", "c35",
    "realme c51", "c51",
    "realme c53", "c53",
    "realme c61", "c61",
    "realme c63", "c63",
    "realme c71", "c71",
    "realme note 50", "note 50"
]

def set_bot_commands():
    try:
        default_commands = [
            BotCommand("start", "✨ start"),
            BotCommand("contact", "📞 contact")
        ]
        bot.set_my_commands(default_commands, scope=BotCommandScopeDefault())

        admin_commands = [
            BotCommand("start", "✨ start"),
            BotCommand("contact", "📞 contact"),
            BotCommand("panel", "👨‍💻 admin panel")
        ]
        bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(ADMIN_CHAT_ID))
    except Exception as e:
        print(f"Error setting commands: {e}")

def clean_device_name(raw_text):
    lines = [re.split(r'\s{2,}', line.strip()) for line in raw_text.split('\n') if line.strip()]
    device_name = "Not Detected"
    
    for line_list in lines:
        line_clean = " ".join(line_list).strip()
        
        helio_match = re.search(r'(?i)\b(helio\s+[a-z0-9]+)\b', line_clean)
        if helio_match:
            return helio_match.group(1).title()

        galaxy_match = re.search(r'(?i)\b(galaxy\s+[a-z0-9]+(?:\s+5g|\s+pro|\s+plus|\s+lite)?)\b', line_clean)
        if galaxy_match:
            return galaxy_match.group(1).title()
            
        moto_match = re.search(r'(?i)\b(moto\s+[a-z0-9]+(?:\s+5g|\s+pro|\s+plus|\s+lite)?)\b', line_clean)
        if moto_match:
            return moto_match.group(1).title()

        pixel_match = re.search(r'(?i)\b(?:google\s+)?(pixel\s+[0-9a-z]+(?:\s+pro|\s+xl|\s+a|\s+fold)?)\b', line_clean)
        if pixel_match:
            return pixel_match.group(1).title()
            
        oneplus_match = re.search(r'(?i)\b(oneplus\s+[a-z0-9\s]+)\b', line_clean)
        if oneplus_match:
            return oneplus_match.group(1).title()

    for i, cols in enumerate(lines):
        for j, col in enumerate(cols):
            if any(keyword in col.lower() for keyword in ["device name", "phone name", "model name", "model"]):
                temp_name = re.sub(r'(?i)device\s*name|model\s*name|model|phone\s*name|device\s*:', '', col).replace(":", "").replace(">", "").strip()
                if temp_name and temp_name.lower() != "device name" and not any(x in temp_name.lower() for x in ["storage", "ram", "processor", "battery", "android", "number"]):
                    device_name = temp_name
                    break
                
                if i + 1 < len(lines) and j < len(lines[i+1]):
                    next_val = lines[i+1][j].replace(">", "").strip()
                    if next_val and not any(x in next_val.lower() for x in ["storage", "ram", "processor", "battery", "android", "version", "number"]):
                        device_name = next_val
                        break
        if device_name != "Not Detected":
            break
            
    if device_name == "Not Detected" or len(device_name) < 3:
        for line_list in lines:
            line_clean = " ".join(line_list).strip()
            if any(b in line_clean.lower() for b in SUPPORTED_BRANDS + ["vivo", "iqoo", "huawei", "honor"]):
                line_clean = re.sub(r'(?i)model\s*number.*', '', line_clean)
                device_name = line_clean.replace(">", "").strip()
                break
                
    device_name = re.sub(r'(?i)device\s*name\s*|model\s*name\s*|model\s*', '', device_name).strip()
    return device_name.title() if device_name else "Not Detected"

def extract_android_version(text):
    matches = re.findall(r'(?:android\s*version|android|version)\s*(?::)?\s*(\d{1,2})', text, re.IGNORECASE)
    if matches:
        for match in matches:
            if 9 <= int(match) <= 16:
                return match
        return matches[0]
        
    raw_numbers = re.findall(r'\b(1[0-6]|[9])\b', text)
    if raw_numbers:
        return raw_numbers[0]
        
    return "Not Detected"

def detect_cpu(text):
    if any(x in text for x in ["mediatek", "helio", "dimensity", " mtk", " mt6"]):
        return "MediaTek"
    elif any(x in text for x in ["snapdragon", "qualcomm", " sm6", " sm7", " sm8", " sdm", "g45"]):
        return "Qualcomm Snapdragon"
    elif any(x in text for x in ["exynos", "s5e", "galaxy", "sm-a217", "sm-a", "sm-m"]):
        return "Samsung Exynos"
    elif any(x in text for x in ["unisoc", "spreadtrum", "ums"]):
        return "Unisoc"
    elif any(x in text for x in ["tensor", "google", "gs101", "gs201"]):
        return "Google Tensor"
    return "Not Detected"

def detect_os_ui(text):
    if "oxygenos" in text or "oxygen" in text:
        return "OxygenOS"
    elif "hyperos" in text:
        return "HyperOS"
    elif "miui" in text:
        return "MIUI"
    elif "coloros" in text:
        return "ColorOS"
    elif "realme ui" in text:
        return "Realme UI"
    elif any(x in text for x in ["one ui", "galaxy", "samsung", "sm-"]):
        return "One UI"
    elif "originos" in text or "funtouch" in text:
        return "Funtouch OS / OriginOS"
    elif "magic" in text or "emui" in text:
        return "MagicOS / EMUI"
    elif "myos" in text:
        return "MyOS"
    elif "hios" in text:
        return "HiOS"
    elif "xos" in text:
        return "XOS"
    elif "moto" in text or "hello" in text:
        return "My UX / Stock Android"
    elif "pixel" in text or "google" in text:
        return "Pixel UI / Stock Android"
    return "Stock Android / Other"

# ==================== FORCE JOIN CALLBACK HANDLER ====================

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def verify_join_callback(call):
    if check_user_joined(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Verification Successful!", show_alert=True)
        bot.edit_message_text(
            "Welcome to All Phone Root Checker Bot\n\n"
            "Please send a clear screenshot of your (About Phone) or (My Phone) settings page I will scan it and tell you if your device can be rooted or not\n\n\n"
            "ফোন রুট চেকার বটে আপনাকে স্বাগত\n\n"
            "দয়া করে আপনার সেটিংসের (About Phone) অথবা (My Phone) পেজের একটি পরিষ্কার স্ক্রিনশট পাঠান। আমি এটি স্ক্যান করে বলে দেব আপনার ডিভাইসটি রুট করা সম্ভব কি না।",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
    else:
        bot.answer_callback_query(call.id, "❌ আপনি এখনো গ্রুপে জয়েন করেননি!", show_alert=True)

# ==================== ADMIN PANEL & BUTTONS ====================

def get_stats_text():
    total_users, total_scans = get_stats_data()
    current_time = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    
    stats_msg = (
        "📊 **BOT REAL-TIME STATISTICS**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 **Total Active Users:** `{total_users}` User(s)\n"
        f"📩 **Total Screenshots Checked:** `{total_scans}` Times\n"
        f"🟢 **Bot Status:** `Online & Running ⚡`\n"
        f"⏰ **Last Checked:** `{current_time}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ *System status auto-updated from database.*"
    )
    return stats_msg

@bot.message_handler(commands=['panel'])
def admin_panel(message):
    if message.chat.id == ADMIN_CHAT_ID:
        markup = InlineKeyboardMarkup()
        btn_stats = InlineKeyboardButton("📊 Check Stats", callback_data="admin_stats")
        btn_broadcast = InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast")
        markup.add(btn_stats)
        markup.add(btn_broadcast)
        
        panel_msg = (
            "⚙️ **ADMIN CONTROL PANEL**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Welcome back, Boss! Choose an option below to manage your bot:\n\n"
            "• **/stats** — View user & check count statistics\n"
            "• **/broadcast [text]** — Send message to all users\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        bot.reply_to(message, panel_msg, parse_mode="Markdown", reply_markup=markup)
    else:
        bot.reply_to(message, "❌ You are not authorized to use this command.")

@bot.message_handler(commands=['stats'])
def bot_stats(message):
    if message.chat.id == ADMIN_CHAT_ID:
        bot.reply_to(message, get_stats_text(), parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ You are not authorized to use this command.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def handle_admin_buttons(call):
    if call.message.chat.id == ADMIN_CHAT_ID:
        if call.data == "admin_stats":
            bot.answer_callback_query(call.id, "📊 Loading Statistics...")
            bot.send_message(call.message.chat.id, get_stats_text(), parse_mode="Markdown")
            
        elif call.data == "admin_broadcast":
            bot.answer_callback_query(call.id, "📢 Broadcast Helper")
            instruction = (
                "📢 **How to Broadcast a Message:**\n\n"
                "Type `/broadcast` followed by your message.\n\n"
                "**Example:**\n"
                "`/broadcast Hello everyone! Our bot has been updated with new features.`"
            )
            bot.send_message(call.message.chat.id, instruction, parse_mode="Markdown")
    else:
        bot.answer_callback_query(call.id, "❌ Unauthorized Action", show_alert=True)

@bot.message_handler(commands=['broadcast'])
def broadcast_message(message):
    if message.chat.id == ADMIN_CHAT_ID:
        msg_text = message.text.replace('/broadcast', '').strip()
        
        if not msg_text:
            bot.reply_to(
                message, 
                "⚠️ **Please enter a message to broadcast.**\n\n**Example:**\n`/broadcast Hi, we have a new update!`", 
                parse_mode="Markdown"
            )
            return
            
        users = get_all_users()
        success = 0
        failed = 0
        
        status_msg = bot.reply_to(message, "📢 **Broadcasting message to all users...**", parse_mode="Markdown")
        
        for user_id in users:
            try:
                bot.send_message(user_id, msg_text)
                success += 1
                time.sleep(0.05)
            except Exception:
                failed += 1
                
        bot.edit_message_text(
            f"✅ **Broadcast Completed Successfully!**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 **Delivered:** `{success}`\n"
            f"❌ **Failed/Blocked:** `{failed}`\n"
            f"👥 **Total Targeted:** `{len(users)}`",
            chat_id=message.chat.id,
            message_id=status_msg.message_id,
            parse_mode="Markdown"
        )
    else:
        bot.reply_to(message, "❌ You are not authorized to use this command.")

# ==================== USER HANDLERS ====================

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    add_user(message.chat.id)
    
    # Check if user joined
    if not check_user_joined(message.chat.id):
        join_msg = (
            "⚠️ **বট ব্যবহার করার পূর্বে আপনাকে আমাদের অফিশিয়াল গ্রুপে জয়েন হতে হবে!**\n\n"
            "নিচের লিংকে ক্লিক করে গ্রুপে জয়েন করুন এবং **Verify / Check Again** বাটনে চাপ দিন।"
        )
        bot.reply_to(message, join_msg, parse_mode="Markdown", reply_markup=get_join_keyboard())
        return

    welcome_msg = (
        "Welcome to All Phone Root Checker Bot\n\n"
        "Please send a clear screenshot of your (About Phone) or (My Phone) settings page "
        "I will scan it and tell you if your device can be rooted or not\n\n\n"
        "ফোন রুট চেকার বটে আপনাকে স্বাগত\n\n"
        "দয়া করে আপনার সেটিংসের (About Phone) অথবা (My Phone) পেজের একটি পরিষ্কার স্ক্রিনশট পাঠান। "
        "আমি এটি স্ক্যান করে বলে দেব আপনার ডিভাইসটি রুট করা সম্ভব কি না।"
    )
    bot.reply_to(message, welcome_msg)

@bot.message_handler(commands=['contact'])
def send_contact_info(message):
    add_user(message.chat.id)
    
    if not check_user_joined(message.chat.id):
        join_msg = "⚠️ **বট ব্যবহার করার পূর্বে আপনাকে আমাদের অফিশিয়াল গ্রুপে জয়েন হতে হবে!**"
        bot.reply_to(message, join_msg, parse_mode="Markdown", reply_markup=get_join_keyboard())
        return

    contact_markup = InlineKeyboardMarkup()
    contact_markup.add(
        InlineKeyboardButton(" WhatsApp ", url="https://wa.me/8801319100359"),
        InlineKeyboardButton(" Telegram ", url="https://t.me/osmanbhaiofficial")
    )
    contact_msg = "💼 **রুট করার জন্য এখনই আমাদের সাথে যোগাযোগ করুন:**"
    bot.reply_to(message, contact_msg, parse_mode="Markdown", reply_markup=contact_markup)

@bot.message_handler(content_types=['photo'])
def handle_about_phone_screenshot(message):
    add_user(message.chat.id)
    
    # Check if user joined before processing photo
    if not check_user_joined(message.chat.id):
        join_msg = "⚠️ **ছবি স্ক্যান করার পূর্বে আপনাকে আমাদের অফিশিয়াল গ্রুপে জয়েন করতে হবে!**"
        bot.reply_to(message, join_msg, parse_mode="Markdown", reply_markup=get_join_keyboard())
        return

    increment_scan_count()
    
    image_path = 'temp_screenshot.jpg'
    try:
        initial_msg = (
            "⚡ **SYSTEM SCAN IN PROGRESS...**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚙️ **Checking Root Support...**\n\n"
            "`[░░░░░░░░░░░░] 0%`\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🚀 *Please wait while AI analyzes your phone...*"
        )
        status_message = bot.reply_to(message, initial_msg, parse_mode="Markdown")
        
        def run_percent_loading():
            for i in range(1, 101):
                if i % 4 == 0 or i == 1 or i == 100:
                    bar_length = 12
                    filled = int((i / 100) * bar_length)
                    bar = "▓" * filled + "░" * (bar_length - filled)
                    
                    loading_text = (
                        f"⚡ **SYSTEM SCAN IN PROGRESS...**\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"⚙️ **Checking Root Support...**\n\n"
                        f"`[{bar}] {i}%`\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"🚀 *Please wait while AI analyzes your phone...*"
                    )
                    try:
                        bot.edit_message_text(
                            loading_text, 
                            chat_id=message.chat.id, 
                            message_id=status_message.message_id, 
                            parse_mode="Markdown"
                        )
                    except Exception:
                        pass
                time.sleep(0.035)

        loading_thread = Thread(target=run_percent_loading)
        loading_thread.start()
        
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        with open(image_path, 'wb') as new_file:
            new_file.write(downloaded_file)
            
        full_text = pytesseract.image_to_string(Image.open(image_path)).lower()
        
        device_name = clean_device_name(full_text)
        android_version = extract_android_version(full_text)
        cpu_detected = detect_cpu(full_text)
        os_ui_detected = detect_os_ui(full_text)
        
        current_time = datetime.now().strftime("%m/%d/%Y %I:%M:%S %p")
        
        loading_thread.join()
        time.sleep(0.3)

        contact_markup = InlineKeyboardMarkup()
        contact_markup.add(
            InlineKeyboardButton(" WhatsApp ", url="https://wa.me/8801319100359"),
            InlineKeyboardButton(" Telegram ", url="https://t.me/osmanbhaiofficial")
        )
        
        if device_name == "Not Detected":
            error_response = (
                "❌ **ছবিটি ক্লিয়ার না বা ভুল ছবি দিয়েছেন** ⚠️\n\n"
                "আপনার দেওয়া স্ক্রিনশটে কোনো সঠিক Device name বা Model পাওয়া যায়নি। দয়া করে অরিজিনাল সেটিংস পেজের ক্লিয়ার স্ক্রিনশট দিন।\n\n"
                f"📅 **Date & Time:** {current_time}\n\n"
                "রুট ফিডবেক জানতে এখনি আমাদের গ্রুপে জয়েন থাকুন\n"
                "https://t.me/osmanbhaiofficials\n\n"
                "⚠️ **একটু ভালো করে সিওর করুন, এরপরও কোনো সমস্যা থাকলে Admin এর সাথে যোগাযোগ করুন।**"
            )
            bot.edit_message_text(
                error_response, 
                chat_id=message.chat.id, 
                message_id=status_message.message_id, 
                disable_web_page_preview=True, 
                parse_mode="Markdown",
                reply_markup=contact_markup
            )
            
            try:
                error_user_info = (
                    "🚨 **Image Detection Failed Alert!**\n\n"
                    f"👤 **User:** {message.from_user.first_name} {message.from_user.last_name or ''}\n"
                    f"🆔 **User ID:** `{message.from_user.id}`\n"
                    f"🔗 **Username:** @{message.from_user.username or 'None'}\n"
                    f"📱 **Device:** Not Detected ❌\n"
                    f"📅 **Time:** {current_time}\n"
                    "⚠️ **ইউজার একটি ভুল অথবা ঘোলা ছবি সাবমিট করেছে।**"
                )
                with open(image_path, 'rb') as photo_to_send:
                    bot.send_photo(ADMIN_CHAT_ID, photo_to_send, caption=error_user_info, parse_mode="Markdown")
            except Exception as admin_err:
                print(f"[Admin Error Send Failed]: {admin_err}")
                
            return

        is_supported = False
        
        if "helio" in full_text or "helio" in device_name.lower():
            is_supported = True
        elif "oneplus" in full_text or "oxygenos" in full_text:
            is_supported = True
        elif "pixel" in full_text or "google" in full_text:
            is_supported = True
        elif "realme" in full_text or "realme ui" in os_ui_detected.lower() or "rmx" in full_text:
            if cpu_detected == "MediaTek":
                is_supported = True
            elif any(m in full_text or m in device_name.lower() for m in REALME_UNISOC_SUPPORTED):
                is_supported = True
            else:
                is_supported = False
        elif any(brand in full_text for brand in SUPPORTED_BRANDS):
            is_supported = True

        if any(x in full_text for x in ["oppo", "realme"]) and any(x in full_text for x in ["v5", "v6"]):
            is_supported = False
            
        if any(b in full_text for b in ["vivo", "iqoo", "huawei", "honor"]) or any(x in os_ui_detected.lower() for x in ["funtouch", "originos", "magic", "emui"]):
            is_supported = False
            
        if "samsung" in full_text and "one ui 8" in full_text:
            is_supported = False

        if is_supported:
            response_text = (
                "🎉 **Congratulations! Root possible** ✅\n\n"
                f"📱 **Device:** {device_name}\n"
                f"🤖 **Android Version:** {android_version}\n"
                f"⚙️ **Processor:** {cpu_detected}\n"
                f"💿 **System UI:** {os_ui_detected}\n"
                f"📅 **Date & Time:** {current_time}\n\n"
                "রুট ফিডবেক জানতে এখনি আমাদের গ্রুপে জয়েন থাকুন\n"
                "https://t.me/osmanbhaiofficials\n\n"
                "💼 **রুট করার জন্য এখনই আমাদের সাথে যোগাযোগ করুন:**"
            )
        else:
            response_text = (
                "❌ **Root Not Supported / Very Hard** ⚠️\n\n"
                f"📱 **Device:** {device_name}\n"
                f"🤖 **Android Version:** {android_version}\n"
                f"⚙️ **Processor:** {cpu_detected}\n"
                f"💿 **System UI:** {os_ui_detected}\n"
                "📝 **Note:** Rooting is not possible for this brand's devices.\n"
                f"📅 **Date & Time:** {current_time}\n\n"
                "রুট ফিডবেক জানতে এখনি আমাদের গ্রুপে জয়েন থাকুন\n"
                "https://t.me/osmanbhaiofficials\n\n"
                "❌ **আপনার ফোন রুট হবে না বা এই মুহূর্তে সাপোর্ট নেই।**\n"
                "📝 **নোট:** এই ব্র্যান্ডের ফোন গুলো রুট করা সম্ভব নয়।\n\n"
                "⚠️ **একটু ভালো করে সিওর করুন, এরপরও কোনো সমস্যা থাকলে Admin এর সাথে যোগাযোগ করুন।**"
            )
            
        bot.edit_message_text(
            response_text, 
            chat_id=message.chat.id, 
            message_id=status_message.message_id, 
            disable_web_page_preview=True, 
            parse_mode="Markdown",
            reply_markup=contact_markup
        )

        try:
            user_info = (
                "🔔 **New Screenshot Received!**\n\n"
                f"👤 **User:** {message.from_user.first_name} {message.from_user.last_name or ''}\n"
                f"🆔 **User ID:** `{message.from_user.id}`\n"
                f"🔗 **Username:** @{message.from_user.username or 'None'}\n"
                f"📱 **Device:** {device_name}\n"
                f"⚙️ **Processor/OS:** {cpu_detected} / {os_ui_detected}\n"
                f"🤖 **Android:** {android_version}\n"
                f"🚦 **Root Support:** {'✅ Possible' if is_supported else '❌ Impossible'}"
            )
            
            with open(image_path, 'rb') as photo_to_send:
                bot.send_photo(ADMIN_CHAT_ID, photo_to_send, caption=user_info, parse_mode="Markdown")
        except Exception as admin_err:
            print(f"[Admin Send Error] Failed to notify admin: {admin_err}")
        
    except Exception as e:
        if "timeout" in str(e).lower() or "connectionpool" in str(e).lower():
            bot.reply_to(message, "⚠️ Network connection is unstable. Please try sending the screenshot again after a moment.\n\n⚠️ নেটওয়ার্ক সংযোগ দুর্বল। দয়া করে একটু পরে আবার স্ক্রিনশটটি পাঠান।")
        else:
            bot.reply_to(message, f"❌ An error occurred / সমস্যা হয়েছে: {str(e)}")
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)

if __name__ == "__main__":
    set_bot_commands()

    server_thread = Thread(target=run_web_server)
    server_thread.daemon = True
    server_thread.start()

    print("Flask Web Server & Multi-Brand Scanner Bot is running...")

    bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
