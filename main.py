import telebot
import feedparser
import time
import urllib.parse
import re
from googletrans import Translator
from telebot import types

# SOZLAMALAR
TOKEN = '8358476165:AAFsfhih8yADOpXaJa_JCvndQBDUUQZWmds' #
CHANNEL_ID = '@karnayuzb'

SOURCES = {
    'BBC World': 'http://feeds.bbci.co.uk/news/world/rss.xml',
    'Al Jazeera': 'https://www.aljazeera.com/xml/rss/all.xml',
    'Kun.uz': 'https://kun.uz/news/rss',
    'Daryo.uz': 'https://daryo.uz/feed/',
    'Terabayt.uz': 'https://www.terabayt.uz/feed',
    'CNN News': 'http://rss.cnn.com/rss/edition_world.rss',
    'Reuters': 'https://www.reutersagency.com/feed/?best-topics=world-news&post_type=best',
    'Championat.asia': 'https://championat.asia/uz/news/rss'
}

bot = telebot.TeleBot(TOKEN)
translator = Translator()
sent_news = set() #

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_html)

def get_ai_image(prompt):
    encoded_prompt = urllib.parse.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=768&nologo=true"

def get_image_url(entry): #
    if 'links' in entry:
        for link in entry.links:
            if 'image' in link.get('type', '') or 'media' in link.get('rel', ''):
                return link.get('href')
    if 'media_content' in entry:
        return entry.media_content[0]['url']
    return None

def process_news():
    for name, url in SOURCES.items():
        feed = feedparser.parse(url)
        for entry in feed.entries[:3]:
            if entry.link in sent_news:
                continue
            
            title = entry.title
            description = entry.get('description', '')
            description = clean_html(description)[:300] + "..."
            
            img_url = get_image_url(entry)
            is_uzbek = name in ['Kun.uz', 'Daryo.uz', 'Terabayt.uz', 'Championat.asia']

            if not is_uzbek:
                try:
                    title_uz = translator.translate(title, dest='uz').text
                    desc_uz = translator.translate(description, dest='uz').text
                except:
                    title_uz, desc_uz = title, description
            else:
                title_uz, desc_uz = title, description

            if not img_url:
                img_url = get_ai_image(title_uz)

            caption = (
                f"📢 **{title_uz}**\n\n"
                f"📝 {desc_uz}\n\n"
