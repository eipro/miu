import requests
from bs4 import BeautifulSoup
import re
import os
import base64
import time
import json
import ipaddress
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# --- تنظیمات پیشرفته ---

# لیست سیاه کشورها
BLOCKED_COUNTRIES = ['IR', 'CN', 'RU', 'KP']

# حداکثر تعداد کانفیگ از هر کشور (برای جلوگیری از سنگین شدن)
MAX_CONFIGS_PER_COUNTRY = 50

# فیلتر زمانی (بر اساس ساعت) - فقط پیام‌های ۴۸ ساعت اخیر
TIME_LIMIT_HOURS = 48

# پروتکل‌های مورد نظر
PREFIXES = ('vless://', 'vmess://', 'trojan://', 'ss://', 'hysteria2://', 'tuic://')

# فایل‌های خروجی
OUTPUT_FILE = "filtered_configs.txt"
README_FILE = "README.md"
HTML_FILE = "index.html"

# --- توابع کمکی ---

def load_channels():
    channel_list = []
    if os.path.exists('channels.txt'):
        with open('channels.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    channel_list.append(line)
    return channel_list

def get_ip_info(ip):
    """دریافت نام کشور و نام ISP"""
    try:
        # استفاده از API که ISP را هم برگرداند
        response = requests.get(f"http://ip-api.com/json/{ip}?fields=countryCode,isp,org", timeout=3)
        if response.status_code == 200:
            data = response.json()
            country = data.get('countryCode', '')
            # تلاش برای گرفتن نام دیتاسنتر تمیز
            isp = data.get('isp', '') or data.get('org', '')
            
            # تمیز کردن نام ISP های طولانی
            if isp:
                isp = isp.split(',')[0].split(' ')[0] # فقط کلمه اول (مثلا Hetzner)
                if len(isp) > 10: isp = isp[:10]
            
            return country, isp
    except:
        pass
    return "", ""

def get_flag_emoji(country_code):
    if not country_code: return "🏳️"
    return ''.join([chr(ord(c) + 127397) for c in country_code.upper()])

def is_valid_ip(ip):
    try:
        ip_obj = ipaddress.ip_address(ip)
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved:
            return False
        return True
    except ValueError:
        return True # دامین است

def is_recent_message(msg_soup):
    """بررسی تاریخ پیام"""
    try:
        time_tag = msg_soup.find('time')
        if time_tag and 'datetime' in time_tag.attrs:
            msg_time_str = time_tag['datetime']
            # فرمت تلگرام: 2023-10-27T10:00:00+00:00
            # حذف بخش منطقه زمانی برای مقایسه ساده
            msg_time_str = msg_time_str.split('+')[0]
            msg_time = datetime.fromisoformat(msg_time_str)
            
            if datetime.utcnow() - msg_time < timedelta(hours=TIME_LIMIT_HOURS):
                return True
            return False
    except:
        pass
    return True # اگر تاریخ پیدا نشد، پیش‌فرض قبول کن

def is_reality(config):
    """تشخیص Reality بودن"""
    if 'security=reality' in config or 'pbk=' in config or 'fp=' in config:
        return True
    return False

def rename_config(config, new_name, protocol):
    """تغییر نام کانفیگ با پشتیبانی از VMess"""
    try:
        if protocol == 'vmess':
            # دیکد کردن VMess
            b64_part = config.replace('vmess://', '')
            # تصحیح پدینگ
            missing_padding = len(b64_part) % 4
            if missing_padding:
                b64_part += '=' * (4 - missing_padding)
            
            json_str = base64.b64decode(b64_part).decode('utf-8')
            data = json.loads(json_str)
            
            # تغییر نام
            data['ps'] = new_name
            
            # اینکد دوباره
            new_json = json.dumps(data)
            new_b64 = base64.b64encode(new_json.encode('utf-8')).decode('utf-8')
            return f"vmess://{new_b64}"
            
        else:
            # برای سایر پروتکل‌ها (VLESS, Trojan, etc.)
            # ساختار URL را پارس می‌کنیم تا هش (نام) را عوض کنیم
            if '#' in config:
                base_config = config.split('#')[0]
                return f"{base_config}#{new_name}"
            else:
                return f"{config}#{new_name}"
    except Exception as e:
        # اگر مشکلی پیش آمد، همان قبلی را برگردان
        return config

def parse_config_details(config):
    """استخراج جزئیات برای جدول HTML"""
    protocol = config.split('://')[0]
    
    # برای VMess باید دیکد کنیم تا پورت و آدرس را بگیریم
    if protocol == 'vmess':
        try:
            b64 = config.replace('vmess://', '')
            missing_padding = len(b64) % 4
            if missing_padding: b64 += '=' * (4 - missing_padding)
            data = json.loads(base64.b64decode(b64).decode('utf-8'))
            return protocol, data.get('add', 'Unknown'), data.get('port', '0')
        except:
            return protocol, 'Unknown', '0'
    else:
        # برای بقیه (VLESS, URL-based)
        pattern = r'@([^:]+):(\d+)'
        match = re.search(pattern, config)
        if match:
            return protocol, match.group(1), match.group(2)
        return protocol, 'Unknown', '0'

def generate_html(configs):
    """تولید فایل index.html"""
    rows = ""
    for idx, c in enumerate(configs):
        # c = (sort_key, final_config, details_dict)
        details = c[2]
        link = c[1]
        
        rows += f"""
        <tr>
            <td>{idx + 1}</td>
            <td>{details['flag']}</td>
            <td>{details['country']}</td>
            <td>{details['isp']}</td>
            <td><span class="badge {details['protocol']}">{details['protocol']}</span></td>
            <td>{details['port']} {details['features']}</td>
            <td>
                <button class="btn-copy" onclick="copyToClipboard('{link}')">Copy</button>
            </td>
        </tr>
        """
        
    html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Professional Proxy List</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #121212; color: #e0e0e0; margin: 0; padding: 20px; }}
        h1 {{ text-align: center; color: #4CAF50; }}
        .container {{ max-width: 1200px; margin: 0 auto; overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; background-color: #1e1e1e; border-radius: 8px; overflow: hidden; }}
        th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #333; }}
        th {{ background-color: #2c2c2c; color: #4CAF50; }}
        tr:hover {{ background-color: #252525; }}
        .btn-copy {{ background-color: #2196F3; color: white; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer; transition: 0.3s; }}
        .btn-copy:hover {{ background-color: #0b7dda; }}
        .badge {{ padding: 3px 8px; border-radius: 12px; font-size: 0.8em; font-weight: bold; color: white; }}
        .badge.vless {{ background-color: #9c27b0; }}
        .badge.vmess {{ background-color: #e91e63; }}
        .badge.trojan {{ background-color: #ff9800; }}
        .badge.ss {{ background-color: #607d8b; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎒 Proxy Collector Dashboard</h1>
        <p style="text-align: center;">Total Active Configs: {len(configs)} | Last Update: {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}</p>
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Flag</th>
                    <th>Country</th>
                    <th>ISP</th>
                    <th>Protocol</th>
                    <th>Port/Tags</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </div>
    <script>
        function copyToClipboard(text) {{
            navigator.clipboard.writeText(text).then(() => {{
                alert('Config copied to clipboard!');
            }});
        }}
    </script>
</body>
</html>
    """
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html_template)

# --- تابع اصلی ---

def fetch_configs():
    channels = load_channels()
    if not channels: return

    raw_configs = []
    seen_identifiers = set()
    
    # ساختار ذخیره‌سازی: list of tuples (sort_key, final_config, details_dict)
    all_processed_configs = []
    
    # شمارنده برای محدودیت کشور
    country_counter = {}

    headers = {'User-Agent': 'Mozilla/5.0 ... Chrome/91.0'} # (خلاصه شده)

    # 1. جمع‌آوری
    print(f"📥 Scraping {len(channels)} channels (Last {TIME_LIMIT_HOURS}h)...")
    for url in channels:
        username = url.split('/')[-1]
        try:
            response = requests.get(f"https://t.me/s/{username}", headers=headers, timeout=10)
            if response.status_code != 200: continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            # پیدا کردن باکس‌های پیام
            msg_wraps = soup.select('.tgme_widget_message_wrap')
            
            for wrap in msg_wraps:
                # چک کردن تاریخ پیام
                if not is_recent_message(wrap):
                    continue

                msg_text_div = wrap.select_one('.tgme_widget_message_text')
                if not msg_text_div: continue

                # اصلاح خطوط
                for br in msg_text_div.find_all("br"): br.replace_with("\n")
                lines = msg_text_div.get_text().split('\n')
                
                for line in lines:
                    clean_line = line.strip()
                    if clean_line.startswith(PREFIXES):
                         # حذف نام قدیمی (در غیر VMess)
                        if not clean_line.startswith('vmess://') and '#' in clean_line:
                            clean_line = clean_line.split('#')[0]
                        raw_configs.append(clean_line)
                        
        except Exception as e:
            print(f"Error scraping {username}: {e}")

    print(f"✅ Found {len(raw_configs)} recent configs. Processing...")

    # 2. پردازش
    global_counter = 1
    
    for config in raw_configs:
        protocol, ip, port = parse_config_details(config)
        
        if not ip or not port: continue
        if not is_valid_ip(ip): continue
        
        identifier = f"{ip}:{port}"
        if identifier in seen_identifiers: continue
        seen_identifiers.add(identifier)
        
        print(f"Processing {protocol.upper()} {ip}...", end="\r")
        
        country, isp = get_ip_info(ip)
        
        # فیلتر لیست سیاه
        if country in BLOCKED_COUNTRIES: continue
        
        # فیلتر محدودیت تعداد
        current_count = country_counter.get(country, 0)
        if current_count >= MAX_CONFIGS_PER_COUNTRY: continue
        country_counter[country] = current_count + 1
        
        flag = get_flag_emoji(country)
        
        # تگ‌های ویژگی‌ها
        features = ""
        if protocol == 'vless' and is_reality(config):
            features += "⚡Reality "
        if str(port) == '443':
            features += "🔒 "
        
        # نام‌گذاری جدید: 🇩🇪 Hetzner-1 ⚡
        base_name = f"{flag} {isp} {global_counter}"
        if features: base_name += f" {features.strip()}"
        
        final_config = rename_config(config, base_name, protocol)
        
        # ذخیره اطلاعات
        details = {
            'flag': flag,
            'country': country if country else 'Unknown',
            'isp': isp if isp else 'Unknown',
            'protocol': protocol,
            'port': port,
            'features': features
        }
        
        # کلید مرتب‌سازی: اول کشور، بعد پروتکل
        sort_key = (country if country else "ZZZ") + protocol
        all_processed_configs.append((sort_key, final_config, details))
        
        global_counter += 1
        time.sleep(0.3) # برای جلوگیری از بن شدن IP API

    # 3. مرتب‌سازی و خروجی
    all_processed_configs.sort(key=lambda x: x[0])
    
    # تولید فایل کلی
    final_string = "\n".join([item[1] for item in all_processed_configs])
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(base64.b64encode(final_string.encode('utf-8')).decode('utf-8'))
        
    # تولید فایل‌های جداگانه
    protocols = set(x[2]['protocol'] for x in all_processed_configs)
    for proto in protocols:
        subset = [x[1] for x in all_processed_configs if x[2]['protocol'] == proto]
        with open(f"{proto}.txt", "w", encoding="utf-8") as f:
            f.write(base64.b64encode("\n".join(subset).encode('utf-8')).decode('utf-8'))
            
    # تولید HTML
    generate_html(all_processed_configs)
    
    # آپدیت README (ساده)
    with open(README_FILE, "w") as f:
        f.write(f"# 🎒 Proxy Collector\nUpdated: {datetime.utcnow()}\nTotal: {len(all_processed_configs)}\n\nCheck [index.html](index.html) for details.")

    print(f"\n\n🎉 Done! Total: {len(all_processed_configs)}")

if __name__ == "__main__":
    fetch_configs()
