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
# CONFIGURATION
# ============================================
MIN_ARTICLES_FOR_TRENDING = 50  # Don't run trending on small batches
MAX_TRENDING_TOPICS = 5  # Show top 5 trending topics

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
    """Load RSS feeds from feeds.txt file with acronyms"""
    feeds = {}
    
    try:
        with open('feeds.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Expected format: Feed Name|Acronym|URL
                if '|' in line:
                    parts = line.split('|')
                    
                    if len(parts) == 3:
                        feed_name = parts[0].strip()
                        acronym = parts[1].strip()
                        url = parts[2].strip()
                        feeds[feed_name] = {'url': url, 'acronym': acronym}
                    elif len(parts) == 2:
                        feed_name = parts[0].strip()
                        url = parts[1].strip()
                        acronym = feed_name.split(' ')[0] if ' ' in feed_name else feed_name
                        feeds[feed_name] = {'url': url, 'acronym': acronym}
        
        print('✓ Loaded ' + str(len(feeds)) + ' RSS feeds')
        return feeds
    except FileNotFoundError:
        print('⚠ feeds.txt not found - using minimal defaults')
        return {
            'ET Markets': {'url': 'https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms', 'acronym': 'ET'}
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
            {'name': 'OTHER NEWS', 'keywords': ['other', 'news']}
        ]
    except Exception as e:
        print('⚠ Error loading topics: ' + str(e))
        return [{'name': 'OTHER NEWS', 'keywords': ['other', 'news']}]

# ============================================
# ESCAPE MARKDOWN FOR LINK TITLES (MINIMAL)
# ============================================
def escape_markdown_title(text):
    """
    Escape only characters that break Telegram Markdown in link titles
    Only need to escape: ] and \
    """
    text = text.replace('\\', '\\\\')  # Escape backslashes first
    text = text.replace(']', '\\]')    # Escape closing brackets
    return text

# ============================================
# CATEGORIZE ARTICLE BY TOPIC
# ============================================
def categorize_article(title, description, topics):
    """Categorize article using scoring"""
    text = (title + ' ' + str(description)).lower()
    
    topic_scores = {}
    
    for topic in topics:
        score = 0
        for keyword in topic['keywords']:
            if keyword in text:
                score += 1
        
        if score > 0:
            topic_scores[topic['name']] = score
    
    if topic_scores:
        best_topic = max(topic_scores, key=topic_scores.get)
        return best_topic
    
    return 'OTHER NEWS'

# ============================================
# FREE TRENDING DETECTION (MINIMAL PATTERNS)
# ============================================
def identify_trending_topics_free(articles, top_n=5):
    """
    Identify trending topics by clustering articles into news themes
    Uses minimal patterns for current events (not duplicating keywords.txt)
    """
    
    if len(articles) < 10:
        return []
    
    # Get current quarter dynamically
    current_month = datetime.now().month
    if 1 <= current_month <= 3:
        quarter = 'Q4'
        quarter_patterns = ['q4', 'fourth quarter', 'results', 'earnings']
    elif 4 <= current_month <= 6:
        quarter = 'Q1'
        quarter_patterns = ['q1', 'first quarter', 'results', 'earnings']
    elif 7 <= current_month <= 9:
        quarter = 'Q2'
        quarter_patterns = ['q2', 'second quarter', 'results', 'earnings']
    else:
        quarter = 'Q3'
        quarter_patterns = ['q3', 'third quarter', 'results', 'earnings']
    
    # Minimal news theme patterns (these are EVENT THEMES, not keywords)
    trending_themes = {
        'Trade and Tariffs': [
            'tariff', 'bilateral trade', 'trade deal', 'trade war', 
            'export', 'import', 'trade agreement'
        ],
        quarter + ' Earnings': quarter_patterns + [
            'profit', 'revenue', 'quarterly', 'beat estimates', 'miss estimates'
        ],
        'Rate Decisions': [
            'rate cut', 'rate hike', 'repo rate', 'policy rate', 
            'monetary policy', 'interest rate decision'
        ],
        'IPO and Listings': [
            'ipo', 'listing', 'issue price', 'subscription', 
            'grey market premium', 'allotment'
        ],
        'Mergers and Deals': [
            'merger', 'acquisition', 'm&a', 'stake sale', 
            'buyout', 'takeover'
        ],
        'Regulatory Actions': [
            'sebi action', 'irdai guideline', 'rbi circular', 
            'penalty', 'enforcement', 'investigation'
        ],
    }
    
    # Cluster articles by theme
    theme_clusters = defaultdict(list)
    
    for article in articles:
        text = article['title'].lower()
        
        # Find best matching theme
        best_theme = None
        max_matches = 0
        
        for theme_name, patterns in trending_themes.items():
            matches = sum(1 for pattern in patterns if pattern in text)
            if matches > max_matches:
                max_matches = matches
                best_theme = theme_name
        
        if best_theme and max_matches > 0:
            theme_clusters[best_theme].append(article)
    
    # Build trending list
    trending = []
    for theme_name, cluster_articles in theme_clusters.items():
        if len(cluster_articles) >= 5:  # Minimum 5 articles to be "trending"
            summary = generate_free_summary(theme_name, cluster_articles[:5])
            
            trending.append({
                'topic': theme_name,
                'count': len(cluster_articles),
                'articles': cluster_articles,
                'summary': summary
            })
    
    # Sort by article count (most covered first)
    trending.sort(key=lambda x: x['count'], reverse=True)
    
    return trending[:top_n]

# ============================================
# GENERATE FREE SUMMARY
# ============================================
def generate_free_summary(topic_name, articles):
    """
    Generate summary from article titles (no API needed)
    """
    
    if not articles:
        return 'Multiple developments reported.'
    
    # Extract key information from titles
    summary_parts = []
    
    for article in articles[:3]:  # Use top 3 articles
        title = article['title']
        
        # Clean and shorten title for summary
        cleaned = title
        for prefix in ['Exclusive:', 'Breaking:', 'Opinion:', 'Analysis:', 'Update:']:
            cleaned = cleaned.replace(prefix, '').strip()
        
        # Shorten if needed
        if len(cleaned) > 70:
            # Try to cut at sentence boundary
            if '.' in cleaned[:70]:
                cleaned = cleaned[:cleaned[:70].rindex('.')] + '.'
            elif ',' in cleaned[:70]:
                cleaned = cleaned[:cleaned[:70].rindex(',')] + '...'
            else:
                cleaned = cleaned[:67] + '...'
        
        summary_parts.append(cleaned)
    
    # Join with bullet points
    summary = ' • '.join(summary_parts)
    
    return summary

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

for feed_name, feed_info in feeds.items():
    try:
        url = feed_info['url']
        acronym = feed_info['acronym']
        
        print('\n' + feed_name + ':')
        
        try:
            # CRITICAL: Use User-Agent header to avoid being blocked
            feed = feedparser.parse(url, request_headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
        except socket.timeout:
            print('  ⏱️  TIMEOUT - Skipping')
            feed_stats[feed_name] = {'total': 0, 'recent': 0, 'relevant': 0}
            continue
        except Exception as e:
            print('  ❌ Error: ' + str(e)[:50])
            feed_stats[feed_name] = {'total': 0, 'recent': 0, 'relevant': 0}
            continue
        
        total_entries = len(feed.entries)
        print('  Total entries: ' + str(total_entries))
        
        if not feed.entries:
            print('  No entries found')
            feed_stats[feed_name] = {'total': 0, 'recent': 0, 'relevant': 0}
            continue
        
        recent_count = 0
        source_count = 0
        
        for entry in feed.entries[:100]:
            try:
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        pub_date = datetime(*entry.published_parsed[:6])
                    except:
                        pass
                
                # CRITICAL: Use 48-hour window (2 days) to match validator
                if pub_date:
                    age_hours = (datetime.now() - pub_date).total_seconds() / 3600
                    if age_hours <= 48:  # 48 hour window
                        recent_count += 1
                    else:
                        continue  # Skip old articles
                else:
                    # No date - assume recent (same as validator)
                    recent_count += 1
                
                title = entry.get('title', '').strip()
                description = entry.get('summary', '') or entry.get('description', '')
                link = entry.get('link', '').strip()
                
                if not title or not link:
                    continue
                
                if link in seen_urls:
                    continue
                
                # Keyword matching (same as validator)
                text = (title + ' ' + str(description)).lower()
                is_relevant = any(kw in text for kw in keywords)
                
                if is_relevant:
                    seen_urls.add(link)
                    time_str = pub_date.strftime('%H:%M') if pub_date else 'Recent'
                    
                    topic = categorize_article(title, description, topics)
                    
                    articles.append({
                        'source': feed_name,
                        'publication': acronym,
                        'title': title,
                        'url': link,
                        'time': time_str,
                        'date': pub_date or datetime.now(),
                        'topic': topic,
                        'description': description
                    })
                    
                    source_count += 1
                        
            except Exception as e:
                continue
        
        feed_stats[feed_name] = {
            'total': total_entries,
            'recent': recent_count,
            'relevant': source_count
        }
        
        print('  Recent (48hrs): ' + str(recent_count))
        print('  Relevant: ' + str(source_count))
        
    except Exception as e:
        print('  ❌ Error: ' + str(e)[:50])
        feed_stats[feed_name] = {'total': 0, 'recent': 0, 'relevant': 0}
        continue

# ============================================
# SUMMARY
# ============================================
print('\n' + '=' * 60)
print('SUMMARY BY PUBLICATION')
print('=' * 60)

all_publications = set()
for feed_name, feed_info in feeds.items():
    all_publications.add(feed_info['acronym'])

for pub in sorted(all_publications):
    pub_feeds = {k: v for k, v in feed_stats.items() if feeds.get(k, {}).get('acronym') == pub}
    if pub_feeds:
        total_rel = sum(f['relevant'] for f in pub_feeds.values())
        print(pub + ': ' + str(total_rel) + ' articles from ' + str(len(pub_feeds)) + ' feeds')

print('\nTotal unique articles: ' + str(len(articles)))

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
# IDENTIFY TRENDING TOPICS (FREE)
# ============================================
trending_topics = []

if len(articles) >= MIN_ARTICLES_FOR_TRENDING:
    print('\n' + '=' * 60)
    print('IDENTIFYING TRENDING TOPICS')
    print('=' * 60)
    print(f'Articles available: {len(articles)} (min: {MIN_ARTICLES_FOR_TRENDING})')
    
    trending_topics = identify_trending_topics_free(articles, top_n=MAX_TRENDING_TOPICS)
    
    if trending_topics:
        print(f'\n✓ Found {len(trending_topics)} trending topics:')
        for i, trending in enumerate(trending_topics, 1):
            print(f"  {i}. {trending['topic']}: {trending['count']} articles")
        print('\n✅ Trending analysis complete (100% FREE)')
    else:
        print('\n⚠️  No significant trending topics identified (need 5+ articles per theme)')
else:
    print(f'\n⚠️  Trending detection: SKIPPED (only {len(articles)} articles, need {MIN_ARTICLES_FOR_TRENDING}+)')

print('=' * 60)

# ============================================
# BUILD TELEGRAM MESSAGE
# ============================================
if not articles:
    msg = '*Financial News Digest*\n' + datetime.now().strftime('%B %d, %Y') + '\n\nNo relevant articles found today.'
    messages = [msg]
else:
    articles.sort(key=lambda x: x['date'], reverse=True)
    
    by_topic = defaultdict(lambda: defaultdict(list))
    for article in articles:
        by_topic[article['topic']][article['publication']].append(article)
    
    messages = []
    
    # HEADER MESSAGE (always separate)
    header_msg = '*Financial News Digest*\n'
    header_msg = header_msg + datetime.now().strftime('%B %d, %Y') + '\n\n'
    
    total_articles = len(articles)
    all_pubs = set(article['publication'] for article in articles)
    
    header_msg = header_msg + str(total_articles) + ' articles from ' + str(len(all_pubs)) + ' publications\n'
    header_msg = header_msg + '━━━━━━━━━━━━━━━━━\n\n'
    
    # Add trending section to header if available
    if trending_topics:
        header_msg = header_msg + '*🔥 TRENDING TODAY*\n\n'
        
        for trending in trending_topics:
            header_msg = header_msg + '*' + trending['topic'] + '* (' + str(trending['count']) + ' articles)\n'
            header_msg = header_msg + trending['summary'] + '\n\n'
        
        header_msg = header_msg + '━━━━━━━━━━━━━━━━━\n\n'
    
    messages.append(header_msg)
    
    # Build content messages (iterate topics in order from topics.txt)
    current_msg = ''
    
    for topic_config in topics:
        topic_name = topic_config['name']
        
        if topic_name not in by_topic:
            continue
        
        publications_in_topic = by_topic[topic_name]
        
        if not publications_in_topic:
            continue
        
        # Build topic section
        topic_section = '*' + topic_name + '*\n\n'
        
        for pub_acronym in sorted(publications_in_topic.keys()):
            articles_from_pub = publications_in_topic[pub_acronym]
            
            if not articles_from_pub:
                continue
            
            articles_from_pub = sorted(articles_from_pub, key=lambda x: x['date'], reverse=True)
            
            pub_section = '_' + pub_acronym + '_\n'
            
            for i, article in enumerate(articles_from_pub, 1):
                title_short = article['title']
                
                if len(title_short) > 75:
                    title_short = title_short[:72] + '...'
                
                # Only escape ] and \ in link titles
                title_escaped = escape_markdown_title(title_short)
                
                article_line = str(i) + '. [' + title_escaped + '](' + article['url'] + ')\n'
                
                # Check if adding this article would exceed limit
                test_length = len(current_msg) + len(topic_section) + len(pub_section) + len(article_line)
                
                if test_length > 2500:  # Conservative 2500 char limit
                    # Save current message and start new one
                    if current_msg.strip():
                        messages.append(current_msg)
                    current_msg = topic_section + pub_section + article_line
                    topic_section = ''  # Don't repeat topic header
                else:
                    pub_section = pub_section + article_line
            
            # Check if adding publication section exceeds limit
            if len(current_msg) + len(topic_section) + len(pub_section) > 2500:
                # Save current message
                if current_msg.strip():
                    messages.append(current_msg)
                current_msg = topic_section + pub_section + '\n'
                topic_section = ''
            else:
                topic_section = topic_section + pub_section + '\n'
        
        # Add completed topic section to current message
        if len(current_msg) + len(topic_section) > 2500:
            if current_msg.strip():
                messages.append(current_msg)
            current_msg = topic_section
        else:
            current_msg = current_msg + topic_section
    
    # Add any remaining content
    if current_msg.strip():
        messages.append(current_msg)

print('\n📊 Split into ' + str(len(messages)) + ' messages')


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
                        # Print response for debugging
                        try:
                            print('  Response: ' + str(response.json()))
                        except:
                            pass
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
