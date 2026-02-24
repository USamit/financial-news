import os
from datetime import datetime, timedelta
import feedparser
import requests
from collections import defaultdict, Counter
import socket
import re

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
MIN_ARTICLES_FOR_TRENDING = 50
MAX_TRENDING_TOPICS = 10

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
        print('⚠ feeds.txt not found')
        return {}
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
# ESCAPE MARKDOWN
# ============================================
def escape_markdown_title(text):
    """Escape only ] and \ for Telegram Markdown"""
    text = text.replace('\\', '\\\\')
    text = text.replace(']', '\\]')
    return text

# ============================================
# ADVANCED DEDUPLICATION
# ============================================
def extract_key_phrases(title):
    """
    Extract key phrases from title for better duplicate detection
    Returns set of important words and bigrams
    """
    # Stop words to ignore
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
        'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'could', 'should', 'may', 'might', 'can', 'says', 'said',
        'after', 'amid', 'over', 'up', 'down', 'out', 'its', 'new', 'this',
        'that', 'these', 'those', 'his', 'her', 'their', 'our', 'your'
    }
    
    # Clean and tokenize
    text = title.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    words = text.split()
    
    # Filter stop words and short words
    words = [w for w in words if w not in stop_words and len(w) > 2]
    
    # Create bigrams (two-word phrases)
    phrases = set(words)
    for i in range(len(words) - 1):
        bigram = words[i] + '_' + words[i + 1]
        phrases.add(bigram)
    
    return phrases

def is_duplicate_advanced(new_article, existing_articles):
    """
    Advanced duplicate detection using key phrase overlap
    Returns True if article is a duplicate
    """
    new_phrases = extract_key_phrases(new_article['title'])
    
    if len(new_phrases) < 3:  # Title too short to compare
        return False
    
    for existing in existing_articles:
        existing_phrases = extract_key_phrases(existing['title'])
        
        if len(existing_phrases) < 3:
            continue
        
        # Calculate overlap
        common = new_phrases.intersection(existing_phrases)
        union = new_phrases.union(existing_phrases)
        
        if len(union) == 0:
            continue
        
        # If 50%+ phrases are the same, it's a duplicate
        similarity = len(common) / len(union)
        
        if similarity >= 0.5:
            return True
    
    return False

# ============================================
# CATEGORIZE ARTICLE
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
# WORD CLOUD TRENDING DETECTION
# ============================================
def identify_trending_wordcloud(articles, top_n=5):
    """
    Identify trending topics using word cloud approach
    Extract most common phrases from article titles
    """
    
    if len(articles) < 50:
        return []
    
    print('  Analyzing article titles for trending phrases...')
    
    # Stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
        'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'could', 'should', 'may', 'might', 'can', 'says', 'said',
        'after', 'amid', 'over', 'up', 'down', 'out', 'its', 'new', 'this',
        'that', 'these', 'those'
    }
    
    # Extract all words and bigrams from titles
    word_counter = Counter()
    bigram_counter = Counter()
    trigram_counter = Counter()
    
    for article in articles:
        title = article['title'].lower()
        title = re.sub(r'[^\w\s]', ' ', title)
        words = title.split()
        words = [w for w in words if w not in stop_words and len(w) > 3]
        
        # Count words
        word_counter.update(words)
        
        # Count bigrams
        for i in range(len(words) - 1):
            bigram = words[i] + ' ' + words[i + 1]
            bigram_counter[bigram] += 1
        
        # Count trigrams
        for i in range(len(words) - 2):
            trigram = words[i] + ' ' + words[i + 1] + ' ' + words[i + 2]
            trigram_counter[trigram] += 1
    
    # Find top phrases (prefer longer phrases)
    top_phrases = []
    
    # Get top trigrams (3-word phrases)
    for phrase, count in trigram_counter.most_common(20):
        if count >= 3:  # At least 3 articles
            top_phrases.append({'phrase': phrase, 'count': count, 'type': 'trigram'})
    
    # Get top bigrams (2-word phrases)
    for phrase, count in bigram_counter.most_common(30):
        if count >= 5:  # At least 5 articles
            # Don't add if already part of a trigram
            is_subset = False
            for existing in top_phrases:
                if phrase in existing['phrase']:
                    is_subset = True
                    break
            if not is_subset:
                top_phrases.append({'phrase': phrase, 'count': count, 'type': 'bigram'})
    
    # Sort by count
    top_phrases.sort(key=lambda x: x['count'], reverse=True)
    
    # Take top N
    top_phrases = top_phrases[:top_n]
    
    print(f'  Found {len(top_phrases)} trending phrases')
    
    # For each trending phrase, find matching articles and create summary
    trending_results = []
    
    for phrase_data in top_phrases:
        phrase = phrase_data['phrase']
        
        # Find articles containing this phrase
        matching_articles = []
        for article in articles:
            if phrase in article['title'].lower():
                matching_articles.append(article)
        
        if len(matching_articles) >= 3:
            # Generate summary from top 3 article titles
            summary_titles = []
            for article in matching_articles[:3]:
                title = article['title']
                # Clean title
                for prefix in ['Exclusive:', 'Breaking:', 'Opinion:', 'Analysis:']:
                    title = title.replace(prefix, '').strip()
                if len(title) > 80:
                    title = title[:77] + '...'
                summary_titles.append(title)
            
            summary = ' • '.join(summary_titles)
            
            trending_results.append({
                'topic': phrase.title(),
                'count': len(matching_articles),
                'summary': summary
            })
    
    return trending_results

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
duplicate_count = 0

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
        feed_duplicates = 0
        
        for entry in feed.entries[:100]:
            try:
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        pub_date = datetime(*entry.published_parsed[:6])
                    except:
                        pass
                
                if pub_date:
                    age_hours = (datetime.now() - pub_date).total_seconds() / 3600
                    if age_hours <= 48:
                        recent_count += 1
                    else:
                        continue
                else:
                    recent_count += 1
                
                title = entry.get('title', '').strip()
                description = entry.get('summary', '') or entry.get('description', '')
                link = entry.get('link', '').strip()
                
                if not title or not link:
                    continue
                
                if link in seen_urls:
                    continue
                
                text = (title + ' ' + str(description)).lower()
                is_relevant = any(kw in text for kw in keywords)
                
                if is_relevant:
                    seen_urls.add(link)
                    time_str = pub_date.strftime('%H:%M') if pub_date else 'Recent'
                    
                    topic = categorize_article(title, description, topics)
                    
                    new_article = {
                        'source': feed_name,
                        'publication': acronym,
                        'title': title,
                        'url': link,
                        'time': time_str,
                        'date': pub_date or datetime.now(),
                        'topic': topic,
                        'description': description
                    }
                    
                    # Advanced deduplication
                    if not is_duplicate_advanced(new_article, articles):
                        articles.append(new_article)
                        source_count += 1
                    else:
                        feed_duplicates += 1
                        duplicate_count += 1
                        
            except Exception as e:
                continue
        
        feed_stats[feed_name] = {
            'total': total_entries,
            'recent': recent_count,
            'relevant': source_count
        }
        
        print('  Recent (48hrs): ' + str(recent_count))
        print('  Relevant: ' + str(source_count))
        if feed_duplicates > 0:
            print('  Duplicates skipped: ' + str(feed_duplicates))
        
    except Exception as e:
        print('  ❌ Error: ' + str(e)[:50])
        feed_stats[feed_name] = {'total': 0, 'recent': 0, 'relevant': 0}
        continue

# ============================================
# DEDUPLICATION SUMMARY
# ============================================
print('\n' + '=' * 60)
print('DEDUPLICATION SUMMARY')
print('=' * 60)

total_before_dedup = len(articles) + duplicate_count
dedup_percentage = (duplicate_count / total_before_dedup * 100) if total_before_dedup > 0 else 0

print(f'Articles before deduplication: {total_before_dedup}')
print(f'Duplicates removed: {duplicate_count}')
print(f'Unique articles remaining: {len(articles)}')
print(f'Reduction: {dedup_percentage:.1f}%')

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
# WORD CLOUD TRENDING DETECTION
# ============================================
trending_topics = []

if len(articles) >= MIN_ARTICLES_FOR_TRENDING:
    print('\n' + '=' * 60)
    print('IDENTIFYING TRENDING TOPICS (WORD CLOUD)')
    print('=' * 60)
    print(f'Articles available: {len(articles)}')
    
    trending_topics = identify_trending_wordcloud(articles, top_n=MAX_TRENDING_TOPICS)
    
    if trending_topics:
        print(f'\n✓ Found {len(trending_topics)} trending topics:')
        for i, trending in enumerate(trending_topics, 1):
            print(f"  {i}. {trending['topic']}: {trending['count']} articles")
        print('\n✅ Trending analysis complete (WORD CLOUD)')
    else:
        print('\n⚠️  No significant trending topics found')
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
    
    # HEADER MESSAGE
    header_msg = '*Financial News Digest*\n'
    header_msg = header_msg + datetime.now().strftime('%B %d, %Y') + '\n\n'
    
    total_articles = len(articles)
    all_pubs = set(article['publication'] for article in articles)
    
    header_msg = header_msg + str(total_articles) + ' articles from ' + str(len(all_pubs)) + ' publications\n'
    header_msg = header_msg + '━━━━━━━━━━━━━━━━━\n\n'
    
    # Add trending section
    if trending_topics:
        header_msg = header_msg + '*🔥 TRENDING TODAY*\n\n'
        
        for trending in trending_topics:
            header_msg = header_msg + '*' + trending['topic'] + '* (' + str(trending['count']) + ' articles)\n'
            header_msg = header_msg + trending['summary'] + '\n\n'
        
        header_msg = header_msg + '━━━━━━━━━━━━━━━━━\n\n'
    
    messages.append(header_msg)
    
    # Build content messages
    current_msg = ''
    
    for topic_config in topics:
        topic_name = topic_config['name']
        
        if topic_name not in by_topic:
            continue
        
        publications_in_topic = by_topic[topic_name]
        
        if not publications_in_topic:
            continue
        
        topic_header = '*' + topic_name + '*\n\n'
        
        if current_msg and len(current_msg) + len(topic_header) > 2500:
            messages.append(current_msg)
            current_msg = ''
        
        current_msg = current_msg + topic_header
        
        for pub_acronym in sorted(publications_in_topic.keys()):
            articles_from_pub = publications_in_topic[pub_acronym]
            
            if not articles_from_pub:
                continue
            
            articles_from_pub = sorted(articles_from_pub, key=lambda x: x['date'], reverse=True)
            
            pub_header = '_' + pub_acronym + '_\n'
            
            if len(current_msg) + len(pub_header) > 2500:
                messages.append(current_msg)
                current_msg = topic_header + pub_header
            else:
                current_msg = current_msg + pub_header
            
            for i, article in enumerate(articles_from_pub, 1):
                title_short = article['title']
                
                if len(title_short) > 75:
                    title_short = title_short[:72] + '...'
                
                title_escaped = escape_markdown_title(title_short)
                
                article_line = str(i) + '. [' + title_escaped + '](' + article['url'] + ')\n'
                
                if len(current_msg) + len(article_line) > 2500:
                    messages.append(current_msg)
                    current_msg = topic_header + pub_header + article_line
                else:
                    current_msg = current_msg + article_line
            
            current_msg = current_msg + '\n'
    
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
