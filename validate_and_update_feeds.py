import feedparser
from datetime import datetime, timedelta
import socket
from collections import defaultdict
import requests
from bs4 import BeautifulSoup
import time

socket.setdefaulttimeout(10)

print('=' * 60)
print('Active Feed Discovery & Validation')
print('Testing for freshness AND keyword relevance')
print('=' * 60)

# ============================================
# LOAD KEYWORDS
# ============================================
def load_keywords():
    """Load keywords from keywords.txt"""
    keywords = []
    try:
        with open('keywords.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                keywords.append(line.lower())
        print(f'✓ Loaded {len(keywords)} keywords for relevance filtering\n')
        return keywords
    except:
        print('⚠ keywords.txt not found - using defaults')
        return ['bank', 'banking', 'finance', 'insurance', 'market', 'economy']

# ============================================
# LOAD MASTER FEEDS
# ============================================
def load_master_feeds():
    feeds = []
    try:
        with open('feeds_master.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) == 3:
                        feeds.append({
                            'name': parts[0].strip(),
                            'acronym': parts[1].strip(),
                            'url': parts[2].strip()
                        })
        return feeds
    except:
        return []

# ============================================
# SCRAPE ALL RSS LINKS FROM BS LISTING PAGE
# ============================================
def scrape_all_bs_rss_feeds():
    """
    Scrape ALL RSS feed links from Business Standard's listing page
    No filtering - just get everything
    """
    listing_url = 'https://www.business-standard.com/rss-feeds/listing'
    
    print(f'  🔍 Scraping ALL RSS feeds from: {listing_url}')
    
    all_feeds = []
    
    try:
        response = requests.get(listing_url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        if response.status_code != 200:
            print(f'    ⚠️  HTTP {response.status_code} - using fallback patterns')
            return get_bs_fallback_feeds()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find ALL links containing RSS URLs
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Only RSS links
            if '.rss' in href or 'rss' in href.lower():
                # Make absolute URL
                if href.startswith('http'):
                    full_url = href
                elif href.startswith('/'):
                    full_url = 'https://www.business-standard.com' + href
                else:
                    full_url = 'https://www.business-standard.com/' + href
                
                # Get link text for naming
                link_text = link.get_text(strip=True)
                
                # Avoid duplicates
                if full_url not in [f['url'] for f in all_feeds]:
                    all_feeds.append({
                        'name': link_text if link_text else 'Unknown',
                        'url': full_url
                    })
        
        print(f'    ✓ Found {len(all_feeds)} RSS feed URLs on page')
        
        if len(all_feeds) == 0:
            print('    ⚠️  No RSS links found - using fallback patterns')
            return get_bs_fallback_feeds()
        
        return all_feeds
        
    except Exception as e:
        print(f'    ⚠️  Scraping error: {str(e)[:50]} - using fallback')
        return get_bs_fallback_feeds()

def get_bs_fallback_feeds():
    """Fallback BS RSS feeds if scraping fails"""
    return [
        {'name': 'Home Page Top Stories', 'url': 'https://www.business-standard.com/rss/home_page_top_stories.rss'},
        {'name': 'Latest News', 'url': 'https://www.business-standard.com/rss/latest.rss'},
        {'name': 'Markets', 'url': 'https://www.business-standard.com/rss/markets-106.rss'},
        {'name': 'Banking Finance', 'url': 'https://www.business-standard.com/rss/finance-101.rss'},
        {'name': 'Economy Policy', 'url': 'https://www.business-standard.com/rss/economy-policy-102.rss'},
        {'name': 'Companies', 'url': 'https://www.business-standard.com/rss/companies-101.rss'},
        {'name': 'Technology', 'url': 'https://www.business-standard.com/rss/technology-108.rss'},
        {'name': 'Opinion', 'url': 'https://www.business-standard.com/rss/opinion-103.rss'},
    ]

# ============================================
# PREDEFINED PATTERNS FOR OTHER PUBLICATIONS
# ============================================
DISCOVERY_PATTERNS = {
    'ET': {
        'name': 'Economic Times',
        'patterns': [
            'https://economictimes.indiatimes.com/rssfeedstopstories.cms',
            'https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms',
            'https://economictimes.indiatimes.com/industry/banking/finance/rssfeeds/13358259.cms',
            'https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms',
            'https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms',
        ]
    },
    'FT': {
        'name': 'Financial Times',
        'patterns': [
            'https://www.ft.com/?format=rss',
            'https://www.ft.com/companies?format=rss',
            'https://www.ft.com/markets?format=rss',
            'https://www.ft.com/world/economy?format=rss',
        ]
    },
    'Mint': {
        'name': 'LiveMint',
        'patterns': [
            'https://www.livemint.com/rss/homepage',
            'https://www.livemint.com/rss/markets',
            'https://www.livemint.com/rss/money',
            'https://www.livemint.com/rss/companies',
            'https://www.livemint.com/rss/economy',
        ]
    },
    'NYT': {
        'name': 'New York Times',
        'patterns': [
            'https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml',
            'https://rss.nytimes.com/services/xml/rss/nyt/Business.xml',
            'https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml',
        ]
    },
    'WSJ': {
        'name': 'Wall Street Journal',
        'patterns': [
            'https://feeds.content.dowjones.io/public/rss/RSSMarketsMain',
            'https://feeds.content.dowjones.io/public/rss/WSJcomUSBusiness',
        ]
    },
    'MC': {
        'name': 'MoneyControl',
        'patterns': [
            'https://www.moneycontrol.com/rss/latestnews.xml',
            'https://www.moneycontrol.com/rss/business.xml',
            'https://www.moneycontrol.com/rss/marketreports.xml',
        ]
    }
}

# ============================================
# VALIDATE WITH KEYWORDS
# ============================================
def is_feed_active_and_relevant(url, keywords, min_relevant=3, hours=48):
    """
    Validate feed: recent + keyword relevant
    Returns: (is_active, relevant_count, total_count, freshest_age)
    """
    try:
        feed = feedparser.parse(url, request_headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        if not feed.entries:
            return False, 0, 0, 999
        
        relevant_recent_count = 0
        total_recent_count = 0
        freshest_age = 999
        
        for entry in feed.entries[:50]:
            try:
                is_recent = False
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                    age_hours = (datetime.now() - pub_date).total_seconds() / 3600
                    
                    if age_hours < hours:
                        is_recent = True
                        total_recent_count += 1
                    
                    if age_hours < freshest_age:
                        freshest_age = age_hours
                else:
                    is_recent = True
                    total_recent_count += 1
                
                if is_recent:
                    title = entry.get('title', '')
                    description = entry.get('summary', '') or entry.get('description', '')
                    text = (title + ' ' + str(description)).lower()
                    
                    is_relevant = any(kw in text for kw in keywords)
                    
                    if is_relevant:
                        relevant_recent_count += 1
                        
            except:
                pass
        
        is_active = relevant_recent_count >= min_relevant
        
        return is_active, relevant_recent_count, total_recent_count, freshest_age
        
    except Exception as e:
        return False, 0, 0, 999

# ============================================
# DISCOVER FEEDS FOR BS (SCRAPE ALL)
# ============================================
def discover_bs_feeds(keywords):
    """
    Discover ALL Business Standard feeds by scraping their listing page
    Tests each one for active + relevant
    """
    
    print('  🔍 Discovering Business Standard feeds...')
    print('     Method: Scraping RSS listing page for ALL feeds')
    
    # Get all RSS URLs from BS listing page
    all_bs_feeds = scrape_all_bs_rss_feeds()
    
    print(f'     Testing {len(all_bs_feeds)} feeds...')
    
    discovered = []
    
    for i, feed_info in enumerate(all_bs_feeds, 1):
        try:
            is_active, relevant, total_recent, age = is_feed_active_and_relevant(
                feed_info['url'], 
                keywords
            )
            
            if is_active:
                feed_name = feed_info['name']
                
                # Clean up name
                if not feed_name or feed_name == 'Unknown' or len(feed_name) < 3:
                    # Generate from URL
                    feed_name = feed_info['url'].split('/')[-1]
                    feed_name = feed_name.replace('.rss', '').replace('-', ' ').title()
                
                feed_name = f'BS {feed_name}'
                
                discovered.append({
                    'name': feed_name,
                    'acronym': 'BS',
                    'url': feed_info['url'],
                    'relevant': relevant,
                    'age': age
                })
                
                print(f'    [{i}/{len(all_bs_feeds)}] ✅ {feed_name}: {relevant} relevant ({age:.1f}h)')
            
            time.sleep(0.3)  # Be polite
            
        except Exception as e:
            continue
    
    print(f'     ✓ Found {len(discovered)} active & relevant BS feeds')
    return discovered

# ============================================
# DISCOVER FEEDS FOR OTHER PUBLICATIONS
# ============================================
def discover_other_feeds(pub_acronym, keywords):
    """
    Discover feeds for non-BS publications using predefined patterns
    """
    
    if pub_acronym not in DISCOVERY_PATTERNS:
        return []
    
    config = DISCOVERY_PATTERNS[pub_acronym]
    print(f'  🔍 Discovering {config["name"]} feeds...')
    
    discovered = []
    
    for url in config['patterns']:
        is_active, relevant, total, age = is_feed_active_and_relevant(url, keywords)
        
        if is_active:
            feed_name = url.split('/')[-1].replace('.rss', '').replace('.xml', '').replace('.cms', '')
            feed_name = feed_name.replace('-', ' ').replace('_', ' ').title()
            feed_name = f'{pub_acronym} {feed_name}'
            
            discovered.append({
                'name': feed_name,
                'acronym': pub_acronym,
                'url': url,
                'relevant': relevant,
                'age': age
            })
            
            print(f'    ✅ {feed_name}: {relevant} relevant ({age:.1f}h)')
    
    print(f'     ✓ Found {len(discovered)} active feeds')
    return discovered

# ============================================
# MAIN VALIDATION
# ============================================
keywords = load_keywords()
master_feeds = load_master_feeds()

if not master_feeds:
    print('ERROR: No feeds in feeds_master.txt')
    exit(1)

print(f'Testing {len(master_feeds)} feeds from feeds_master.txt')
print('Criteria: 3+ RELEVANT articles (matching keywords) from last 48h\n')

working_feeds = []
by_publication = defaultdict(list)

total_tested = 0
broken_feeds = []
irrelevant_feeds = []

for i, feed_info in enumerate(master_feeds, 1):
    print(f'[{i}/{len(master_feeds)}] {feed_info["name"]}')
    total_tested += 1
    
    is_active, relevant, total_recent, age = is_feed_active_and_relevant(
        feed_info['url'], 
        keywords
    )
    
    if is_active:
        print(f'  ✅ Active: {relevant} relevant articles ({total_recent} total recent, {age:.1f}h ago)')
        feed_info['relevant'] = relevant
        feed_info['age'] = age
        working_feeds.append(feed_info)
        by_publication[feed_info['acronym']].append(feed_info)
    else:
        if total_recent == 0:
            print(f'  ❌ Stale/Broken: 0 recent articles')
            broken_feeds.append(feed_info)
        elif relevant == 0:
            print(f'  ⚠️  Irrelevant: {total_recent} recent articles but 0 match keywords')
            irrelevant_feeds.append(feed_info)
        else:
            print(f'  ⚠️  Insufficient: Only {relevant} relevant articles (need 3+)')
            irrelevant_feeds.append(feed_info)

# ============================================
# AUTO-DISCOVERY FOR WEAK PUBLICATIONS
# ============================================
print('\n' + '=' * 60)
print('AUTO-DISCOVERY FOR PUBLICATIONS WITH <3 ACTIVE FEEDS')
print('=' * 60)

MIN_FEEDS_PER_PUB = 3

# Check BS first (special scraping)
if len(by_publication.get('BS', [])) < MIN_FEEDS_PER_PUB:
    current_count = len(by_publication.get('BS', []))
    print(f'\n⚠️  Business Standard (BS): Only {current_count} active feeds')
    print(f'   Target: {MIN_FEEDS_PER_PUB} feeds - discovering alternatives...')
    
    discovered = discover_bs_feeds(keywords)
    
    # Add discovered feeds (avoid duplicates)
    existing_urls = {f['url'] for f in by_publication['BS']}
    
    for feed_info in discovered:
        if feed_info['url'] not in existing_urls:
            working_feeds.append(feed_info)
            by_publication['BS'].append(feed_info)
    
    new_count = len(by_publication['BS'])
    print(f'   ✅ Now has {new_count} active feeds (+{new_count - current_count} discovered)')

# Check other publications
for pub_acronym, config in DISCOVERY_PATTERNS.items():
    current_count = len(by_publication.get(pub_acronym, []))
    
    if current_count < MIN_FEEDS_PER_PUB:
        print(f'\n⚠️  {config["name"]} ({pub_acronym}): Only {current_count} active feeds')
        print(f'   Target: {MIN_FEEDS_PER_PUB} feeds - discovering alternatives...')
        
        discovered = discover_other_feeds(pub_acronym, keywords)
        
        existing_urls = {f['url'] for f in by_publication[pub_acronym]}
        
        for feed_info in discovered:
            if feed_info['url'] not in existing_urls:
                working_feeds.append(feed_info)
                by_publication[pub_acronym].append(feed_info)
        
        new_count = len(by_publication[pub_acronym])
        print(f'   ✅ Now has {new_count} active feeds (+{new_count - current_count} discovered)')

# ============================================
# FINAL SUMMARY
# ============================================
print('\n' + '=' * 60)
print('VALIDATION SUMMARY')
print('=' * 60)
print(f'Total feeds tested: {total_tested}')
print(f'✅ Active & Relevant: {len(working_feeds)}')
print(f'⚠️  Has content but irrelevant: {len(irrelevant_feeds)}')
print(f'❌ Broken/Stale: {len(broken_feeds)}')

print(f'\n📊 BY PUBLICATION:')
for pub in sorted(by_publication.keys()):
    feeds = by_publication[pub]
    avg_relevant = sum(f.get('relevant', 0) for f in feeds) / len(feeds) if feeds else 0
    print(f'  {pub}: {len(feeds)} active feeds (avg {avg_relevant:.1f} relevant articles)')

# ============================================
# GENERATE feeds.txt
# ============================================
print('\n' + '=' * 60)
print('GENERATING feeds.txt')
print('=' * 60)

if len(working_feeds) == 0:
    print('❌ ERROR: No working feeds found!')
    exit(1)

try:
    with open('feeds.txt', 'w') as f:
        f.write('# AUTO-GENERATED - Only Active & Relevant Feeds\n')
        f.write('# Criteria: 3+ articles matching keywords from last 48h\n')
        f.write(f'# Last validated: {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}\n')
        f.write(f'# Active feeds: {len(working_feeds)}/{total_tested}\n\n')
        
        for pub in sorted(by_publication.keys()):
            feeds_list = by_publication[pub]
            
            # Sort by relevance
            feeds_list.sort(key=lambda x: x.get('relevant', 0), reverse=True)
            
            f.write(f'# {pub} - {len(feeds_list)} feeds\n')
            
            for feed_info in feeds_list:
                f.write(f'{feed_info["name"]}|{feed_info["acronym"]}|{feed_info["url"]}\n')
            
            f.write('\n')
    
    print(f'✅ Generated feeds.txt with {len(working_feeds)} active & relevant feeds')
    
    total_expected_articles = sum(f.get('relevant', 0) for f in working_feeds)
    print(f'   Expected relevant articles in main run: ~{total_expected_articles}')
    
except Exception as e:
    print(f'❌ Error: {str(e)}')
    exit(1)

print('\n' + '=' * 60)
print('✅ Validation complete!')
print('=' * 60)
