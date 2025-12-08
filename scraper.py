import requests
from bs4 import BeautifulSoup
import re
import os
import base64
import time

# لیست کانال‌ها
channels = [
    'https://t.me/Alpha_V2ray_Group',
    'https://t.me/vpnplusee_free',
    'https://t.me/V2All0',
    'https://t.me/v2rayNG_Streisand',
    'https://t.me/v2ray_proxyz',
    'https://t.me/proxyirgp0',
    'https://t.me/NETMelliAnti',
    'https://t.me/prrofile_purple',
    'https://t.me/vpnz4',
    'https://t.me/Computerwormss',
    'https://t.me/v2rayngvpn',
    'https://t.me/vpnmasi_gp',
    'https://t.me/xy_su',
    'https://t.me/ServerNett',
    'https://t.me/Outline_Vpn',
    'https://t.me/vpnplusee',
    'https://t.me/FAST_configs',
    'https://t.me/NIM_VPN_ir',
    'https://t.me/TechnoTrendZone',
    'https://t.me/YamYamProxy',
    "https://t.me/ZAVI3H",
    'https://t.me/V2rayfastt',
    "https://t.me/s/v2rayfree",
    "https://t.me/s/PrivateVPNs",
    "https://t.me/s/prrofile_purple",
    "https://t.me/s/DirectVPN",
]

# پروتکل‌های مورد نظر
prefixes = ('vless://',)

def extract_username(url):
    return url.split('/')[-1]

def get_flag_emoji(country_code):
    """تبدیل کد دو حرفی کشور به ایموجی پرچم"""
    if not country_code:
        return "🏳️"
    return ''.join([chr(ord(c) + 127397) for c in country_code.upper()])

def get_ip_info(ip):
    """دریافت اطلاعات جغرافیایی IP"""
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}?fields=countryCode", timeout=3)
        if response.status_code == 200:
            data = response.json()
            return data.get('countryCode', '')
    except:
        pass
    return ""

def parse_vless(config):
    """استخراج IP و Port از کانفیگ VLESS برای تست و بررسی تکراری"""
    # فرمت معمول: vless://uuid@ip:port?params...
    pattern = r'vless://[^@]+@([^:]+):(\d+)'
    match = re.search(pattern, config)
    if match:
        return match.group(1), int(match.group(2))
    return None, None

def fetch_configs():
    raw_configs = []
    seen_identifiers = set() # برای حذف تکراری‌ها
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # 1. جمع‌آوری اولیه کانفیگ‌ها
    print("📥 Start scraping channels...")
    for url in channels:
        username = extract_username(url)
        
        try:
            response = requests.get(f"https://t.me/s/{username}", headers=headers, timeout=10)
            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            messages = soup.select('.tgme_widget_message_text')
            
            for msg in messages:
                for br in msg.find_all("br"):
                    br.replace_with("\n")
                
                text = msg.get_text()
                lines = text.split('\n')
                
                for line in lines:
                    clean_line = line.strip()
                    if clean_line.startswith(prefixes):
                        if '#' in clean_line:
                            clean_line = clean_line.split('#')[0]
                        raw_configs.append(clean_line)
            
        except Exception as e:
            print(f"Error scraping {username}: {e}")

    print(f"✅ Scraped {len(raw_configs)} raw configs. Starting processing...")

    # 2. پردازش کانفیگ‌ها (حذف تکراری، افزودن پرچم)
    final_configs = ""
    config_count = 1
    
    for config in raw_configs:
        ip, port = parse_vless(config)
        
        if not ip or not port:
            continue
            
        # شناسه یکتا برای حذف تکراری (IP:Port)
        identifier = f"{ip}:{port}"
        if identifier in seen_identifiers:
            continue # تکراری است
        
        seen_identifiers.add(identifier)
        
        print(f"Processing {ip}:{port}...", end="\r")
        
        # دریافت پرچم
        country_code = get_ip_info(ip)
        flag = get_flag_emoji(country_code)
        
        # ساخت نام جدید
        new_name = f"{flag} Config-{config_count}"
        final_config = f"{config}#{new_name}"
        
        final_configs += final_config + "\n"
        config_count += 1
        
        # وقفه کوتاه برای جلوگیری از مسدود شدن توسط IP-API
        time.sleep(0.5)

    # 3. ذخیره خروجی
    if final_configs:
        encoded_configs = base64.b64encode(final_configs.encode('utf-8')).decode('utf-8')
        
        output_file = "filtered_configs.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(encoded_configs)
        
        print(f"\n\n🎉 Success! {config_count-1} unique configs found and saved.")
    else:
        print("\n\n⚠️ No valid configs found after filtering.")

if __name__ == "__main__":
    fetch_configs()
