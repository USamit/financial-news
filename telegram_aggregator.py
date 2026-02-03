import os
from datetime import datetime, timedelta
import feedparser
import requests
from collections import defaultdict

token = os.getenv('TELEGRAM_BOT_TOKEN')
chat = os.getenv('TELEGRAM_CHAT_ID')

print('Starting Financial News Aggregator...')

feeds = {
    # Economic Times - Verified Working
    'ET Markets': 'https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms',
    'ET Banking': 'https://economictimes.indiatimes.com/industry/banking/finance/banking/rssfeeds/13358256.cms',
    'ET Finance': 'https://economictimes.indiatimes.com/industry/banking/finance/rssfeeds/13358259.cms',
    'ET Insurance': 'https://economictimes.indiatimes.com/industry/banking/finance/insure/rssfeeds/13358276.cms',
    'ET Stocks': 'https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms',
    
    # Mint - Verified Working
    'Mint Markets': 'https://www.livemint.com/rss/markets',
    'Mint Money': 'https://www.livemint.com/rss/money',
    'Mint Banking': 'https://www.livemint.com/rss/industry/banking',
    'Mint Companies': 'https://www.livemint.com/rss/companies',
    
    # MoneyControl - Verified Working
    'MC Business': 'https://www.moneycontrol.com/rss/business.xml',
    'MC Markets': 'https://www.moneycontrol.com/rss/latestnews.xml'
}

keywords = [
    'bank', 'banking', 'financial', 'finance', 'fintech', 'credit', 'loan',
    'payment', 'upi', 'market', 'stock', 'equity', 'invest', 'insurance',
    'rbi', 'sebi', 'deposit', 'nifty', 'sensex', 'ipo', 'mutual fund'
]

articles = []

for source, url in feeds.items():
    try:
        print('Fetching from ' + source + '...')
        feed = feedparser.parse(url)
        
        if not feed.entries:
            continue
            
        source_count = 0
        
        for entry in feed.entries[:50]:
            try:
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        pub_date = datetime(*entry.published_parsed[:6])
                    except:
                        pass
                
                # Changed to 2 days
                if pub_date and (datetime.now() - pub_date) > timedelta(days=2):
                    continue
                
                title = entry.get('title', '').strip()
                description = entry.get('summary', '') or entry.get('description', '')
                link = entry.get('link', '').strip()
                
                if not title or not link:
                    continue
                
                text = (title + ' ' + str(description)).lower()
                is_relevant = any(kw in text for kw in keywords)
                
                if is_relevant:
                    time_str = pub_date.strftime('%H:%M') if pub_date else 'Recent'
                    articles.append({
                        'source': source,
                        'title': title,
                        'url': link,
                        'time': time_str,
                        'date': pub_date or datetime.now()
                    })
                    source_count = source_count + 1
                    
                    if source_count >= 8:
                        break
                        
            except Exception as e:
                continue
        
        print('  Found ' + str(source_count) + ' relevant articles')
        
    except Exception as e:
        print('  Error: ' + str(e))
        continue

print('\nTotal articles: ' + str(len(articles)))

if not articles:
    msg = '*Financial News Digest*\n' + datetime.now().strftime('%B %d, %Y') + '\n\nNo relevant articles found today.'
    messages = [msg]
else:
    articles.sort(key=lambda x: x['date'], reverse=True)
    
    by_source = defaultdict(list)
    for article in articles:
        by_source[article['source']].append(article)
    
    # Build message parts
    messages = []
    current_msg = '*Financial News Digest*\n'
    current_msg = current_msg + datetime.now().strftime('%B %d, %Y') + '\n\n'
    current_msg = current_msg + '📊 ' + str(len(articles)) + ' articles from ' + str(len(by_source)) + ' sources\n'
    current_msg = current_msg + '━━━━━━━━━━━━━━━━━\n\n'
    
    # Group by publication
    et_sources = [s for s in by_source.keys() if s.startswith('ET ')]
    mint_sources = [s for s in by_source.keys() if s.startswith('Mint ')]
    mc_sources = [s for s in by_source.keys() if s.startswith('MC ')]
    
    def add_section(msg, section_text):
        # If adding this would exceed limit, start new message
        if len(msg) + len(section_text) > 3800:
            return msg, section_text
        return msg + section_text, ''
    
    # Economic Times
    if et_sources:
        section = '📰 *ECONOMIC TIMES*\n'
        for source in sorted(et_sources):
            items = by_source[source][:5]
            if items:
                section = section + '_' + source.replace('ET ', '') + '_\n'
                for i, article in enumerate(items, 1):
                    title_short = article['title']
                    if len(title_short) > 80:
                        title_short = title_short[:77] + '...'
                    section = section + str(i) + '. [' + title_short + '](' + article['url'] + ')\n'
        section = section + '\n'
        
        current_msg, overflow = add_section(current_msg, section)
        if overflow:
            messages.append(current_msg)
            current_msg = overflow
    
    # Mint
    if mint_sources:
        section = '📰 *MINT*\n'
        for source in sorted(mint_sources):
            items = by_source[source][:5]
            if items:
                section = section + '_' + source.replace('Mint ', '') + '_\n'
                for i, article in enumerate(items, 1):
                    title_short = article['title']
                    if len(title_short) > 80:
                        title_short = title_short[:77] + '...'
                    section = section + str(i) + '. [' + title_short + '](' + article['url'] + ')\n'
        section = section + '\n'
        
        current_msg, overflow = add_section(current_msg, section)
        if overflow:
            messages.append(current_msg)
            current_msg = overflow
    
    # MoneyControl
    if mc_sources:
        section = '📰 *MONEYCONTROL*\n'
        for source in sorted(mc_sources):
            items = by_source[source][:5]
            if items:
                section = section + '_' + source.replace('MC ', '') + '_\n'
                for i, article in enumerate(items, 1):
                    title_short = article['title']
                    if len(title_short) > 80:
                        title_short = title_short[:77] + '...'
                    section = section + str(i) + '. [' + title_short + '](' + article['url'] + ')\n'
        section = section + '\n'
        
        current_msg, overflow = add_section(current_msg, section)
        if overflow:
            messages.append(current_msg)
            current_msg = overflow
    
    # Add remaining content
    if current_msg.strip():
        messages.append(current_msg)

# Send to Telegram
if not token or not chat:
    print('ERROR: Token or Chat ID missing!')
else:
    try:
        url = 'https://api.telegram.org/bot' + token + '/sendMessage'
        
        for i, msg in enumerate(messages):
            print('\nSending message part ' + str(i+1) + '/' + str(len(messages)))
            print('Message length: ' + str(len(msg)) + ' characters')
            
            data = {
                'chat_id': chat,
                'text': msg,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, json=data, timeout=30)
            
            if response.status_code == 200:
                print('✅ Sent part ' + str(i+1))
            else:
                print('❌ Error on part ' + str(i+1) + ': ' + str(response.status_code))
                print(response.text[:200])
            
            # Small delay between messages
            if i < len(messages) - 1:
                import time
                time.sleep(1)
        
        print('\n✅ All messages sent!')
            
    except Exception as e:
        print('❌ Error: ' + str(e))

print('\nScript completed')
