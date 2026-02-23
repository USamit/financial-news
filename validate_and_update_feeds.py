import feedparser
from datetime import datetime, timedelta
import socket
from collections import defaultdict

# Set timeout
socket.setdefaulttimeout(10)

print('=' * 60)
print('RSS Feed Auto-Validator')
print('Testing feeds from feeds_master.txt')
print('=' * 60)

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
        print('Please create feeds_master.txt with your feed list')
        return []
    except Exception as e:
        print(f'ERROR loading feeds_master.txt: {str(e)}')
        return []

# ============================================
# VALIDATE SINGLE FEED
# ============================================
def validate_feed(feed_info):
    """
    Validate a single feed
    Returns: (status, message)
    - status: 'working', 'stale', 'broken', 'timeout'
    """
    try:
        feed = feedparser.parse(feed_info['url'])
        
        if not feed.entries:
            return 'broken', '0 entries'
        
        # Check for recent content (last 72 hours - more lenient)
        recent_count = 0
        for entry in feed.entries[:20]:
            try:
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                    if (datetime.now() - pub_date) <= timedelta(hours=72):
                        recent_count += 1
            except:
                pass
        
        total_entries = len(feed.entries)
        
        if recent_count == 0:
            return 'stale', f'{total_entries} entries, 0 recent (72hrs)'
        else:
            return 'working', f'{total_entries} entries, {recent_count} recent'
        
    except socket.timeout:
        return 'timeout', 'Request timed out'
    except Exception as e:
        return 'broken', str(e)[:50]

# ============================================
# TEST ALL FEEDS
# ============================================
master_feeds = load_master_feeds()

if not master_feeds:
    print('No feeds loaded!')
    exit(1)

print(f'\nTesting {len(master_feeds)} feeds from feeds_master.txt\n')

working_feeds = []
stale_feeds = []
broken_feeds = []
timeout_feeds = []

for i, feed_info in enumerate(master_feeds, 1):
    print(f'[{i}/{len(master_feeds)}] {feed_info["name"]}')
    
    status, message = validate_feed(feed_info)
    
    if status == 'working':
        print(f'  ✅ {message}')
        working_feeds.append(feed_info)
    elif status == 'stale':
        print(f'  ⚠️  STALE: {message}')
        stale_feeds.append(feed_info)
        # Include stale feeds if they have entries (might update later)
        working_feeds.append(feed_info)
    elif status == 'timeout':
        print(f'  ⏱️  TIMEOUT: {message}')
        timeout_feeds.append(feed_info)
    else:  # broken
        print(f'  ❌ BROKEN: {message}')
        broken_feeds.append(feed_info)

# ============================================
# SUMMARY
# ============================================
print('\n' + '=' * 60)
print('VALIDATION SUMMARY')
print('=' * 60)
print(f'Total feeds tested: {len(master_feeds)}')
print(f'✅ Working (fresh): {len(working_feeds) - len(stale_feeds)}')
print(f'⚠️  Working (stale): {len(stale_feeds)}')
print(f'⏱️  Timeout: {len(timeout_feeds)}')
print(f'❌ Broken: {len(broken_feeds)}')
print(f'\n📝 Feeds to include in feeds.txt: {len(working_feeds)}')
print('=' * 60)

# Show what's excluded
if broken_feeds or timeout_feeds:
    print('\n⚠️  EXCLUDED FEEDS (will not be in feeds.txt):')
    for feed_info in broken_feeds + timeout_feeds:
        print(f'  - {feed_info["name"]}')

# ============================================
# GENERATE feeds.txt (AUTO-UPDATE)
# ============================================
print('\n' + '=' * 60)
print('UPDATING feeds.txt')
print('=' * 60)

# Group by publication
by_publication = defaultdict(list)
for feed_info in working_feeds:
    by_publication[feed_info['acronym']].append(feed_info)

try:
    with open('feeds.txt', 'w') as f:
        f.write('# AUTO-GENERATED - DO NOT EDIT MANUALLY\n')
        f.write('# Edit feeds_master.txt instead\n')
        f.write(f'# Last validated: {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}\n')
        f.write(f'# Working feeds: {len(working_feeds)}/{len(master_feeds)}\n')
        f.write('# Format: Feed Name|Acronym|URL\n\n')
        
        for pub in sorted(by_publication.keys()):
            feeds_list = by_publication[pub]
            f.write(f'# {pub} - {len(feeds_list)} feeds\n')
            
            for feed_info in sorted(feeds_list, key=lambda x: x['name']):
                f.write(f'{feed_info["name"]}|{feed_info["acronym"]}|{feed_info["url"]}\n')
            
            f.write('\n')
    
    print(f'✅ Updated feeds.txt with {len(working_feeds)} working feeds')
    print(f'   Excluded {len(broken_feeds) + len(timeout_feeds)} non-working feeds')
    
except Exception as e:
    print(f'❌ Error writing feeds.txt: {str(e)}')
    exit(1)

print('\n' + '=' * 60)
print('✅ Feed validation complete!')
print('   Main aggregator will use updated feeds.txt')
print('=' * 60)
