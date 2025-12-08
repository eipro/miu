import requests
from bs4 import BeautifulSoup
import re
import os
import base64
import time
import ipaddress
from datetime import datetime

# --- تنظیمات ---

# کشورهایی که نمی‌خواهیم در لیست باشند (لیست سیاه)
BLOCKED_COUNTRIES = ['IR', 'CN', 'RU', 'KP'] 

# پروتکل‌های مورد نظر
PREFIXES = ('vless://', 'trojan://', 'ss://', 'hysteria2://', 'tuic://')

# فایل‌های خروجی
OUTPUT_FILE = "filtered_configs.txt"
README_FILE = "README.md"

def load_channels():
    """خواندن لیست کانال‌ها از فایل متنی"""
    channel_list = []
    if os.path.exists('channels.txt'):
        with open('channels.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    channel_list.append(line)
    return channel_list

def extract_username(url):
    return url.split('/')[-1]

def get_flag_emoji(country_code):
    if not country_code:
        return "🏳️"
    return ''.join([chr(ord(c) + 127397) for c in country_code.upper()])

def get_ip_info(ip):
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}?fields=countryCode", timeout=3)
        if response.status_code == 200:
            data = response.json()
            return data.get('countryCode', '')
    except:
        pass
    return ""

def is_valid_ip(ip):
    try:
        ip_obj = ipaddress.ip_address(ip)
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved:
            return False
        return True
    except ValueError:
        return True

def parse_config(config):
    """استخراج پروتکل، IP و Port"""
    pattern = r'(vless|trojan|ss|hysteria2|tuic)://[^@]+@([^:]+):(\d+)'
    match = re.search(pattern, config)
    if match:
        return match.group(1), match.group(2), int(match.group(3))
    return None, None, None

def update_readme(stats, total_count):
    """بروزرسانی فایل README با آمار جدید"""
    date_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    readme_content = f"""# 🎒 Proxy Collector
Auto-updated proxy subscription links.

**Last Update:** `{date_str}`
**Total Configs:** `{total_count}`

## 📂 Subscriptions
| Protocol | Filename (Base64) |
|----------|-------------------|
| **All** | `filtered_configs.txt` |
| VLESS    | `vless.txt` |
| Trojan   | `trojan.txt` |
| SS       | `ss.txt` |

## 📊 Country Stats
| Flag | Country | Count |
|------|---------|-------|
"""
    
    # مرتب‌سازی کشورها بر اساس تعداد
    sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)
    
    for country, count in sorted_stats:
        flag = get_flag_emoji(country)
        country_name = country if country else "Unknown"
        readme_content += f"| {flag} | {country_name} | {count} |\n"

    with open(README_FILE, "w", encoding="utf-8") as f:
        f.write(readme_content)

def fetch_configs():
    channels = load_channels()
    if not channels:
        print("❌ No channels found in channels.txt")
        return

    raw_configs = []
    seen_identifiers = set()
    
    # دیکشنری برای تفکیک پروتکل‌ها
    protocol_configs = {
        'vless': [],
        'trojan': [],
        'ss': [],
        'hysteria2': [],
        'tuic': []
    }
    
    # لیست نهایی برای همه کانفیگ‌ها
    all_final_configs = []
    
    # آمار کشورها
    country_stats = {}

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # 1. جمع‌آوری
    print(f"📥 Scraping {len(channels)} channels...")
    for url in channels:
        username = extract_username(url)
        try:
            response = requests.get(f"https://t.me/s/{username}", headers=headers, timeout=10)
            if response.status_code != 200: continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            messages = soup.select('.tgme_widget_message_text')
            
            for msg in messages:
                for br in msg.find_all("br"): br.replace_with("\n")
                lines = msg.get_text().split('\n')
                for line in lines:
                    clean_line = line.strip()
                    if clean_line.startswith(PREFIXES):
                        if '#' in clean_line:
                            clean_line = clean_line.split('#')[0]
                        raw_configs.append(clean_line)
        except Exception as e:
            print(f"Error scraping {username}: {e}")

    print(f"✅ Scraped {len(raw_configs)} raw configs. Processing...")

    # 2. پردازش
    config_count = 1
    
    for config in raw_configs:
        protocol, ip, port = parse_config(config)
        
        if not ip or not port: continue
        if not is_valid_ip(ip): continue
        
        identifier = f"{ip}:{port}"
        if identifier in seen_identifiers: continue
        seen_identifiers.add(identifier)
        
        print(f"Processing {ip}:{port}...", end="\r")
        
        country_code = get_ip_info(ip)
        
        # فیلتر کشور (بلاک لیست)
        if country_code in BLOCKED_COUNTRIES:
            continue
            
        flag = get_flag_emoji(country_code)
        
        # آپدیت آمار
        stats_key = country_code if country_code else "Unknown"
        country_stats[stats_key] = country_stats.get(stats_key, 0) + 1
        
        # نام‌گذاری
        new_name = f"{flag} Config-{config_count}"
        final_config = f"{config}#{new_name}"
        
        # اضافه کردن به لیست کلی
        # برای مرتب‌سازی، تاپل (کشور, متن) ذخیره می‌کنیم
        sort_key = country_code if country_code else "ZZZ"
        all_final_configs.append((sort_key, final_config))
        
        # اضافه کردن به لیست تفکیک شده پروتکل
        if protocol in protocol_configs:
            protocol_configs[protocol].append(final_config)
        elif protocol == 'hysteria2' or protocol == 'tuic':
            # هیستریا و تویک رو فعلا میذاریم کنار بقیه یا فایل جدا اگر بخواید
            # اینجا فرض میکنیم فایل جدا ندارن یا میرن تو vless (دلخواه)
            pass

        config_count += 1
        time.sleep(0.5)

    # 3. ذخیره فایل کلی (مرتب شده)
    all_final_configs.sort(key=lambda x: x[0])
    final_string = "\n".join([item[1] for item in all_final_configs])
    
    if final_string:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(base64.b64encode(final_string.encode('utf-8')).decode('utf-8'))
    
    # 4. ذخیره فایل‌های جداگانه پروتکل‌ها
    for proto, confs in protocol_configs.items():
        if confs:
            content = "\n".join(confs)
            filename = f"{proto}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(base64.b64encode(content.encode('utf-8')).decode('utf-8'))

    # 5. آپدیت README
    update_readme(country_stats, len(all_final_configs))
    
    print(f"\n\n🎉 Done! Total unique configs: {len(all_final_configs)}")
    print("Files updated: filtered_configs.txt, vless.txt, trojan.txt, ss.txt, README.md")

if __name__ == "__main__":
    fetch_configs()
