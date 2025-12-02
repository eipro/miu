import requests
from bs4 import BeautifulSoup
import re
import os

# لیست کانال‌ها (فقط نام کاربری یا لینک کامل)
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
]

# پروتکل‌هایی که دنبالشان هستیم - فقط vless طبق درخواست شما
prefixes = ('vless://',)

def extract_username(url):
    """نام کاربری کانال را از لینک استخراج می‌کند"""
    return url.split('/')[-1]

def fetch_configs():
    all_configs = ""
    config_count = 1  # شمارنده برای نام‌گذاری ترتیبی کانفیگ‌ها
    
    # هدر فیک برای اینکه تلگرام فکر کند مرورگر واقعی هستیم
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    for url in channels:
        username = extract_username(url)
        print(f"Checking {username}...")
        
        try:
            # درخواست به نسخه پیش‌نمایش وب کانال (t.me/s/username)
            response = requests.get(f"https://t.me/s/{username}", headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"Failed to fetch {username}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # پیدا کردن متن پیام‌ها در HTML
            messages = soup.select('.tgme_widget_message_text')
            
            channel_configs = ""
            for msg in messages:
                # تبدیل تگ‌های <br> به خط جدید برای جداسازی صحیح
                for br in msg.find_all("br"):
                    br.replace_with("\n")
                
                text = msg.get_text()
                lines = text.split('\n')
                
                for line in lines:
                    clean_line = line.strip()
                    if clean_line.startswith(prefixes):
                        # لاجیک تغییر نام کانفیگ
                        # حذف هر چیزی که بعد از # وجود دارد (اسم قدیمی)
                        if '#' in clean_line:
                            clean_line = clean_line.split('#')[0]
                        
                        # ساخت اسم جدید با شماره: Config-1, Config-2, ...
                        new_name = f"Config-{config_count}"
                        
                        # چسباندن کانفیگ تمیز شده به اسم جدید
                        final_config = f"{clean_line}#{new_name}"
                        
                        channel_configs += final_config + "\n"
                        config_count += 1
            
            if channel_configs:
                # خط مربوط به اضافه کردن نام منبع حذف شد
                all_configs += channel_configs

        except Exception as e:
            print(f"Error scraping {username}: {e}")

    # ذخیره در فایل
    output_file = "filtered_configs.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(all_configs)
    
    print(f"\n✅ Done. Configs saved to {output_file}")

if __name__ == "__main__":
    fetch_configs()
