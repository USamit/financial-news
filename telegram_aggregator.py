import os
from datetime import datetime, timedelta
import feedparser
import requests
from collections import defaultdict

token = os.getenv('TELEGRAM_BOT_TOKEN')
chat = os.getenv('TELEGRAM_CHAT_ID')

# ============================================
# LOAD RECIPIENTS from recipients.txt
# ============================================
def load_recipients():
    """Load recipient chat IDs from recipients.txt file"""
    recipients = []
    
    # Always start with the main chat ID from secret
    if chat:
        recipients.append(chat)
        print('Added primary recipient from TELEGRAM_CHAT_ID secret')
    
    # Try to load additional recipients from file
    try:
        with open('recipients.txt', 'r') as f:
            print('Successfully opened recipients.txt')
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Skip the TELEGRAM_CHAT_ID placeholder (already added above)
                if line == 'TELEGRAM_CHAT_ID':
                    continue
                
                # Add the chat ID
                recipients.append(line)
                print('  Line ' + str(line_num) + ': Added recipient ' + line)
        
        print('Total recipients loaded: ' + str(len(recipients)))
        return recipients
        
    except FileNotFoundError:
        print('WARNING: recipients.txt not found, using only TELEGRAM_CHAT_ID from secret')
        return recipients
    except Exception as e:
        print('ERROR reading recipients.txt: ' + str(e))
        return recipients

RECIPIENTS = load_recipients()

print('\n' + '=' * 60)
print('Starting Financial News Aggregator...')
print('=' * 60)

# ============================================
# RSS FEEDS - Only Verified Working Feeds
# ============================================
feeds = {
    # Economic Times (6 feeds)
    'ET Markets': 'https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms',
    'ET Banking': 'https://economictimes.indiatimes.com/industry/banking/finance/banking/rssfeeds/13358256.cms',
    'ET Finance': 'https://economictimes.indiatimes.com/industry/banking/finance/rssfeeds/13358259.cms',
    'ET Insurance': 'https://economictimes.indiatimes.com/industry/banking/finance/insure/rssfeeds/13358276.cms',
    'ET Stocks': 'https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms',
    'ET Economy': 'https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms',
    
    # Mint (6 feeds)
    'Mint Markets': 'https://www.livemint.com/rss/markets',
    'Mint Money': 'https://www.livemint.com/rss/money',
    'Mint Banking': 'https://www.livemint.com/rss/industry/banking',
    'Mint Insurance': 'https://www.livemint.com/rss/insurance',
    'Mint Companies': 'https://www.livemint.com/rss/companies',
    'Mint Economy': 'https://www.livemint.com/rss/news/india',
    
    # Financial Times (6 feeds)
    'FT Markets': 'https://www.ft.com/markets?format=rss',
    'FT Banking': 'https://www.ft.com/companies/financials?format=rss',
    'FT World Economy': 'https://www.ft.com/world/economy?format=rss',
    'FT Companies': 'https://www.ft.com/companies?format=rss',
    'FT India': 'https://www.ft.com/india?format=rss',
    'FT Asia Markets': 'https://www.ft.com/markets/asia-pacific?format=rss',
    
    # Wall Street Journal (5 feeds)
    'WSJ Markets': 'https://feeds.content.dowjones.io/public/rss/RSSMarketsMain',
    'WSJ Finance': 'https://feeds.content.dowjones.io/public/rss/WSJcomUSBusiness',
    'WSJ Economy': 'https://feeds.content.dowjones.io/public/rss/RSSWorldNews',
    'WSJ India': 'https://feeds.content.dowjones.io/public/rss/WSJcomIndia',
    'WSJ Asia': 'https://feeds.content.dowjones.io/public/rss/WSJcomAsia',
}

# ============================================
# COMPREHENSIVE KEYWORD LIST
# ============================================
keywords = [
    # Core banking & finance
    'bank', 'banks', 'banking', 'lender', 'lenders', 'lending',
    'financial', 'finance', 'financing', 'fintech',
    'credit', 'loan', 'loans', 'mortgage',
    'deposit', 'deposits', 'capital', 'asset',
    
    # Rates & monetary policy
    'interest rate', 'rates', 'rate cut', 'rate hike',
    'repo', 'reverse repo', 'bank rate', 'fed funds', 'terminal rate',
    'policy rate', 'monetary', 'liquidity', 'tightening', 'easing',
    
    # Deposits (specific types)
    'deposit rate', 'term deposit', 'fixed deposit', 'fd rates',
    'savings rate', 'certificate of deposit', 'cd rates',
    'retail deposit', 'bulk deposit',
    
    # Money markets & wholesale funding
    'commercial paper', 'treasury bill', 't-bill',
    'money market', 'interbank', 'overnight rate', 'repo market',
    
    # Markets & investments
    'market', 'markets', 'stock', 'stocks', 'equity', 'equities',
    'share', 'shares', 'index', 'indices',
    'invest', 'investment', 'investor',
    'fund', 'funds', 'mutual fund', 'etf',
    'volatility', 'valuation',
    
    # Bonds & yield curve
    'bond', 'bonds', 'bond yield', 'bond issuance',
    'debt', 'debt issuance', 'yield', 'yields', 'yield curve',
    'spread', 'spreads', 'credit spread',
    'sovereign yield', 'gilts', 'g-sec', 'government securities',
    
    # Inflation & macro
    'inflation', 'deflation', 'cpi inflation', 'core inflation',
    'real rates', 'inflation expectations',
    'fiscal', 'budget', 'deficit',
    'economy', 'economic', 'gdp', 'growth', 'recession',
    
    # Central banks & regulators
    'rbi', 'sebi', 'fed', 'ecb', 'boj',
    'irdai', 'irda',
    'central bank', 'regulation', 'regulatory', 'compliance',
    'policy', 'treasury', 'sovereign',
    
    # Risk & balance sheet
    'capital adequacy', 'basel',
    'npa', 'npas', 'bad loan',
    'provision', 'provisions',
    'stress test', 'asset quality',
    'leverage', 'solvency', 'liquidity coverage',
    'lcr', 'nsfr', 'alm',
    
    # Corporate borrowing & funding
    'corporate borrowing', 'refinancing',
    'funding cost', 'cost of capital', 'cost of funds',
    'deposit mobilisation',
    
    # Payments & digital
    'payment', 'payments', 'upi', 'cards', 'digital',
    'wallet', 'neobank',
    
    # Corporate & business finance
    'earnings', 'profit', 'profits', 'loss',
    'margin', 'margins',
    'ipo', 'listing', 'buyback',
    'merger', 'acquisition', 'm&a',
    'balance sheet', 'cash flow',
    
    # Insurance - General
    'insurance', 'insurer', 'insurers', 'reinsurance', 'reinsurer',
    'underwriting', 'underwriter', 'premium', 'premiums',
    'policyholder', 'policy', 'claim', 'claims',
    
    # Insurance - Life
    'life insurance', 'lic', 'term insurance', 'endowment',
    'ulip', 'annuity', 'pension',
    
    # Insurance - Health
    'health insurance', 'mediclaim', 'hospitalisation',
    
    # Insurance - General/Non-Life
    'general insurance', 'motor insurance', 'fire insurance',
    'marine insurance', 'property insurance', 'liability insurance',
    
    # Insurance - Metrics & Ratios
    'claims ratio', 'loss ratio', 'combined ratio',
    'expense ratio', 'commission ratio',
    'incurred claims', 'claims paid', 'claims outstanding',
    'claim settlement ratio',
    
    # Insurance - Solvency & Capital
    'solvency ratio', 'solvency margin',
    'own funds', 'technical reserves',
    
    # Insurance - Distribution
    'agent', 'broker', 'bancassurance', 'distribution',
    
    # India-specific
    'psu bank', 'public sector bank',
    'nbfc', 'hfc',
    'mclr', 'base rate', 'crr', 'slr',
    'liquidity adjustment facility',
    
    # Publication names
    'barrons', "barron's"
]

articles = []
barrons_articles = []
feed_stats = {}
seen_urls = set()

# ============================================
# PROCESS RSS FEEDS
# ============================================
for source, url in feeds.items():
    try:
        print('\n' + source + ':')
        feed = feedparser.parse(url)
        
        total_entries = len(feed.entries)
        print('  Total entries: ' + str(total_entries))
        
        if not feed.entries:
            print('  No entries found')
            feed_stats[source] = {'total': 0, 'recent': 0, 'relevant': 0, 'barrons': 0}
            continue
        
        recent_count = 0
        source_count = 0
        barrons_count = 0
        
        for entry in feed.entries[:50]:
            try:
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        pub_date = datetime(*entry.published_parsed[:6])
                    except:
                        pass
                
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
                
                if link in seen_urls:
                    continue
                
                text = (title + ' ' + str(description)).lower()
                is_relevant = any(kw in text for kw in keywords)
                
                is_barrons = 'barron' in text
                
                if is_relevant:
                    seen_urls.add(link)
                    time_str = pub_date.strftime('%H:%M') if pub_date else 'Recent'
                    article_data = {
                        'source': source,
                        'title': title,
                        'url': link,
                        'time': time_str,
                        'date': pub_date or datetime.now()
                    }
                    
                    if is_barrons:
                        barrons_articles.append(article_data)
                        barrons_count += 1
                    else:
                        articles.append(article_data)
                    
                    source_count += 1
                    
                    if source_count >= 8:
                        break
                        
            except Exception as e:
                continue
        
        feed_stats[source] = {
            'total': total_entries,
            'recent': recent_count,
            'relevant': source_count,
            'barrons': barrons_count
        }
        
        print('  Recent (24 hrs): ' + str(recent_count))
        print('  Relevant: ' + str(source_count))
        if barrons_count > 0:
            print('  Barrons articles: ' + str(barrons_count))
        
    except Exception as e:
        print('  Error: ' + str(e))
        feed_stats[source] = {'total': 0, 'recent': 0, 'relevant': 0, 'barrons': 0}
        continue

# ============================================
# SUMMARY
# ============================================
print('\n' + '=' * 60)
print('SUMMARY BY PUBLICATION')
print('=' * 60)

for pub in ['ET', 'Mint', 'FT', 'WSJ']:
    pub_feeds = {k: v for k, v in feed_stats.items() if k.startswith(pub)}
    if pub_feeds:
        total_rel = sum(f['relevant'] for f in pub_feeds.values())
        total_barrons = sum(f['barrons'] for f in pub_feeds.values())
        if total_barrons > 0:
            print(pub + ': ' + str(total_rel) + ' articles (' + str(total_barrons) + ' Barrons) from ' + str(len(pub_feeds)) + ' feeds')
        else:
            print(pub + ': ' + str(total_rel) + ' articles from ' + str(len(pub_feeds)) + ' feeds')

print('\nTotal unique articles: ' + str(len(articles)))
print('Total Barrons articles: ' + str(len(barrons_articles)))
print('=' * 60)

# ============================================
# BUILD TELEGRAM MESSAGE
# ============================================
if not articles and not barrons_articles:
    msg = '*Financial News Digest*\n' + datetime.now().strftime('%B %d, %Y') + '\n\nNo relevant articles found today.'
    messages = [msg]
else:
    articles.sort(key=lambda x: x['date'], reverse=True)
    barrons_articles.sort(key=lambda x: x['date'], reverse=True)
    
    by_source = defaultdict(list)
    for article in articles:
        by_source[article['source']].append(article)
    
    messages = []
    current_msg = '*Financial News Digest*\n'
    current_msg = current_msg + datetime.now().strftime('%B %d, %Y') + '\n\n'
    current_msg = current_msg + str(len(articles) + len(barrons_articles)) + ' unique articles from ' + str(len(by_source)) + ' sources\n'
    current_msg = current_msg + '━━━━━━━━━━━━━━━━━\n\n'
    
    et_sources = sorted([s for s in by_source.keys() if s.startswith('ET ')])
    mint_sources = sorted([s for s in by_source.keys() if s.startswith('Mint ')])
    ft_sources = sorted([s for s in by_source.keys() if s.startswith('FT ')])
    wsj_sources = sorted([s for s in by_source.keys() if s.startswith('WSJ ')])
    
    def add_section(msg, section_text):
        if len(msg) + len(section_text) > 3800:
            return msg, section_text
        return msg + section_text, ''
    
    def build_section(title, sources_list, prefix=''):
        if not sources_list:
            return ''
        section = '*' + title + '*\n'
        for source in sources_list:
            items = by_source[source][:5]
            if items:
                items_sorted = sorted(items, key=lambda x: x['date'], reverse=True)
                section = section + '_' + source.replace(prefix, '') + '_\n'
                for i, article in enumerate(items_sorted, 1):
                    title_short = article['title']
                    if len(title_short) > 75:
                        title_short = title_short[:72] + '...'
                    section = section + str(i) + '. [' + title_short + '](' + article['url'] + ')\n'
        return section + '\n'
    
    for title, sources, prefix in [
        ('ECONOMIC TIMES', et_sources, 'ET '),
        ('MINT', mint_sources, 'Mint '),
        ('FINANCIAL TIMES', ft_sources, 'FT '),
        ('WALL STREET JOURNAL', wsj_sources, 'WSJ ')
    ]:
        if sources:
            section = build_section(title, sources, prefix)
            if section:
                current_msg, overflow = add_section(current_msg, section)
                if overflow:
                    messages.append(current_msg)
                    current_msg = overflow
    
    if barrons_articles:
        barrons_section = '*BARRONS*\n'
        barrons_section = barrons_section + '_Republished Articles_\n'
        for i, article in enumerate(barrons_articles[:10], 1):
            title_short = article['title']
            if len(title_short) > 75:
                title_short = title_short[:72] + '...'
            barrons_section = barrons_section + str(i) + '. [' + title_short + '](' + article['url'] + ')\n'
        barrons_section = barrons_section + '\n'
        
        current_msg, overflow = add_section(current_msg, barrons_section)
        if overflow:
            messages.append(current_msg)
            current_msg = overflow
    
    if current_msg.strip():
        messages.append(current_msg)

# ============================================
# SEND TO ALL RECIPIENTS
# ============================================
if not token:
    print('\nERROR: Missing TELEGRAM_BOT_TOKEN')
elif not RECIPIENTS:
    print('\nERROR: No recipients found')
else:
    try:
        url = 'https://api.telegram.org/bot' + token + '/sendMessage'
        
        print('\n' + '=' * 60)
        print('SENDING TO ' + str(len(RECIPIENTS)) + ' RECIPIENTS')
        print('=' * 60)
        
        for recipient in RECIPIENTS:
            print('\nSending to chat ID: ' + str(recipient)[:3] + '...')
            
            for i, msg in enumerate(messages):
                print('  Part ' + str(i + 1) + '/' + str(len(messages)) + ' (' + str(len(msg)) + ' chars)')
                
                data = {
                    'chat_id': recipient,
                    'text': msg,
                    'parse_mode': 'Markdown',
                    'disable_web_page_preview': True
                }
                
                response = requests.post(url, json=data, timeout=30)
                
                if response.status_code == 200:
                    print('  ✅ Sent')
                else:
                    print('  ❌ Error: ' + str(response.status_code))
                    print('  Response: ' + response.text[:200])
                
                if i < len(messages) - 1:
                    import time
                    time.sleep(1)
        
        print('\n✅ ALL MESSAGES SENT!')
            
    except Exception as e:
        print('\nERROR sending messages: ' + str(e))

print('\nScript completed')
