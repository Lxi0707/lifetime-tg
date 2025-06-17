import os
import random
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.error import TelegramError
from datetime import datetime

# 配置
OODATA_URL = "https://oodata.net/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def fetch_oodata():
    try:
        response = requests.get(OODATA_URL, headers=HEADERS)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching oodata: {e}")
        return None

def parse_freebies(html):
    soup = BeautifulSoup(html, 'html.parser')
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 查找今日发布的信息
    today_section = soup.find('div', {'class': 'post-list'})
    if not today_section:
        return None
    
    items = today_section.find_all('article', {'class': 'post'})
    if not items:
        return None
    
    freebies = {"本体限免": [], "内购限免": []}
    
    for item in items:
        # 检查日期是否为今天
        date_tag = item.find('time', {'class': 'post-date'})
        if not date_tag or today not in date_tag.get('datetime', ''):
            continue
        
        title_tag = item.find('h2', {'class': 'post-title'})
        title = title_tag.get_text(strip=True) if title_tag else "无标题"
        
        # 获取详情链接
        link = title_tag.find('a')['href'] if title_tag and title_tag.find('a') else None
        
        # 获取类型信息
        type_tag = item.find('span', {'class': 'post-category'})
        item_type = type_tag.get_text(strip=True) if type_tag else "未知类型"
        
        # 获取价格信息
        price_tag = item.find('span', {'class': 'post-price'})
        price_info = price_tag.get_text(strip=True) if price_tag else ""
        
        # 判断是本体限免还是内购限免
        if "本体" in item_type or "完全" in item_type or "限免" in item_type:
            category = "本体限免"
        elif "内购" in item_type or "IAP" in item_type:
            category = "内购限免"
        else:
            continue
        
        freebies[category].append({
            "title": title,
            "type": item_type,
            "price": price_info,
            "link": link
        })
    
    return freebies

def format_message(freebies):
    if not freebies or (not freebies["本体限免"] and not freebies["内购限免"]):
        return "今日没有发现限免信息~"
    
    message = "🎮 今日限免信息 🎮\n\n"
    today = datetime.now().strftime("%Y年%m月%d日")
    message += f"📅 {today}\n\n"
    
    # 打乱每个类别中的顺序
    for category in freebies:
        random.shuffle(freebies[category])
    
    # 添加本体限免信息
    if freebies["本体限免"]:
        message += "🔥 <b>本体限免</b>\n"
        for item in freebies["本体限免"]:
            message += f"- {item['title']} ({item['type']})"
            if item['price']:
                message += f" - {item['price']}"
            if item['link']:
                message += f"\n  🔗 {item['link']}"
            message += "\n"
        message += "\n"
    
    # 添加内购限免信息
    if freebies["内购限免"]:
        message += "💰 <b>内购限免</b>\n"
        for item in freebies["内购限免"]:
            message += f"- {item['title']} ({item['type']})"
            if item['price']:
                message += f" - {item['price']}"
            if item['link']:
                message += f"\n  🔗 {item['link']}"
            message += "\n"
    
    message += "\n数据来源: oodata.net"
    return message

def send_to_telegram(message):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    channel_id = os.getenv("TELEGRAM_CHANNEL_ID")
    
    if not bot_token or not channel_id:
        print("Telegram bot token or channel ID not set")
        return False
    
    try:
        bot = Bot(token=bot_token)
        bot.send_message(
            chat_id=channel_id,
            text=message,
            parse_mode='HTML',
            disable_web_page_preview=True
        )
        return True
    except TelegramError as e:
        print(f"Error sending to Telegram: {e}")
        return False

def main():
    print("Starting oodata freebies scraper...")
    
    html = fetch_oodata()
    if not html:
        print("Failed to fetch oodata")
        return
    
    freebies = parse_freebies(html)
    if not freebies:
        print("No freebies found for today")
        send_to_telegram("今日没有发现限免信息~")
        return
    
    message = format_message(freebies)
    print("Formatted message:\n", message)
    
    if send_to_telegram(message):
        print("Message sent to Telegram successfully")
    else:
        print("Failed to send message to Telegram")

if __name__ == "__main__":
    main()
