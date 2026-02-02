#!/usr/bin/env python3
“””
Telegram Bot Financial News Aggregator
Perfect for iOS - delivers news directly to your Telegram app
“””

import os
import json
from datetime import datetime, timedelta
import feedparser
from collections import defaultdict

try:
import requests
except ImportError:
print(“Please install requests: pip install requests”)
exit(1)

class TelegramNewsAggregator:
“”“Financial news aggregator with Telegram delivery”””

```
def __init__(self, config_file='telegram_config.json'):
    self.config = self.load_config(config_file)
    self.bot_token = self.config.get('bot_token') or os.getenv('TELEGRAM_BOT_TOKEN')
    self.chat_id = self.config.get('chat_id') or os.getenv('TELEGRAM_CHAT_ID')
    
    self.feeds = {
        'Economic Times': [
            'https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms',
        ],
        'Mint': [
            'https://www.livemint.com/rss/markets',
        ],
        'Reuters': [
            'https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best'
        ]
    }
    
    self.banking_keywords = [
        'bank', 'banking', 'financial', 'fintech', 'credit',
        'loan', 'deposit', 'rbi', 'federal reserve', 'central bank',
        'payment', 'digital banking', 'neobank', 'regulatory'
    ]

def load_config(self, config_file):
    """Load Telegram configuration"""
    default_config = {
        'bot_token': '',  # Get from @BotFather
        'chat_id': '',    # Your Telegram chat ID
        'instructions': {
            'setup': [
                'Open Telegram and search for @BotFather',
                'Send: /newbot',
                'Follow instructions to create your bot',
                'Copy the bot token to this config',
                'Send a message to your bot',
                'Visit: https://api.telegram.org/bot<TOKEN>/getUpdates',
                'Find your chat_id in the response'
            ]
        }
    }
    
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    else:
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        print(f"Created config template: {config_file}")
        return default_config

def is_relevant(self, title, description):
    """Check if article is relevant"""
    text = (title + ' ' + description).lower()
    return any(keyword in text for keyword in self.banking_keywords)

def fetch_feed(self, url, source):
    """Fetch RSS feed"""
    articles = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            pub_date = None
            if hasattr(entry, 'published_parsed'):
                pub_date = datetime(*entry.published_parsed[:6])
            
            if pub_date and (datetime.now() - pub_date) > timedelta(days=1):
                continue
            
            title = entry.get('title', '')
            description = entry.get('summary', '') or entry.get('description', '')
            
            if not self.is_relevant(title, description):
                continue
            
            articles.append({
                'source': source,
                'title': title,
                'description': description[:200],
                'url': entry.get('link', ''),
                'published': pub_date.strftime('%H:%M') if pub_date else 'Recent'
            })
    except Exception as e:
        print(f"Error: {e}")
    
    return articles

def fetch_all_news(self):
    """Fetch all news"""
    print("\n📡 Fetching news...")
    all_articles = []
    
    for source, urls in self.feeds.items():
        for url in urls:
            articles = self.fetch_feed(url, source)
            all_articles.extend(articles)
            print(f"  ✓ {source}: {len(articles)} articles")
    
    return all_articles

def format_telegram_message(self, articles):
    """Format message for Telegram"""
    by_source = defaultdict(list)
    for article in articles:
        by_source[article['source']].append(article)
    
    # Header
    message = f"🏦 *Financial News Digest*\n"
    message += f"📅 {datetime.now().strftime('%B %d, %Y')}\n\n"
    message += f"📊 {len(articles)} articles from {len(by_source)} sources\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Articles by source
    for source in sorted(by_source.keys()):
        source_articles = by_source[source][:5]  # Limit per source
        message += f"📰 *{source}* ({len(source_articles)})\n"
        
        for i, article in enumerate(source_articles, 1):
            message += f"\n{i}. [{article['title']}]({article['url']})\n"
            message += f"   🕐 {article['published']}\n"
        
        message += "\n"
    
    message += "━━━━━━━━━━━━━━━━━━━━\n"
    message += "_Automated by Financial News Aggregator_"
    
    return message

def send_telegram_message(self, message):
    """Send message via Telegram"""
    if not self.bot_token or not self.chat_id:
        print("\n❌ Telegram not configured!")
        print("Please set up bot_token and chat_id in telegram_config.json")
        print("\nSetup instructions:")
        print("1. Open Telegram, search: @BotFather")
        print("2. Create new bot: /newbot")
        print("3. Copy the token")
        print("4. Send a message to your bot")
        print("5. Get chat_id from: https://api.telegram.org/bot<TOKEN>/getUpdates")
        return False
    
    url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
    
    data = {
        'chat_id': self.chat_id,
        'text': message,
        'parse_mode': 'Markdown',
        'disable_web_page_preview': False
    }
    
    try:
        print("\n📱 Sending to Telegram...", end=' ')
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()
        print("✅ Sent!")
        return True
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def send_telegram_document(self, filepath, caption):
    """Send HTML file as document"""
    if not self.bot_token or not self.chat_id:
        return False
    
    url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"
    
    try:
        with open(filepath, 'rb') as f:
            files = {'document': f}
            data = {
                'chat_id': self.chat_id,
                'caption': caption
            }
            response = requests.post(url, files=files, data=data, timeout=30)
            response.raise_for_status()
            print("✅ HTML report sent!")
            return True
    except Exception as e:
        print(f"❌ Error sending document: {e}")
        return False

def generate_html(self, articles):
    """Generate simple HTML report"""
    html = f"""<!DOCTYPE html>
```

<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Financial News</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; padding: 20px; background: #f5f5f5; }}
        .article {{ background: white; padding: 15px; margin: 10px 0; border-radius: 8px; }}
        .title {{ font-weight: bold; font-size: 16px; margin-bottom: 5px; }}
        a {{ color: #007bff; text-decoration: none; }}
    </style>
</head>
<body>
    <h1>🏦 Financial News - {datetime.now().strftime('%B %d, %Y')}</h1>
"""

```
    by_source = defaultdict(list)
    for article in articles:
        by_source[article['source']].append(article)
    
    for source, source_articles in sorted(by_source.items()):
        html += f"<h2>📰 {source}</h2>"
        for article in source_articles:
            html += f"""
<div class="article">
    <div class="title"><a href="{article['url']}">{article['title']}</a></div>
    <div style="color: #666; font-size: 14px;">🕐 {article['published']}</div>
    <div style="margin-top: 8px;">{article['description']}</div>
</div>
```

“””

```
    html += "</body></html>"
    return html

def run(self):
    """Main execution"""
    print("\n" + "="*60)
    print("📱 Telegram Financial News Aggregator")
    print("="*60)
    
    # Fetch news
    articles = self.fetch_all_news()
    
    print(f"\n✅ Found {len(articles)} relevant articles")
    
    if not articles:
        message = f"🏦 Financial News Digest\n{datetime.now().strftime('%B %d, %Y')}\n\nNo relevant articles found today."
        self.send_telegram_message(message)
        return
    
    # Send message
    message = self.format_telegram_message(articles)
    self.send_telegram_message(message)
    
    # Generate and send HTML report
    html_content = self.generate_html(articles)
    html_file = f'financial_news_{datetime.now().strftime("%Y%m%d")}.html'
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("📄 Sending HTML report...", end=' ')
    self.send_telegram_document(html_file, f"📰 Full Report - {len(articles)} articles")
    
    print("\n" + "="*60)
    print("✅ Done! Check your Telegram app on iPhone")
    print("="*60 + "\n")
```

def main():
aggregator = TelegramNewsAggregator()
aggregator.run()

if **name** == “**main**”:
main()
