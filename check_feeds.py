import os

print('=' * 60)
print('CHECKING FEEDS.TXT')
print('=' * 60)

# Check if file exists
if not os.path.exists('feeds.txt'):
    print('❌ feeds.txt does NOT exist!')
    exit(1)

print('✅ feeds.txt exists')

# Check modification time
import datetime
mod_time = datetime.datetime.fromtimestamp(os.path.getmtime('feeds.txt'))
print(f'Last modified: {mod_time}')

age_hours = (datetime.datetime.now() - mod_time).total_seconds() / 3600
print(f'Age: {age_hours:.1f} hours ago')

# Read BS feeds
print('\n' + '=' * 60)
print('BS FEEDS IN feeds.txt:')
print('=' * 60)

bs_count = 0
with open('feeds.txt', 'r') as f:
    for line_num, line in enumerate(f, 1):
        line = line.strip()
        if '|BS|' in line:
            bs_count += 1
            parts = line.split('|')
            if len(parts) == 3:
                print(f'\n{bs_count}. {parts[0]}')
                print(f'   URL: {parts[2]}')

if bs_count == 0:
    print('\n❌ NO BS FEEDS FOUND IN feeds.txt!')
else:
    print(f'\n✅ Found {bs_count} BS feeds')

print('=' * 60)
