import os
from datetime import datetime, timedelta
import feedparser
import requests
from collections import defaultdict

token = os.getenv(‘TELEGRAM_BOT_TOKEN’)
chat = os.getenv(‘TELEGRAM_CHAT_ID’)

print(‘Starting Financial News Aggregator…’)
print(’=’*60)

feeds = {
# Economic Times - Comprehensive Coverage
‘ET Markets’: ‘https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms’,
‘ET Banking’: ‘https://economictimes.indiatimes.com/industry/banking/finance/banking/rssfeeds/13358256.cms’,
‘ET Finance’: ‘https://economictimes.indiatimes.com/industry/banking/finance/rssfeeds/13358259.cms’,
‘ET Insurance’: ‘https://economictimes.indiatimes.com/industry/banking/finance/insure/rssfeeds/13358276.cms’,
‘ET Stocks’: ‘https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms’,
‘ET Economy’: ‘https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms’,

```
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
'Barrons Asia': 'https://www.barrons.com/articles/asia?mod=rss_asia'
```

}

# COMPLETE keywords list from user

keywords = [
# Banking & Finance Core
‘bank’, ‘banking’, ‘financial’, ‘finance’, ‘fintech’,
‘credit’, ‘loan’, ‘lender’, ‘capital’, ‘asset’,

```
# Rates & Policy
'rate hike', 'rate cut', 'policy rate', 'repo', 'reverse repo',
'bank rate', 'fed funds', 'terminal rate',

# Deposits & Retail Funding
'deposit rate', 'term deposit', 'fixed deposit', 'fd rates',
'savings rate', 'certificate of deposit', 'cd rates',
'retail deposit', 'bulk deposit',

# Money Markets & Wholesale Funding
'commercial paper', 'treasury bill', 't-bill',
'money market', 'interbank', 'overnight rate',
'repo market',

# Bonds & Yield Curve
'bond yield', 'yield curve', 'credit spread',
'sovereign yield', 'gilts', 'g-sec', 'government securities',

# Corporate Borrowing
'corporate borrowing', 'bond issuance', 'debt issuance',
'refinancing', 'funding cost', 'cost of capital',

# Liquidity & Balance Sheet
'cost of funds', 'liquidity', 'lcr', 'nsfr',
'alm', 'deposit mobilisation',

# Inflation
'inflation', 'cpi inflation', 'core inflation',
'real rates', 'inflation expectations',

# India-Specific
'rbi', 'mclr', 'base rate', 'crr', 'slr',
'liquidity adjustment facility'
```

]

articles = []
feed_stats = {}
seen_urls = set()  # Track duplicate URLs

for source, url in feeds.items():
try:
print(’\n’ + source + ‘:’)
feed = feedparser.parse(url)

```
    total_entries = len(feed.entries)
    print('  Total entries: ' + str(total_entries))
    
    if not feed.entries:
        print('  ❌ No entries found')
        feed_stats[source] = {'total': 0, 'recent': 0, 'relevant': 0}
        continue
    
    recent_count = 0
    source_count = 0
    
    for entry in feed.entries[:50]:
        try:
            pub_date = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    pub_date = datetime(*entry.published_parsed[:6])
                except:
                    pass
            
            # 24 hours lookback
            if pub_date and (datetime.now() - pub_date) <= timedelta(days=1):
                recent_count += 1
            elif not pub_date:
                recent_count += 1
            else:
                continue
            
            title = entry.get('title', '').strip()
            description = entry.get('summary', '') or entry.get('description', '')
            link = entry.get('link', '').strip()
            
            if not title or not link:
                continue
            
            # Check for duplicate URL
            if link in seen_urls:
                continue
            
            text = (title + ' ' + str(description)).lower()
            is_relevant = any(kw in text for kw in keywords)
            
            if is_relevant:
                seen_urls.add(link)  # Mark as seen
                time_str = pub_date.strftime('%H:%M') if pub_date else 'Recent'
                articles.append({
                    'source': source,
                    'title': title,
                    'url': link,
                    'time': time_str,
                    'date': pub_date or datetime.now()
                })
                source_count += 1
                
                if source_count >= 8:
                    break
                    
        except Exception as e:
            continue
    
    feed_stats[source] = {
        'total': total_entries,
        'recent': recent_count,
        'relevant': source_count
    }
    
    print('  Recent (24 hrs): ' + str(recent_count))
    print('  ✅ Relevant: ' + str(source_count))
    
except Exception as e:
    print('  ❌ Error: ' + str(e))
    feed_stats[source] = {'total': 0, 'recent': 0, 'relevant': 0}
    continue
```

print(’\n’ + ‘=’*60)
print(‘SUMMARY BY PUBLICATION’)
print(’=’*60)

for pub in [‘ET’, ‘Mint’, ‘MC’, ‘FT’, ‘WSJ’, ‘Barrons’]:
pub_feeds = {k: v for k, v in feed_stats.items() if k.startswith(pub)}
if pub_feeds:
total_rel = sum(f[‘relevant’] for f in pub_feeds.values())
print(f’{pub}: {total_rel} articles from {len(pub_feeds)} feeds’)

print(’\nTotal unique articles: ’ + str(len(articles)))
print(’=’*60)

if not articles:
msg = ‘*Financial News Digest*\n’ + datetime.now().strftime(’%B %d, %Y’) + ‘\n\nNo relevant articles found today.’
messages = [msg]
else:
# Sort ALL articles by recency first
articles.sort(key=lambda x: x[‘date’], reverse=True)

```
by_source = defaultdict(list)
for article in articles:
    by_source[article['source']].append(article)

messages = []
current_msg = '*Financial News Digest*\n'
current_msg = current_msg + datetime.now().strftime('%B %d, %Y') + '\n\n'
current_msg = current_msg + '📊 ' + str(len(articles)) + ' unique articles from ' + str(len(by_source)) + ' sources\n'
current_msg = current_msg + '━━━━━━━━━━━━━━━━━\n\n'

et_sources = sorted([s for s in by_source.keys() if s.startswith('ET ')])
mint_sources = sorted([s for s in by_source.keys() if s.startswith('Mint ')])
mc_sources = sorted([s for s in by_source.keys() if s.startswith('MC ')])
ft_sources = sorted([s for s in by_source.keys() if s.startswith('FT ')])
wsj_sources = sorted([s for s in by_source.keys() if s.startswith('WSJ ')])
barrons_sources = sorted([s for s in by_source.keys() if 'Barrons' in s])

def add_section(msg, section_text):
    if len(msg) + len(section_text) > 3800:
        return msg, section_text
    return msg + section_text, ''

def build_section(title, sources_list, prefix=''):
    if not sources_list:
        return ''
    section = '📰 *' + title + '*\n'
    for source in sources_list:
        items = by_source[source][:5]
        if items:
            # Sort items by recency WITHIN each subsection
            items_sorted = sorted(items, key=lambda x: x['date'], reverse=True)
            section = section + '_' + source.replace(prefix, '') + '_\n'
            for i, article in enumerate(items_sorted, 1):
                title_short = article['title']
                if len(title_short) > 75:
                    title_short = title_short[:72] + '...'
                section = section + str(i) + '. [' + title_short + '](' + article['url'] + ')\n'
    return section + '\n'

# Build all sections
for title, sources, prefix in [
    ('ECONOMIC TIMES', et_sources, 'ET '),
    ('MINT', mint_sources, 'Mint '),
    ('MONEYCONTROL', mc_sources, 'MC '),
    ('FINANCIAL TIMES', ft_sources, 'FT '),
    ('WALL STREET JOURNAL', wsj_sources, 'WSJ '),
    ('BARRONS', barrons_sources, 'Barrons ')
]:
    if sources:
        section = build_section(title, sources, prefix)
        if section:
            current_msg, overflow = add_section(current_msg, section)
            if overflow:
                messages.append(current_msg)
                current_msg = overflow

if current_msg.strip():
    messages.append(current_msg)
```

# Send to Telegram

if not token or not chat:
print(‘ERROR: Missing credentials’)
else:
try:
url = ‘https://api.telegram.org/bot’ + token + ‘/sendMessage’

```
    for i, msg in enumerate(messages):
        print('\nSending part ' + str(i+1) + '/' + str(len(messages)) + ' (' + str(len(msg)) + ' chars)')
        
        data = {
            'chat_id': chat,
            'text': msg,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True
        }
        
        response = requests.post(url, json=data, timeout=30)
        
        if response.status_code == 200:
            print('✅ Sent')
        else:
            print('❌ Error: ' + str(response.status_code))
            print(response.text[:300])
        
        if i < len(messages) - 1:
            import time
            time.sleep(1)
    
    print('\n✅ All sent!')
        
except Exception as e:
    print('❌ Error: ' + str(e))
```

print(’\nScript completed’)