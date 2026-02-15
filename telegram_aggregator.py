import os
from datetime import datetime, timedelta
import feedparser
import requests
from collections import defaultdict
import socket

# Set global timeout for all network operations
socket.setdefaulttimeout(10)

token = os.getenv('TELEGRAM_BOT_TOKEN')
chat = os.getenv('TELEGRAM_CHAT_ID')

print('=' * 60)
print('Starting Financial News Aggregator...')
print('=' * 60)

# ============================================
# LOAD RECIPIENTS from recipients.txt
# ============================================
def load_recipients():
    """Load recipient chat IDs from recipients.txt file"""
    recipients = []
    
    if chat:
        recipients.append(chat)
        print('✓ Added primary recipient from secret')
    
    try:
        with open('recipients.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or line == 'TELEGRAM_CHAT_ID':
                    continue
                recipients.append(line)
        print('✓ Loaded ' + str(len(recipients)) + ' total recipients')
        return recipients
    except FileNotFoundError:
        print('⚠ recipients.txt not found')
        return recipients
    except Exception as e:
        print('⚠ Error loading recipients: ' + str(e))
        return recipients

# ============================================
# LOAD KEYWORDS from keywords.txt
# ============================================
def load_keywords():
    """Load keywords from keywords.txt file"""
    keywords = []
    
    try:
        with open('keywords.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                keywords.append(line.lower())
        print('✓ Loaded ' + str(len(keywords)) + ' keywords')
        return keywords
    except FileNotFoundError:
        print('⚠ keywords.txt not found - using minimal defaults')
        return ['bank', 'banking', 'finance', 'insurance', 'market', 'economy']
    except Exception as e:
        print('⚠ Error loading keywords: ' + str(e))
        return ['bank', 'banking', 'finance', 'insurance', 'market', 'economy']

# ============================================
# LOAD FEEDS from feeds.txt
# ============================================
def load_feeds():
    """Load RSS feeds from feeds.txt file"""
    feeds = {}
    
    try:
        with open('feeds.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Expected format: Source Name|URL
                if '|' in line:
                    parts = line.split('|', 1)
                    if len(parts) == 2:
                        source_name = parts[0].strip()
                        url = parts[1].strip()
                        feeds[source_name] = url
        
        print('✓ Loaded ' + str(len(feeds)) + ' RSS feeds')
        return feeds
    except FileNotFoundError:
        print('⚠ feeds.txt not found - using minimal defaults')
        return {
            'ET Markets': 'https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms',
            'Mint Markets': 'https://www.livemint.com/rss/markets'
        }
    except Exception as e:
        print('⚠ Error loading feeds: ' + str(e))
        return {}

# ============================================
# LOAD TOPICS from topics.txt
# ============================================
def load_topics():
    """Load topic categorization from topics.txt file"""
    topics = []
    
    try:
        with open('topics.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Expected format: Topic Name|keyword1,keyword2,keyword3
                if '|' in line:
                    parts = line.split('|', 1)
                    if len(parts) == 2:
                        topic_name = parts[0].strip()
                        keywords_str = parts[1].strip()
                        keywords = [kw.strip().lower() for kw in keywords_str.split(',')]
                        topics.append({
                            'name': topic_name,
                            'keywords': keywords
                        })
        
        print('✓ Loaded ' + str(len(topics)) + ' topic categories')
        return topics
    except FileNotFoundError:
        print('⚠ topics.txt not found - using minimal defaults')
        return [
            {'name': 'BANKING & FINANCE', 'keywords': ['bank', 'banking', 'loan', 'credit']},
            {'name': 'MARKETS', 'keywords': ['market', 'stock', 'equity', 'share']},
            {'name': 'INSURANCE', 'keywords': ['insurance', 'insurer', 'premium', 'claim']},
            {'name': 'OTHER NEWS', 'keywords': ['other', 'news']}
        ]
    except Exception as e:
        print('⚠ Error loading topics: ' + str(e))
        return [
            {'name': 'BANKING & FINANCE', 'keywords': ['bank', 'banking', 'loan', 'credit']},
            {'name': 'MARKETS', 'keywords': ['market', 'stock', 'equity', 'share']},
            {'name': 'OTHER NEWS', 'keywords': ['other', 'news']}
        ]

# ============================================
# CATEGORIZE ARTICLE BY TOPIC
# ============================================
def categorize_article(title, description, topics):
    """Categorize article into topic based on keywords"""
    text = (title + ' ' + str(description)).lower()
    
    # Check each topic's keywords (order matters - first match wins)
    for topic in topics:
        for keyword in topic['keywords']:
            if keyword in text:
                return topic['name']
    
    # Default category if no match
    return 'OTHER NEWS'

# Load configuration
RECIPIENTS = load_recipients()
keywords = load_keywords()
feeds = load_feeds()
topics = load_topics()

if not feeds:
    print('ERROR: No feeds loaded!')
    exit(1)

articles = []
feed_stats = {}
seen_urls = set()

# ============================================
# PROCESS RSS FEEDS
# ============================================
print('\n' + '=' * 60)
print('FETCHING ARTICLES FROM ' + str(len(feeds)) + ' FEEDS')
print('=' * 60)

for source, url in feeds.items():
    try:
        print('\n' + source + ':')
        
        try:
            feed = feedparser.parse(url)
        except socket.timeout:
            print('  ⏱️  TIMEOUT - Skipping')
            feed_stats[source] = {'total': 0, 'recent': 0, 'relevant': 0}
            continue
        except Exception as e:
            print('  ❌ Error: ' + str(e)[:50])
            feed_stats[source] = {'total': 0, 'recent': 0, 'relevant': 0}
            continue
        
        total_entries = len(feed.entries)
        print('  Total entries: ' + str(total_entries))
        
        if not feed.entries:
            print('  No entries found')
            feed_stats[source] = {'total': 0, 'recent': 0, 'relevant': 0}
            continue
        
        recent_count = 0
        source_count = 0
        
        # INCREASED: Check up to 100 entries per feed (was 40)
        for entry in feed.entries[:100]:
            try:
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        pub_date = datetime(*entry.published_parsed[:6])
                    except:
                        pass
                
                # Filter: Last 24 hours only
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
                
                # Keyword matching
                text = (title + ' ' + str(description)).lower()
                is_relevant = any(kw in text for kw in keywords)
                
                if is_relevant:
                    seen_urls.add(link)
                    time_str = pub_date.strftime('%H:%M') if pub_date else 'Recent'
                    
                    # Categorize article by topic
                    topic = categorize_article(title, description, topics)
                    
                    articles.append({
                        'source': source,
                        'title': title,
                        'url': link,
                        'time': time_str,
                        'date': pub_date or datetime.now(),
                        'topic': topic
                    })
                    
                    source_count += 1
                    
                    # INCREASED: Max 20 articles per feed (was 10)
                    if source_count >= 20:
                        break
                        
            except Exception as e:
                continue
        
        feed_stats[source] = {
            'total': total_entries,
            'recent': recent_count,
            'relevant': source_count
        }
        
        print('  Recent (24hrs): ' + str(recent_count))
        print('  Relevant: ' + str(source_count))
        
    except Exception as e:
        print('  ❌ Error: ' + str(e)[:50])
        feed_stats[source] = {'total': 0, 'recent': 0, 'relevant': 0}
        continue

# ============================================
# SUMMARY
# ============================================
print('\n' + '=' * 60)
print('SUMMARY BY PUBLICATION')
print('=' * 60)

# Dynamically detect all publications
all_publications = set()
for source in feed_stats.keys():
    if ' ' in source:
        pub = source.split(' ')[0]
        all_publications.add(pub)

for pub in sorted(all_publications):
    pub_feeds = {k: v for k, v in feed_stats.items() if k.startswith(pub + ' ')}
    if pub_feeds:
        total_rel = sum(f['relevant'] for f in pub_feeds.values())
        print(pub + ': ' + str(total_rel) + ' articles from ' + str(len(pub_feeds)) + ' feeds')

print('\nTotal unique articles: ' + str(len(articles)))

# Print topic distribution
print('\n' + '=' * 60)
print('SUMMARY BY TOPIC')
print('=' * 60)

topic_counts = defaultdict(int)
for article in articles:
    topic_counts[article['topic']] += 1

for topic in sorted(topic_counts.keys()):
    print(topic + ': ' + str(topic_counts[topic]) + ' articles')

print('=' * 60)

# ============================================
# BUILD TELEGRAM MESSAGE
# ============================================
if not articles:
    msg = '*Financial News Digest*\n' + datetime.now().strftime('%B %d, %Y') + '\n\nNo relevant articles found today.'
    messages = [msg]
else:
    # Sort articles by date (most recent first)
    articles.sort(key=lambda x: x['date'], reverse=True)
    
    # Group articles by topic
    by_topic = defaultdict(list)
    for article in articles:
        by_topic[article['topic']].append(article)
    
    messages = []
    current_msg = '*Financial News Digest*\n'
    current_msg = current_msg + datetime.now().strftime('%B %d, %Y') + '\n\n'
    current_msg = current_msg + str(len(articles)) + ' articles across ' + str(len(by_topic)) + ' topics\n'
    current_msg = current_msg + '━━━━━━━━━━━━━━━━━\n\n'
    
    def add_section(msg, section_text):
        if len(msg) + len(section_text) > 3800:
            return msg, section_text
        return msg + section_text, ''
    
    # Build sections by topic (in order defined in topics.txt)
    for topic_config in topics:
        topic_name = topic_config['name']
        
        if topic_name not in by_topic:
            continue
        
        # INCREASED: Max 25 articles per topic (was 15)
        topic_articles = by_topic[topic_name][:25]
        
        if not topic_articles:
            continue
        
        section = '*' + topic_name + '*\n'
        section = section + str(len(topic_articles)) + ' articles\n\n'
        
        for i, article in enumerate(topic_articles, 1):
            title_short = article['title']
            if len(title_short) > 70:
                title_short = title_short[:67] + '...'
            
            # Show source in parentheses
            source_short = article['source']
            if len(source_short) > 20:
                source_short = source_short[:17] + '...'
            
            section = section + str(i) + '. [' + title_short + '](' + article['url'] + ')\n'
            section = section + '   _' + source_short + ' • ' + article['time'] + '_\n'
        
        section = section + '\n'
        
        current_msg, overflow = add_section(current_msg, section)
        if overflow:
            messages.append(current_msg)
            current_msg = overflow
    
    if current_msg.strip():
        messages.append(current_msg)

# ============================================
# SEND TO ALL RECIPIENTS
# ============================================
if not token:
    print('\n❌ ERROR: Missing TELEGRAM_BOT_TOKEN')
elif not RECIPIENTS:
    print('\n❌ ERROR: No recipients found')
else:
    try:
        url = 'https://api.telegram.org/bot' + token + '/sendMessage'
        
        print('\n' + '=' * 60)
        print('SENDING TO ' + str(len(RECIPIENTS)) + ' RECIPIENTS')
        print('=' * 60)
        
        for recipient in RECIPIENTS:
            print('\n📤 Sending to: ' + str(recipient)[:3] + '...')
            
            for i, msg in enumerate(messages):
                print('  Part ' + str(i + 1) + '/' + str(len(messages)))
                
                data = {
                    'chat_id': recipient,
                    'text': msg,
                    'parse_mode': 'Markdown',
                    'disable_web_page_preview': True
                }
                
                try:
                    response = requests.post(url, json=data, timeout=15)
                    
                    if response.status_code == 200:
                        print('  ✅ Sent')
                    else:
                        print('  ❌ Error: ' + str(response.status_code))
                except requests.Timeout:
                    print('  ⚠️  Timeout')
                except Exception as e:
                    print('  ❌ Error: ' + str(e)[:50])
                
                if i < len(messages) - 1:
                    import time
                    time.sleep(1)
        
        print('\n✅ ALL MESSAGES SENT!')
            
    except Exception as e:
        print('\n❌ ERROR: ' + str(e))

print('\n' + '=' * 60)
print('Script completed')
print('=' * 60)
