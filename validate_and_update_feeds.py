import feedparser
from datetime import datetime, timedelta
import socket
from collections import defaultdict
import requests
from bs4 import BeautifulSoup
import time

# Set timeout
socket.setdefaulttimeout(15)  # Longer timeout

print('=' * 60)
print('RSS Feed Auto-Validator & Discovery')
print('Intelligent feed validation with auto-discovery')
print('=' * 60)

# ============================================
# PUBLICATION DISCOVERY CONFIGS
# ============================================
DISCOVERY_CONFIGS = {
    'BS': {
        'name': 'Business Standard',
        'base_url': 'https://www.business-standard.com',
        'rss_page': 'https://www.business-standard.com/rss-feeds',
        'common_patterns': [
            'https://www.business-standard.com/rss/{}.rss',
            'https://www.business-standard.com/rss/news-{}.rss',
            'https://www.business-standard.com/rss/category-{}.rss',
        ]
    },
    'ET': {
        'name': 'Economic Times',
        'base_url': 'https://economictimes.indiatimes.com',
        'rss_page': 'https://economictimes.indiatimes.com/rss.cms',
        'common_patterns': [
            'https://economictimes.indiatimes.com/rssfeeds/{}.cms',
            'https://economictimes.indiatimes.com/{}/rssfeeds/{}.cms',
        ]
    },
    'FT': {
        'name': 'Financial Times',
        'base_url': 'https://www.ft.com',
        'common_patterns': [
            'https://www.ft.com/{}?format=rss',
            'https://www.ft.com/rss/{}',
        ]
    },
    'Mint': {
        'name': 'LiveMint',
        'base_url': 'https://www.livemint.com',
        'rss_page': 'https://www.livemint.com/rss',
        'common_patterns': [
            'https://www.livemint.com/rss/{}',
        ]
    },
    'NYT': {
        'name': 'New York Times',
        'base_url': 'https://www.nytimes.com',
        'common_patterns': [
            'https://rss.nytimes.com/services/xml/rss/nyt/{}.xml',
        ]
    },
    'WSJ': {
        'name': 'Wall Street Journal',
        'base_url': 'https://www.wsj.com',
        'common_patterns': [
            'https://feeds.content.dowjones.io/public/rss/{}',
        ]
    },
    'MC': {
        'name': 'MoneyControl',
        'base_url': 'https://www.moneycontrol.com',
        'common_patterns': [
            'https://www.moneycontrol.com/rss/{}.xml',
        ]
    }
}

# ============================================
# LOAD MASTER FEED LIST
# ============================================
def load_master_feeds():
    """Load all feeds from feeds_master.txt"""
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
                        feed_name = parts[0].strip()
                        acronym = parts[1].strip()
                        url = parts[2].strip()
                        feeds.append({
                            'name': feed_name,
                            'acronym': acronym,
                            'url': url
                        })
        
        return feeds
    except FileNotFoundError:
        print('ERROR: feeds_master.txt not found!')
        return []
    except Exception as e:
        print(f'ERROR loading feeds_master.txt: {str(e)}')
        return []

# ============================================
# SMART FEED VALIDATION (WITH RETRIES)
# ============================================
def validate_feed_smart(feed_info, max_retries=2):
    """
    Validate feed with retries and lenient criteria
    Returns: (status, message, entry_count)
    """
    
    for attempt in range(max_retries):
        try:
            # Add headers to mimic browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Parse feed with timeout
            feed = feedparser.parse(feed_info['url'], request_headers=headers)
            
            if not feed.entries:
                if attempt < max_retries - 1:
                    time.sleep(2)  # Wait before retry
                    continue
                return 'broken', '0 entries', 0
            
            # More lenient: Accept feeds with content from last 7 days (not 72 hours)
            recent_count = 0
            for entry in feed.entries[:30]:  # Check more entries
                try:
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6])
                        if (datetime.now() - pub_date) <= timedelta(days=7):
                            recent_count += 1
                except:
                    pass
            
            total_entries = len(feed.entries)
            
            # More lenient: Accept if ANY content exists, even if old
            if total_entries == 0:
                return 'broken', '0 entries', 0
            elif recent_count == 0 and total_entries > 0:
                # Has entries but old - still accept (some feeds update weekly)
                return 'working', f'{total_entries} entries (stale but valid)', total_entries
            else:
                return 'working', f'{total_entries} entries, {recent_count} recent (7d)', total_entries
            
        except socket.timeout:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return 'timeout', 'Timeout after retries', 0
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return 'broken', str(e)[:50], 0
    
    return 'broken', 'Failed after retries', 0

# ============================================
# DISCOVER RSS FEEDS FROM WEBSITE
# ============================================
def discover_feeds_from_website(pub_acronym):
    """
    Discover RSS feeds by scraping publication's website
    Returns list of discovered feed URLs
    """
    
    if pub_acronym not in DISCOVERY_CONFIGS:
        return []
    
    config = DISCOVERY_CONFIGS[pub_acronym]
    discovered = []
    
    print(f'  🔍 Discovering feeds from {config["name"]} website...')
    
    # Method 1: Scrape RSS page if available
    if 'rss_page' in config:
        try:
            response = requests.get(config['rss_page'], timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find RSS links
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if 'rss' in href.lower() or '.xml' in href.lower():
                        # Make absolute URL
                        if href.startswith('http'):
                            discovered.append(href)
                        elif href.startswith('/'):
                            discovered.append(config['base_url'] + href)
                
                # Find <link rel="alternate"> tags
                for link in soup.find_all('link', type='application/rss+xml'):
                    if 'href' in link.attrs:
                        href = link['href']
                        if href.startswith('http'):
                            discovered.append(href)
                        elif href.startswith('/'):
                            discovered.append(config['base_url'] + href)
        except Exception as e:
            print(f'    ⚠️  Error scraping RSS page: {str(e)[:50]}')
    
    # Method 2: Try common patterns
    if 'common_patterns' in config:
        common_sections = ['business', 'markets', 'economy', 'companies', 'banking', 
                          'finance', 'news', 'technology', 'opinion', 'latest']
        
        for pattern in config['common_patterns']:
            for section in common_sections:
                try:
                    url = pattern.format(section)
                    discovered.append(url)
                except:
                    pass
    
    # Remove duplicates
    discovered = list(set(discovered))
    
    print(f'    Found {len(discovered)} potential feed URLs')
    
    return discovered

# ============================================
# TEST DISCOVERED FEEDS
# ============================================
def test_discovered_feeds(discovered_urls, pub_acronym, pub_name):
    """
    Test discovered feeds and return working ones
    """
    
    if not discovered_urls:
        return []
    
    print(f'  🧪 Testing {len(discovered_urls)} discovered feeds...')
    
    working = []
    tested = 0
    
    for url in discovered_urls[:20]:  # Limit to 20 to save time
        tested += 1
        
        try:
            feed = feedparser.parse(url, request_headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if feed.entries and len(feed.entries) >= 5:  # At least 5 entries
                # Extract feed name from URL or title
                feed_title = feed.feed.get('title', '') if hasattr(feed, 'feed') else ''
                
                if not feed_title:
                    # Generate name from URL
                    feed_title = url.split('/')[-1].replace('.rss', '').replace('.xml', '').replace('-', ' ').title()
                
                feed_name = f'{pub_acronym} {feed_title}'
                
                working.append({
                    'name': feed_name,
                    'acronym': pub_acronym,
                    'url': url,
                    'entries': len(feed.entries)
                })
                
                print(f'    ✅ Found: {feed_name} ({len(feed.entries)} entries)')
        except:
            pass
    
    print(f'    Result: {len(working)} working feeds from {tested} tested')
    
    return working

# ============================================
# MAIN VALIDATION
# ============================================
master_feeds = load_master_feeds()

if not master_feeds:
    print('No feeds loaded!')
    exit(1)

print(f'\nTesting {len(master_feeds)} feeds from feeds_master.txt\n')

working_feeds = []
broken_feeds = []

# Track by publication
by_publication = defaultdict(list)

for i, feed_info in enumerate(master_feeds, 1):
    print(f'[{i}/{len(master_feeds)}] {feed_info["name"]}')
    
    status, message, entry_count = validate_feed_smart(feed_info)
    
    if status == 'working':
        print(f'  ✅ {message}')
        working_feeds.append(feed_info)
        by_publication[feed_info['acronym']].append(feed_info)
    else:
        print(f'  ❌ {status.upper()}: {message}')
        broken_feeds.append(feed_info)

# ============================================
# AUTO-DISCOVERY FOR PUBLICATIONS WITH 0 FEEDS
# ============================================
print('\n' + '=' * 60)
print('AUTO-DISCOVERY FOR PUBLICATIONS WITH NO WORKING FEEDS')
print('=' * 60)

for pub_acronym, config in DISCOVERY_CONFIGS.items():
    if pub_acronym not in by_publication or len(by_publication[pub_acronym]) == 0:
        print(f'\n❌ {config["name"]} ({pub_acronym}): 0 working feeds')
        print(f'   Attempting auto-discovery...')
        
        # Discover feeds
        discovered_urls = discover_feeds_from_website(pub_acronym)
        
        if discovered_urls:
            # Test discovered feeds
            new_working_feeds = test_discovered_feeds(discovered_urls, pub_acronym, config['name'])
            
            if new_working_feeds:
                print(f'   ✅ Auto-discovered {len(new_working_feeds)} working feeds!')
                working_feeds.extend(new_working_feeds)
                by_publication[pub_acronym].extend(new_working_feeds)
            else:
                print(f'   ⚠️  No working feeds found in discovery')
        else:
            print(f'   ⚠️  Could not discover feeds from website')
    else:
        print(f'✅ {config["name"]} ({pub_acronym}): {len(by_publication[pub_acronym])} working feeds')

# ============================================
# SUMMARY
# ============================================
print('\n' + '=' * 60)
print('VALIDATION SUMMARY')
print('=' * 60)
print(f'Total feeds tested: {len(master_feeds)}')
print(f'✅ Working from master: {len(working_feeds) - sum(len(feeds) for feeds in by_publication.values() if feeds[0].get("entries"))}')
print(f'🔍 Auto-discovered: {sum(1 for f in working_feeds if "entries" in f)}')
print(f'❌ Broken/Timeout: {len(broken_feeds)}')
print(f'\n📝 Total feeds for feeds.txt: {len(working_feeds)}')
print('=' * 60)

# Show publication breakdown
print('\n📊 BY PUBLICATION:')
for pub in sorted(by_publication.keys()):
    print(f'  {pub}: {len(by_publication[pub])} feeds')

# ============================================
# GENERATE feeds.txt
# ============================================
print('\n' + '=' * 60)
print('UPDATING feeds.txt')
print('=' * 60)

try:
    with open('feeds.txt', 'w') as f:
        f.write('# AUTO-GENERATED - DO NOT EDIT MANUALLY\n')
        f.write('# Edit feeds_master.txt instead\n')
        f.write(f'# Last validated: {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}\n')
        f.write(f'# Working feeds: {len(working_feeds)} ({len(master_feeds)} in master)\n')
        f.write('# Format: Feed Name|Acronym|URL\n\n')
        
        for pub in sorted(by_publication.keys()):
            feeds_list = by_publication[pub]
            f.write(f'# {pub} - {len(feeds_list)} feeds\n')
            
            for feed_info in sorted(feeds_list, key=lambda x: x['name']):
                f.write(f'{feed_info["name"]}|{feed_info["acronym"]}|{feed_info["url"]}\n')
            
            f.write('\n')
    
    print(f'✅ Updated feeds.txt with {len(working_feeds)} working feeds')
    print(f'   ({len(master_feeds)} from master + auto-discovered)')
    
except Exception as e:
    print(f'❌ Error writing feeds.txt: {str(e)}')
    exit(1)

print('\n' + '=' * 60)
print('✅ Feed validation & discovery complete!')
print('=' * 60)
