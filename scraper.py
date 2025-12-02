import requests
from bs4 import BeautifulSoup
import re
import os
import base64

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
]

# پروتکل‌های مورد نظر
prefixes = ('vless://',)

def extract_username(url):
    return url.split('/')[-1]

def fetch_configs():
    all_configs = ""
    config_count = 1
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    for url in channels:
        username = extract_username(url)
        print(f"Checking {username}...")
        
        try:
            response = requests.get(f"https://t.me/s/{username}", headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"Failed to fetch {username}")
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
                        
                        new_name = f"Config-{config_count}"
                        final_config = f"{clean_line}#{new_name}"
                        
                        all_configs += final_config + "\n"
                        config_count += 1
            
        except Exception as e:
            print(f"Error scraping {username}: {e}")

    # تبدیل به Base64
    encoded_configs = base64.b64encode(all_configs.encode('utf-8')).decode('utf-8')

    # ذخیره در فایل
    output_file = "filtered_configs.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(encoded_configs)
    
    print(f"\n✅ Done. {config_count-1} configs found.")
    print(f"Encoded configs saved to {output_file}")

if __name__ == "__main__":
    fetch_configs()
