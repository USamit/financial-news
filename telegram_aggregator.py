import os
from datetime import datetime, timedelta
import feedparser
import requests
from collections import defaultdict

token = os.getenv('TELEGRAM_BOT_TOKEN')
chat = os.getenv('TELEGRAM_CHAT_ID')

print('Fetching financial news...')

feeds = {
    # Economic Times - Comprehensive Coverage
    'ET Markets': 'https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms',
    'ET Banking': 'https://economictimes.indiatimes.com/industry/banking/finance/banking/rssfeeds/13358256.cms',
    'ET Finance': 'https://economictimes.indiatimes.com/industry/banking/finance/rssfeeds/13358259.cms',
    'ET Insurance': 'https://economictimes.indiatimes.com/industry/banking/finance/insure/rssfeeds/13358276.cms',
    'ET Stocks': 'https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms',
    'ET Economy': 'https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms',
    
    # Mint - Comprehensive Coverage
    'Mint Markets': 'https://www.livemint.com/rss/markets',
    'Mint Money': 'https://www.livemint.com/rss/money',
    'Mint Banking': 'https://www.livemint.com/rss/industry/banking',
    'Mint Insurance': 'https://www.livemint.com/rss/insurance',
    'Mint Companies': 'https://www.livemint.com/rss/companies',
    'Mint Economy': 'https://www.livemint.com/rss/news/india',
    
    # MoneyControl - Comprehensive Coverage
    'MC Business': 'https://www.moneycontrol.com/rss/business.xml',
    'MC Markets': 'https://www.moneycontrol.com/rss/marketedge.xml',
    'MC Stocks': 'https://www.moneycontrol.com/rss/latestnews.xml',
    'MC Banking': 'https://www.moneycontrol.com/rss/MCtopnews.xml',
    
    # Financial Times - Premium Global + India Coverage
    'FT Markets': 'https://www.ft.com/markets?format=rss',
    'FT Banking': 'https://www.ft.com/companies/financials?format=rss',
    'FT World Economy': 'https://www.ft.com/world/economy?format=rss',
    'FT Companies': 'https://www.ft.com/companies?format=rss',
    'FT India': 'https://www.ft.com/india?format=rss',
    'FT Asia Markets': 'https://www.ft.com/markets/asia-pacific?format=rss',
    
    # Wall Street Journal - Premium US/Global + India Coverage
    'WSJ Markets': 'https://feeds.content.dowjones.io/public/rss/RSSMarketsMain',
    'WSJ Finance': 'https://feeds.content.dowjones.io/public/rss/WSJcomUSBusiness',
    'WSJ Economy': 'https://feeds.content.dowjones.io/public/rss/RSSWorldNews',
    'WSJ India': 'https://feeds.content.dowjones.io/public/rss/WSJcomIndia',
    'WSJ Asia': 'https://feeds.content.dowjones.io/public/rss/WSJcomAsia',
    
    # Barrons - Premium Investment + India Coverage
    'Barrons Markets': 'https://www.barrons.com/rss',
    'Barrons Asia': 'https://www.barrons.com/rss/asia'
}

keywords = [
    # Banking
    'bank', 'banking', 'neobank', 'digital bank', 'hdfc', 'icici', 'sbi', 'axis',
    # Finance
    'financial', 'finance', 'fintech', 'credit', 'loan', 'lending', 'borrowing',
    # Payments
    'payment', 'upi', 'wallet', 'paytm', 'phonepe', 'razorpay',
    # Markets
    'market', 'stock', 'equity', 'share', 'trading', 'invest', 'sensex', 'nifty', 'nse', 'bse',
    # Insurance
    'insurance', 'insurer', 'policy', 'premium', 'life insurance', 'health insurance', 'lic',
    # Regulators
    'rbi', 'sebi', 'irdai', 'reserve bank', 'central bank', 'fed', 'federal reserve',
    # Key Terms
    'deposit', 'npa', 'monetary', 'fiscal', 'interest rate', 'repo rate',
    'bond', 'treasury', 'derivative', 'mutual fund', 'ipo', 'rupee', 'inr',
    # India specific
    'india', 'indian', 'mumbai', 'delhi', 'bangalore', 'adani', 'reliance', 'tata'
]

articles = []

for source, url in feeds.items():
    try:
        print('Fetching from ' + source + '...')
        feed = feedparser.parse(url)
        source_count = 0
        
        for entry in feed.entries[:40]:
            pub_date = None
            if hasattr(entry, 'published_parsed'):
                pub_date = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed'):
                pub_date = datetime(*entry.updated_parsed[:6])
            
            # Look back 2 days for better coverage
            if pub_date and (datetime.now() - pub_date) > timedelta(days=2):
                continue
            
            title = entry.get('title', '')
            description = entry.get('summary', '') or entry.get('description', '')
            link = entry.get('link', '')
            
            # Check relevance
            text = (title + ' ' + description).lower()
            if any(kw in text for kw in keywords):
                time_str = pub_date.strftime('%H:%M') if pub_date else 'Recent'
                articles.append({
                    'source': source,
                    'title': title,
                    'url': link,
                    'time': time_str,
                    'date': pub_date
                })
                source_count = source_count + 1
                if source_count >= 10:
                    break
        
        print('  Found ' + str(source_count) + ' articles')
    except Exception as e:
        print('  Error: ' + str(e))

# Sort by date (newest first)
articles.sort(key=lambda x: x.get('date') or datetime.min, reverse=True)

print('\nTotal articles found: ' + str(len(articles)))

if not articles:
    msg = '*Financial News Digest*\n' + datetime.now().strftime('%B %d, %Y') + '\n\nNo relevant articles found.'
else:
    by_source = defaultdict(list)
    for article in articles:
        by_source[article['source']].append(article)
    
    msg = '*Financial News Digest*\n'
    msg = msg + datetime.now().strftime('%B %d, %Y') + '\n\n'
    msg = msg + '📊 ' + str(len(articles)) + ' articles from ' + str(len(by_source)) + ' sources\n'
    msg = msg + '━━━━━━━━━━━━━━━━━\n\n'
    
    # Group by publication
    et_sources = [s for s in by_source.keys() if s.startswith('ET ')]
    mint_sources = [s for s in by_source.keys() if s.startswith('Mint ')]
    mc_sources = [s for s in by_source.keys() if s.startswith('MC ')]
    ft_sources = [s for s in by_source.keys() if s.startswith('FT ')]
    wsj_sources = [s for s in by_source.keys() if s.startswith('WSJ ')]
    barrons_sources = [s for s in by_source.keys() if 'Barrons' in s]
    
    # Economic Times
    if et_sources:
        msg = msg + '📰 *ECONOMIC TIMES*\n'
        for source in sorted(et_sources):
            items = by_source[source][:5]
            if items:
                msg = msg + '_' + source.replace('ET ', '') + '_\n'
                for i, article in enumerate(items, 1):
                    title_short = article['title']
                    if len(title_short) > 85:
                        title_short = title_short[:82] + '...'
                    msg = msg + str(i) + '. [' + title_short + '](' + article['url'] + ')\n'
        msg = msg + '\n'
    
    # Mint
    if mint_sources:
        msg = msg + '📰 *MINT*\n'
        for source in sorted(mint_sources):
            items = by_source[source][:5]
            if items:
                msg = msg + '_' + source.replace('Mint ', '') + '_\n'
                for i, article in enumerate(items, 1):
                    title_short = article['title']
                    if len(title_short) > 85:
                        title_short = title_short[:82] + '...'
                    msg = msg + str(i) + '. [' + title_short + '](' + article['url'] + ')\n'
        msg = msg + '\n'
    
    # MoneyControl
    if mc_sources:
        msg = msg + '📰 *MONEYCONTROL*\n'
        for source in sorted(mc_sources):
            items = by_source[source][:5]
            if items:
                msg = msg + '_' + source.replace('MC ', '') + '_\n'
                for i, article in enumerate(items, 1):
                    title_short = article['title']
                    if len(title_short) > 85:
                        title_short = title_short[:82] + '...'
                    msg = msg + str(i) + '. [' + title_short + '](' + article['url'] + ')\n'
        msg = msg + '\n'
    
    # Financial Times
    if ft_sources:
        msg = msg + '📰 *FINANCIAL TIMES*\n'
        for source in sorted(ft_sources):
            items = by_source[source][:5]
            if items:
                msg = msg + '_' + source.replace('FT ', '') + '_\n'
                for i, article in enumerate(items, 1):
                    title_short = article['title']
                    if len(title_short) > 85:
                        title_short = title_short[:82] + '...'
                    msg = msg + str(i) + '. [' + title_short + '](' + article['url'] + ')\n'
        msg = msg + '\n'
    
    # Wall Street Journal
    if wsj_sources:
        msg = msg + '📰 *WALL STREET JOURNAL*\n'
        for source in sorted(wsj_sources):
            items = by_source[source][:5]
            if items:
                msg = msg + '_' + source.replace('WSJ ', '') + '_\n'
                for i, article in enumerate(items, 1):
                    title_short = article['title']
                    if len(title_short) > 85:
                        title_short = title_short[:82] + '...'
                    msg = msg + str(i) + '. [' + title_short + '](' + article['url'] + ')\n'
        msg = msg + '\n'
    
    # Barrons
    if barrons_sources:
        msg = msg + '📰 *BARRONS*\n'
        for source in barrons_sources:
            items = by_source[source][:5]
            if items:
                section = source.replace('Barrons ', '')
                if section != source:
                    msg = msg + '_' + section + '_\n'
                for i, article in enumerate(items, 1):
                    title_short = article['title']
                    if len(title_short) > 85:
                        title_short = title_short[:82] + '...'
                    msg = msg + str(i) + '. [' + title_short + '](' + article['url'] + ')\n'
        msg = msg + '\n'

if token and chat:
    url = 'https://api.telegram.org/bot' + token + '/sendMessage'
    data = {'chat_id': chat, 'text': msg, 'parse_mode': 'Markdown', 'disable_web_page_preview': True}
    response = requests.post(url, json=data, timeout=10)
    if response.status_code == 200:
        print('✅ Sent to Telegram!')
    else:
        print('❌ Error: ' + str(response.status_code))
        print(response.text)
else:
    print('❌ No token or chat ID')
