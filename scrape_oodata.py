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
from datetime import datetime

# 配置常量
OODATA_URL = "https://oodata.net/"
REQUEST_TIMEOUT = 10
MAX_MESSAGE_LENGTH = 4096  # Telegram消息长度限制

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
            
            # 添加错误标识前缀
            if is_error:
                text = f"⚠️ {text}"
            
            # 处理超长消息分片
            if len(text) > MAX_MESSAGE_LENGTH:
                parts = [text[i:i+MAX_MESSAGE_LENGTH] for i in range(0, len(text), MAX_MESSAGE_LENGTH)]
                for part in parts:
                    await bot.send_message(
                        chat_id=target_chat,
                        text=part,
                        parse_mode='HTML',
                        disable_web_page_preview=True
                    )
                    await asyncio.sleep(1)  # 防止速率限制
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

    def fetch_oodata(self):
        """抓取oodata网页内容"""
        try:
            response = self.session.get(OODATA_URL, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            error_msg = f"抓取oodata失败: {str(e)}"
            print(f"❌ {error_msg}")
            return None

    def parse_freebies(self, html):
        """解析限免信息"""
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 查找今日发布的信息
        today_section = soup.find('div', {'class': 'post-list'})
        if not today_section:
            print("⚠️ 未找到今日信息区域")
            return None
        
        items = today_section.find_all('article', {'class': 'post'})
        if not items:
            print("⚠️ 今日无发布内容")
            return None
        
        freebies = {"本体限免": [], "内购限免": []}
        
        for item in items:
            # 检查日期是否为今天
            date_tag = item.find('time', {'class': 'post-date'})
            if not date_tag or today not in date_tag.get('datetime', ''):
                continue
            
            # 提取标题和链接
            title_tag = item.find('h2', {'class': 'post-title'})
            title = title_tag.get_text(strip=True) if title_tag else "无标题"
            link = title_tag.find('a')['href'] if title_tag and title_tag.find('a') else None
            
            # 提取类型和价格
            type_tag = item.find('span', {'class': 'post-category'})
            item_type = type_tag.get_text(strip=True) if type_tag else "未知类型"
            
            price_tag = item.find('span', {'class': 'post-price'})
            price_info = price_tag.get_text(strip=True) if price_tag else ""
            
            # 分类处理
            if any(keyword in item_type for keyword in ["本体", "完全", "限免"]):
                category = "本体限免"
            elif any(keyword in item_type for keyword in ["内购", "IAP"]):
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

    def format_message(self, freebies):
        """格式化消息内容"""
        if not freebies or (not freebies["本体限免"] and not freebies["内购限免"]):
            return None
        
        message = "🎮 <b>今日限免信息</b> 🎮\n\n"
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
                    message += f"\n  🔗 <a href='{item['link']}'>查看详情</a>"
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
                    message += f"\n  🔗 <a href='{item['link']}'>查看详情</a>"
                message += "\n"
        
        message += "\n📌 数据来源: oodata.net"
        return message

    async def run(self):
        """主执行逻辑"""
        print("🚀 启动oodata限免信息抓取...")
        
        # 检查必要配置
        if not all([self.bot_token, self.channel_id, self.personal_chat_id]):
            print("❌ 缺少必要的环境变量配置")
            return
        
        # 抓取数据
        html = self.fetch_oodata()
        if not html:
            await self.send_telegram_message("无法获取oodata网站数据", self.personal_chat_id, is_error=True)
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
