#!/usr/bin/env python3
"""
Oodata限免信息抓取与Telegram自动发布脚本
功能：
1. 抓取oodata.net今日限免信息
2. 分类整理为本体限免和内购限免
3. 打乱每个类别中的顺序
4. 有信息时发布到Telegram频道
5. 无信息时发送通知到个人账号
"""

import os
import random
import asyncio
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.error import TelegramError
from datetime import datetime, timedelta

# 配置常量
BASE_URL = "https://oodata.net/"
DATE_FORMAT = "%Y%m%d"
REQUEST_TIMEOUT = 10
MAX_MESSAGE_LENGTH = 4096

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9"
}

class OodataScraper:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.channel_id = os.getenv("TELEGRAM_CHANNEL_ID")
        self.personal_chat_id = os.getenv("TELEGRAM_PERSONAL_CHAT_ID")
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def generate_today_url(self):
        """生成今日限免信息URL"""
        today = datetime.now().strftime(DATE_FORMAT)
        return f"{BASE_URL}app-store-limited-time-free-{today}/"

    async def send_telegram_message(self, text, chat_id=None, is_error=False):
        """发送消息到Telegram"""
        if not self.bot_token:
            print("❌ Telegram bot token未配置")
            return False

        target_chat = chat_id or self.channel_id
        if not target_chat:
            print("❌ 未指定接收聊天ID")
            return False

        try:
            bot = Bot(token=self.bot_token)
            if is_error:
                text = f"⚠️ {text}"
            
            if len(text) > MAX_MESSAGE_LENGTH:
                parts = [text[i:i+MAX_MESSAGE_LENGTH] for i in range(0, len(text), MAX_MESSAGE_LENGTH)]
                for part in parts:
                    await bot.send_message(
                        chat_id=target_chat,
                        text=part,
                        parse_mode='HTML',
                        disable_web_page_preview=True
                    )
                    await asyncio.sleep(1)
            else:
                await bot.send_message(
                    chat_id=target_chat,
                    text=text,
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
            return True
        except TelegramError as e:
            print(f"❌ Telegram发送错误: {e}")
            return False

    def fetch_page(self, url):
        """抓取网页内容"""
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            # 检查是否是404页面
            if "404" in response.text:
                return None
            return response.text
        except requests.RequestException as e:
            print(f"❌ 抓取页面失败: {str(e)}")
            return None

    def parse_freebies(self, html):
        """解析限免信息"""
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')
        freebies = {"本体限免": [], "内购限免": []}
        
        # 查找文章主体内容
        article_content = soup.find('div', class_='entry-content')
        if not article_content:
            print("⚠️ 未找到文章内容区域")
            return None
        
        # 查找所有列表项
        items = article_content.find_all('li')
        if not items:
            print("⚠️ 未找到限免信息列表")
            return None
        
        for item in items:
            text = item.get_text(strip=True)
            if not text:
                continue
            
            # 提取链接
            link_tag = item.find('a')
            link = link_tag['href'] if link_tag else None
            
            # 分类处理
            if "内购" in text or "IAP" in text:
                category = "内购限免"
            else:
                category = "本体限免"
            
            freebies[category].append({
                "title": text,
                "link": link
            })
        
        return freebies

    def format_message(self, freebies):
        """格式化消息内容"""
        if not freebies or (not freebies["本体限免"] and not freebies["内购限免"]):
            return None
        
        message = "🎮 <b>今日App Store限免信息</b> 🎮\n\n"
        today = datetime.now().strftime("%Y年%m月%d日")
        message += f"📅 {today}\n\n"
        
        # 打乱顺序增加随机性
        for category in freebies:
            random.shuffle(freebies[category])
        
        # 添加本体限免信息
        if freebies["本体限免"]:
            message += "🔥 <b>本体限免</b>\n"
            for item in freebies["本体限免"]:
                message += f"- {item['title']}"
                if item['link']:
                    message += f"\n  🔗 <a href='{item['link']}'>App Store链接</a>"
                message += "\n"
            message += "\n"
        
        # 添加内购限免信息
        if freebies["内购限免"]:
            message += "💰 <b>内购限免</b>\n"
            for item in freebies["内购限免"]:
                message += f"- {item['title']}"
                if item['link']:
                    message += f"\n  🔗 <a href='{item['link']}'>App Store链接</a>"
                message += "\n"
        
        message += "\n📌 数据来源: oodata.net"
        return message

    async def run(self):
        """主执行逻辑"""
        print("🚀 启动oodata限免信息抓取...")
        
        if not all([self.bot_token, self.channel_id, self.personal_chat_id]):
            print("❌ 缺少必要的环境变量配置")
            return
        
        # 生成今日URL并抓取
        today_url = self.generate_today_url()
        print(f"🔍 尝试抓取: {today_url}")
        html = self.fetch_page(today_url)
        
        # 如果今日页面不存在，尝试抓取昨天
        if html is None:
            yesterday = (datetime.now() - timedelta(days=1)).strftime(DATE_FORMAT)
            fallback_url = f"{BASE_URL}app-store-limited-time-free-{yesterday}/"
            print(f"⚠️ 今日页面不存在，尝试抓取昨天: {fallback_url}")
            html = self.fetch_page(fallback_url)
            if html is None:
                await self.send_telegram_message("无法找到最近限免信息页面", self.personal_chat_id, is_error=True)
                return
        
        # 解析数据
        freebies = self.parse_freebies(html)
        message = self.format_message(freebies)
        
        # 处理结果
        if message:
            print("✅ 发现限免信息，准备发送到频道")
            await self.send_telegram_message(message)
        else:
            print("ℹ️ 今日无限免信息")
            await self.send_telegram_message("今日没有发现限免信息", self.personal_chat_id)

async def main():
    scraper = OodataScraper()
    await scraper.run()

if __name__ == "__main__":
    asyncio.run(main())
