import requests
import json
import os
import time

# CONFIG
BOT_TOKEN = "8337194407:AAGdttJEaPGSUYzeLo7_ZZz0_At3pyrHyxY"
OWNER_ID  = 5895386985
API_URL   = "https://tg2num-owner-api.vercel.app?userid={}"

CREDITS_FILE = "credits.json"
CODES_FILE   = "codes.json"

# Globals
last_update_id = 0
credits = {}
codes   = {}

def load_credits():
    global credits
    if os.path.exists(CREDITS_FILE):
        with open(CREDITS_FILE, 'r') as f:
            credits = json.load(f)

def save_credits():
    with open(CREDITS_FILE, 'w') as f:
        json.dump(credits, f)

def load_codes():
    global codes
    if os.path.exists(CODES_FILE):
        with open(CODES_FILE, 'r') as f:
            codes = json.load(f)

def save_codes():
    with open(CODES_FILE, 'w') as f:
        json.dump(codes, f)

def get_credits(uid):
    return credits.get(str(uid), 0)

def add_credits(uid, amount):
    uid = str(uid)
    credits[uid] = get_credits(uid) + amount
    save_credits()

def deduct_credits(uid, amount=1):
    uid = str(uid)
    if get_credits(uid) >= amount:
        credits[uid] -= amount
        save_credits()
        return True
    return False

# Fast send (no retry – VPS slow hone pe wait mat karao)
def send(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text}
    try:
        requests.post(url, json=payload, timeout=8)
    except:
        pass

def get_updates(offset=None):
    params = {'timeout': 8}  # Fast polling
    if offset is not None:
        params['offset'] = offset
    try:
        resp = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates", params=params, timeout=12)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None

# Commands – simple & fast
def cmd_start(chat_id, first_name, user_id):
    text = (
        f"✨ Hey {first_name}! ✨\n\n"
        f"Welcome to Number Finder Bot 🔥\n\n"
        f"Commands:\n"
        f"  /getnum 123456789     → Find number (1 credit) 📱\n"
        f"  /getid @username      → Get user ID 🆔\n"
        f"  /credits              → Check balance 💰\n"
        f"  /redeem CODE          → Redeem code 🎟️\n\n"
        f"Owner only:\n"
        f"  /gen 10 5            → Generate codes 👑\n\n"
        f"By @AIZEN_77 ❤️"
    )
    send(chat_id, text)

def cmd_credits(chat_id, user_id):
    bal = get_credits(user_id)
    text = f"💰 Balance: {bal} credits"
    if bal == 0:
        text += "\nRedeem code!"
    send(chat_id, text)

def cmd_getnum(chat_id, user_id, args):
    if len(args) != 1 or not args[0].isdigit():
        send(chat_id, "Usage: /getnum 123456789")
        return

    target = args[0]

    if get_credits(user_id) < 1:
        send(chat_id, "❌ No credits! Need 1 💸")
        return

    deduct_credits(user_id)

    try:
        r = requests.get(API_URL.format(target), timeout=15)
        if r.status_code != 200:
            add_credits(user_id, 1)
            send(chat_id, "❌ API error - refunded 🔥")
            return

        data = r.json()

        if data.get("status") == "success" and data.get("data", {}).get("found"):
            d = data["data"]
            full = f"{d.get('country_code', '').replace('+', '')}{d.get('number', '')}" or "N/A"
            text = (
                f"🔍 Result\n\n"
                f"🆔 ID: {target}\n"
                f"💎 Username: {d.get('username', 'N/A')}\n"
                f"📱 Number: {full}\n"
                f"🌍 Country: {d.get('country', 'Unknown')}\n"
                f"✅ Found"
            )
        else:
            add_credits(user_id, 1)
            text = f"🔍 Result\n\n🆔 ID: {target}\n❌ Not found\nRefunded 🔥"

        send(chat_id, text)

    except:
        add_credits(user_id, 1)
        send(chat_id, "⚠️ Error - refunded 🔥")

def cmd_getid(chat_id, args):
    if len(args) != 1:
        send(chat_id, "Usage: /getid @username")
        return

    username = args[0].replace('@', '').strip().lower()
    send(chat_id, f"🔍 Checking @{username}...")

    try:
        resp = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?limit=100", timeout=10).json()
        if resp.get('ok'):
            for update in resp.get('result', []):
                msg = update.get('message', {})
                if msg.get('from', {}).get('username', '').lower() == username:
                    uid = msg['from']['id']
                    send(chat_id, f"✅ Found!\n@{username} ID: `{uid}`")
                    return
        send(chat_id, f"❌ @{username} not found\nAsk user to message bot first")
    except:
        send(chat_id, "Error, try later")

def cmd_redeem(chat_id, user_id, args):
    if len(args) != 1:
        send(chat_id, "Usage: /redeem CODE")
        return

    code = args[0].strip().upper()
    value = codes.get(code)

    if value is None:
        send(chat_id, "❌ Invalid code")
        return

    del codes[code]
    save_codes()
    add_credits(user_id, value)
    send(chat_id, f"🎉 Redeemed!\n+{value} credits\nBalance: {get_credits(user_id)} 💰")

def cmd_gen(chat_id, user_id, args):
    if user_id != OWNER_ID:
        return
    if len(args) < 1:
        send(chat_id, "Usage: /gen 10 5")
        return
    count = int(args[0])
    val = int(args[1]) if len(args) > 1 else 1
    text = "Generated:\n"
    for i in range(count):
        code = f"NIT-{int(time.time()*1000 + i):08d}"[-10:].upper()
        codes[code] = val
        text += f"{code} → {val}\n"
    save_codes()
    send(chat_id, text + f"\nTotal: {count}")

def process_update(update):
    global last_update_id

    if 'update_id' in update:
        last_update_id = max(last_update_id, update['update_id'] + 1)

    if 'message' not in update or 'text' not in update['message']:
        return

    msg = update['message']
    chat_id = msg['chat']['id']
    user_id = msg['from']['id']
    fname = msg['from'].get('first_name', 'User')
    text = msg['text'].strip()

    if not text.startswith('/'):
        return

    parts = text.split(maxsplit=1)
    cmd_part = parts[0].lower()
    cmd = cmd_part.split('@')[0].lstrip('/').strip()

    args = parts[1].split() if len(parts) > 1 else []

    print(f"[CMD] /{cmd} from {user_id} (args: {args})")

    if cmd == 'start':
        cmd_start(chat_id, fname, user_id)
    elif cmd == 'credits':
        cmd_credits(chat_id, user_id)
    elif cmd == 'getnum':
        cmd_getnum(chat_id, user_id, args)
    elif cmd == 'getid':
        cmd_getid(chat_id, args)
    elif cmd == 'redeem':
        cmd_redeem(chat_id, user_id, args)
    elif cmd == 'gen':
        cmd_gen(chat_id, user_id, args)

def main():
    load_credits()
    load_codes()
    print("🔥Bot running.......baby")

    while True:
        try:
            updates = get_updates(last_update_id)
            if updates and updates.get('ok'):
                for u in updates.get('result', []):
                    process_update(u)
            time.sleep(0.2)
        except:
            time.sleep(2)

if __name__ == '__main__':
    main()
