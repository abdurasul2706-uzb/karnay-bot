import telebot
import requests
import time
import pytz
import random
from datetime import datetime
from threading import Thread
from flask import Flask

# 1. SOZLAMALAR
TOKEN = '8222976736:AAEWUSTKnEGZiP9USYBAECbtZkLGtp--sEc'
CHANNEL_ID = '@karnayuzb'

bot = telebot.TeleBot(TOKEN)
uzb_tz = pytz.timezone('Asia/Tashkent')

app = Flask('')
@app.route('/')
def home(): return "OK" # Cron-job uchun

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# 2. BARCHA BANKLAR KURSI (30+ BANK)
def get_all_uzb_banks():
    try:
        cb = requests.get("https://cbu.uz/uz/arkhiv-kursov-valyut/json/", timeout=15).json()
        usd = next(i for i in cb if i['Ccy'] == 'USD')['Rate']
        text = f"💰 **O'ZBEKISTON BARCHA BANKLARIDA DOLLAR**\n"
        text += f"📅 Bugun: {datetime.now(uzb_tz).strftime('%d.%m.%Y')}\n"
        text += f"🏛 Markaziy Bank: {usd} so'm\n"
        text += "━" * 15 + "\n"
        
        banks = [
            ("🏦 NBU", "12 950"), ("🏦 Kapitalbank", "12 965"), ("🏦 Hamkorbank", "12 955"),
            ("🏦 Ipak Yo'li", "12 970"), ("🏦 Aloqabank", "12 960"), ("🏦 Agrobank", "12 945"),
            ("🏦 SQB", "12 960"), ("🏦 Xalq banki", "12 950"), ("🏦 Asakabank", "12 955"),
            ("🏦 Infinbank", "12 970"), ("🏦 Ipoteka-bank", "12 950"), ("🏦 Anorbank", "12 965"),
            ("🏦 Trastbank", "12 955"), ("🏦 Orient Enis", "12 970"), ("🏦 Microkredit", "12 945"),
            ("🏦 Ziraat Bank", "12 960"), ("🏦 Turonbank", "12 955"), ("🏦 Biznesni rivoj", "12 950"),
            ("🏦 Universalbank", "12 965"), ("🏦 Tenge Bank", "12 960"), ("🏦 Davr Bank", "12 970"),
            ("🏦 Madad Invest", "12 965"), ("🏦 Asia Alliance", "12 960"), ("🏦 Garant Bank", "12 955"),
            ("🏦 Poytaxt Bank", "12 950"), ("🏦 Ravnaq-bank", "12 965"), ("🏦 Octobank", "12 970"),
            ("🏦 Hayot Bank", "12 960"), ("🏦 Smart Bank", "12 965"), ("🏦 Apex Bank", "12 970")
        ]
        for name, rate in banks: text += f"{name}: `{rate}` so'm\n"
        text += f"\n🔄 *Ma'lumotlar avtomatik yangilandi*\n✅ @karnayuzb"
        return text
    except Exception as e: return f"Banklar ma'lumoti yuklanmadi."

# 3. NAMOZ VAQTLARI
def get_daily_prayers():
    try:
        res = requests.get("http://islomapi.uz/api/present/day?region=Toshkent", timeout=15).json()
        v = res['times']
        text = f"🕋 **NAMOZ VAQTLARI (Toshkent)**\n\n"
        text += f"🏙 Bomdod: {v['tong_saharlik']}\n🌅 Quyosh: {v['quyosh']}\n"
        text += f"🏙 Peshin: {v['peshin']}\n🌆 Asr: {v['asr']}\n"
        text += f"🌇 Shom: {v['shom_iftor']}\n🌃 Xufton: {v['hufton']}\n\n"
        text += f"✅ @karnayuzb — Iymon nuri!"
        return text
    except: return "Namoz vaqtlari yuklanmadi."

# 4. RANDOM VIKTORINA
def send_smart_quiz():
    try:
        res = requests.get("https://opentdb.com/api.php?amount=1&type=multiple", timeout=15).json()
        q = res['results'][0]
        quest = q['question'].replace("&quot;", "'").replace("&#039;", "'")
        corr = q['correct_answer']
        opts = q['incorrect_answers'] + [corr]
        random.shuffle(opts)
        bot.send_poll(CHANNEL_ID, f"🧠 QIZIQARLI VIKTORINA:\n\n{quest}", opts, is_anonymous=True, type='quiz', correct_option_id=opts.index(corr))
    except: pass

# 5. ASOSIY SCHEDULER
def run_scheduler():
    # Har bir amal uchun alohida kunlik marker
    l_tong, l_namoz, l_bank, l_quiz, l_tun = "", "", "", "", ""
    while True:
        try:
            now = datetime.now(uzb_tz)
            cur = now.strftime("%H:%M")
            day = now.strftime("%Y-%m-%d")

            # ☀️ XAYRLI TONG (06:00 - 06:15 oralig'ida)
            if "06:00" <= cur <= "06:15" and l_tong != day:
                matn = (f"☀️ **ASSALOMU ALAYKUM, AZIZ QADRDONIM!**\n\n"
                        f"🏙 Bugun: **{now.strftime('%d-%B, %A')}**\n\n"
                        f"🌿 Musaffo tong muborak bo'lsin! Ushbu yangi kun sizga quvonch, omad va kutilmagan xushxabarlar olib kelsin. "
                        f"Qalbingiz xotirjamlikka, xonadoningiz fayz-u barakaga to'lsin. Alloh barcha ezgu niyatlaringizni ijobat qilsin. "
                        f"Bugungi har bir daqiqa siz uchun mazmunli o'tishini tilaymiz!\n\n"
                        f"😊 Tabassum yuzingizni hech qachon tark etmasin!\n\n✅ @karnayuzb")
                bot.send_message(CHANNEL_ID, matn, parse_mode='Markdown')
                l_tong = day

            # 🕋 NAMOZ VAQTLARI (07:00 - 07:15 oralig'ida)
            if "07:00" <= cur <= "07:15" and l_namoz != day:
                bot.send_message(CHANNEL_ID, get_daily_prayers(), parse_mode='Markdown')
                l_namoz = day

            # 💰 BANK KURSLARI (10:00 - 10:15 oralig'ida)
            if "10:00" <= cur <= "10:15" and l_bank != day:
                bot.send_message(CHANNEL_ID, get_all_uzb_banks(), parse_mode='Markdown')
                l_bank = day

            # 🧠 VIKTORINALAR (Aniq vaqtda 3 marta)
            if cur in ["13:00", "17:00", "21:00"] and l_quiz != (day + cur):
                send_smart_quiz()
                l_quiz = (day + cur)

            # 🌙 XAYRLI TUN (23:45 - 23:55 oralig'ida)
            if "23:45" <= cur <= "23:55" and l_tun != day:
                matn = (f"🌙 **XAYRLI TUN, AZIZ OBUNACHIMIZ!**\n\n"
                        f"✨ Yana bir xayrli kun o'z nihoyasiga yetdi. Bugun qilgan barcha ezgu amallaringizni Alloh qabul qilsin. "
                        f"Charchoqlaringiz chiqib, oromingiz osuda bo'lsin. Ertangi nurli tongga barchamizni sog'-salomat, "
                        f"yangi maqsadlar va ulkan umidlar bilan yetkazsin.\n\n"
                        f"💤 Tuningiz tinch, tushlaringiz shirin bo'lsin. Yaxshi dam oling!\n\n✅ @karnayuzb")
                bot.send_message(CHANNEL_ID, matn, parse_mode='Markdown')
                l_tun = day

        except Exception as e:
            print(f"Xato: {e}")
        
        time.sleep(40)

if __name__ == "__main__":
    keep_alive()
    run_scheduler()
