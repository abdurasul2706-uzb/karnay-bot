import telebot
import feedparser
import time
import requests
import re
import random
from bs4 import BeautifulSoup
from googletrans import Translator
from flask import Flask
from threading import Thread

# 1. RENDER UCHUN SERVER
app = Flask('')
@app.route('/')
def home(): return "Bot is running!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# 2. SOZLAMALAR
TOKEN = '8358476165:AAFsfhih8yWO0pXaJa_JCvndQ8DUUQZWads'
CHANNEL_ID = '@karnayuzb'

# MANBALAR (Siz aytgan miqdor va yo'nalishlar bo'yicha saralangan va chalkashtirilgan)
SOURCES_LIST = [
    ('Kun.uz', 'https://kun.uz/news/rss'), # UZ 1
    ('The New York Times', 'https://rss.nytimes.com/services/xml/rss/nyt/World.xml'), # USA 1
    ('Daryo.uz', 'https://daryo.uz/feed/'), # UZ 2
    ('BBC News', 'http://feeds.bbci.co.uk/news/world/rss.xml'), # EURO 1
    ('Qalampir.uz', 'https://qalampir.uz/uz/rss'), # UZ 3
    ('Al Jazeera', 'https://www.aljazeera.com/xml/rss/all.xml'), # ARAB 1
    ('Gazeta.uz', 'https://www.gazeta.uz/uz/rss/'), # UZ 4
    ('Reuters', 'https://www.reutersagency.com/feed/?best-topics=world-news&post_type=best'), # USA 2
    ('Xabar.uz', 'https://xabar.uz/uz/rss'), # UZ 5
    ('The Guardian', 'https://www.theguardian.com/world/rss'), # EURO 2
    ('Championat.asia', 'https://championat.asia/uz/news/rss'), # SPORT 1
    ('Nikkei Asia', 'https://asia.nikkei.com/rss/feed/nar'), # ASIA 1
    ('Uza.uz', 'https://uza.uz/uz/rss.php'), # UZ 6
    ('The Washington Post', 'https://feeds.washingtonpost.com/rss/world'), # USA 3
    ('Terabayt.uz', 'https://www.terabayt.uz/feed'), # TECH 1
    ('South China Morning Post', 'https://www.scmp.com/rss/91/feed.xml'), # ASIA 2
    ('Podrobno.uz', 'https://podrobno.uz/rss/'), # UZ 7
    ('Euronews', 'https://www.euronews.com/rss?level=vertical&name=news'), # EURO 3
    ('Artnews.com', 'https://www.artnews.com/feed/'), # ART 1
    ('Sputnik O‘zbekiston', 'https://uz.sputniknews.ru/export/rss2/archive/index.xml'), # UZ 8
    ('CNA Asia', 'https://www.channelnewsasia.com/rssfeeds/8395981'), # ASIA 3
    ('UzNews.uz', 'https://uznews.uz/uz/rss'), # UZ 9
    ('Nuz.uz', 'https://nuz.uz/feed') # UZ 10
]

# Manbalarni chalkashtirish
random.shuffle(SOURCES_LIST)
SOURCES = dict(SOURCES_LIST)

bot = telebot.TeleBot(TOKEN)
translator = Translator()
SENT_NEWS_CACHE = set()

def deep_clean_text(text):
    """Texnik matnlarni va 'shovqin'larni butunlay tozalash"""
    if not text: return ""
    
    # 1. Tozalanishi shart bo'lgan qat'iy iboralar (Siz aytgan xunuk yozuvlar)
    trash_patterns = [
        r"muallifning xabarlari kundalik e-pochtangiz.*?qo‘shiladi",
        r"Siz soʻragan sahifaga kirishga ruxsatingiz yoʻq",
        r"veb-sayt himoyalangan",
        r"Xavfsizlik nuqtai nazaridan bu sahifani ko‘rsatib bo‘lmaydi",
        r"cookies-fayllardan foydalanamiz",
        r"Maxfiylik siyosati",
        r"Siz tashrif buyurayotgan veb-sayt",
        r"Davom etish orqali siz rozilik bildirasiz"
    ]
    
    cleaned = text
    for pattern in trash_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    
    # 2. Ortiqcha bo'shliqlar va qatorlarni yo'qotish (Zich holatga keltirish)
    cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned) # Faqat bitta bo'sh qator qoldirish
    cleaned = cleaned.strip()
    
    return cleaned

def get_optimized_content(url):
    """Saytdan rasm va toza matnni yaxlit holda olish"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(url, headers=headers, timeout=12)
        soup = BeautifulSoup(res.content, 'html.parser')
        
        # Keraksiz HTML qismlarni (header, footer, reklama) o'chirib yuborish
        for tag in soup(['script', 'style', 'header', 'footer', 'aside', 'nav', 'form']):
            tag.decompose()

        img = soup.find("meta", property="og:image")
        img_url = img['content'] if img else None
        
        # Maqola matni
        paras = soup.find_all('p')
        content_parts = []
        for p in paras:
            p_text = p.get_text().strip()
            # Agar paragrafda 40 dan kam harf bo'lsa yoki texnik so'z bo'lsa, olmaymiz
            if len(p_text) > 45 and not any(x in p_text.lower() for x in ['login', 'roʻyxat', 'email', 'subscribe']):
                content_parts.append(p_text)
            if len("\n\n".join(content_parts)) > 1500: break
            
        full_text = "\n\n".join(content_parts)
        return img_url, deep_clean_text(full_text)
    except:
        return None, ""

def process_news():
    # Har safar manbalarni chalkashtirib turish
    shuffled_items = list(SOURCES.items())
    random.shuffle(shuffled_items)
    
    for name, url in shuffled_items:
        try:
            print(f"Skaner: {name}")
            feed = feedparser.parse(url)
            
            if feed.entries:
                entry = feed.entries[0]
                if entry.link in SENT_NEWS_CACHE: continue
                
                img_url, full_text = get_optimized_content(entry.link)
                title = entry.title
                
                # Tarjima (Chet el manbalari uchun)
                if name not in ['Kun.uz', 'Daryo.uz', 'Gazeta.uz', 'Qalampir.uz', 'Xabar.uz', 'Terabayt.uz', 'UzNews.uz', 'Uza.uz', 'Championat.asia']:
                    try:
                        title = translator.translate(title, dest='uz').text
                        full_text = translator.translate(full_text[:1200], dest='uz').text
                    except: pass

                # Matnni Telegram limitiga moslash (oxirgi nuqtadan kesish)
                final_text = full_text
                if len(final_text) > 850:
                    final_text = final_text[:850].rsplit('.', 1)[0] + "."

                # POST FORMATI (Siz so'ragandek 📢 Karnay va yaxlitlik)
                caption = f"📢 **{name.upper()}**\n\n"
                caption += f"🎺 **{title}**\n\n"
                caption += f"{final_text}\n\n"
                caption += f"✅ @karnayuzb — Dunyo sizning qo'lingizda!\n"
                caption += f"#{name.replace(' ', '').replace('.', '')} #yangiliklar"

                try:
                    if img_url:
                        bot.send_photo(CHANNEL_ID, img_url, caption=caption, parse_mode='Markdown')
                    else:
                        bot.send_message(CHANNEL_ID, caption, parse_mode='Markdown')
                    
                    SENT_NEWS_CACHE.add(entry.link)
                    if len(SENT_NEWS_CACHE) > 300: SENT_NEWS_CACHE.clear()
                    time.sleep(10)
                except Exception as e:
                    print(f"Yuborishda xato: {e}")
        except: continue

if __name__ == "__main__":
    keep_alive()
    while True:
        process_news()
        print("Sikl tugadi. 5 daqiqa dam...")
        time.sleep(300)
