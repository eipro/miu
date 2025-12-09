import requests
from bs4 import BeautifulSoup
import re
import os
import base64
import time
import json
import ipaddress
from datetime import datetime, timedelta

# --- تنظیمات ---
BLOCKED_COUNTRIES = ['IR', 'CN', 'RU', 'KP']
MAX_CONFIGS_PER_COUNTRY = 50
TIME_LIMIT_HOURS = 48
PREFIXES = ('vless://', 'vmess://', 'trojan://', 'ss://', 'hysteria2://', 'tuic://')

OUTPUT_FILE = "filtered_configs.txt"
README_FILE = "README.md"
HTML_FILE = "index.html"

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
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}?fields=countryCode,isp,org", timeout=3)
        if response.status_code == 200:
            data = response.json()
            country = data.get('countryCode', '')
            isp = data.get('isp', '') or data.get('org', '')
            if isp:
                isp = isp.split(',')[0].split(' ')[0]
                if len(isp) > 15: isp = isp[:15]
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
        return True

def is_recent_message(msg_soup):
    try:
        time_tag = msg_soup.find('time')
        if time_tag and 'datetime' in time_tag.attrs:
            msg_time_str = time_tag['datetime'].split('+')[0]
            msg_time = datetime.fromisoformat(msg_time_str)
            if datetime.utcnow() - msg_time < timedelta(hours=TIME_LIMIT_HOURS):
                return True
            return False
    except:
        pass
    return True

def is_reality(config):
    if 'security=reality' in config or 'pbk=' in config or 'fp=' in config:
        return True
    return False

def rename_config(config, new_name, protocol):
    try:
        if protocol == 'vmess':
            b64_part = config.replace('vmess://', '')
            missing_padding = len(b64_part) % 4
            if missing_padding: b64_part += '=' * (4 - missing_padding)
            json_str = base64.b64decode(b64_part).decode('utf-8')
            data = json.loads(json_str)
            data['ps'] = new_name
            new_json = json.dumps(data)
            return f"vmess://{base64.b64encode(new_json.encode('utf-8')).decode('utf-8')}"
        else:
            if '#' in config:
                base_config = config.split('#')[0]
                return f"{base_config}#{new_name}"
            else:
                return f"{config}#{new_name}"
    except:
        return config

def parse_config_details(config):
    protocol = config.split('://')[0]
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
        pattern = r'@([^:]+):(\d+)'
        match = re.search(pattern, config)
        if match:
            return protocol, match.group(1), match.group(2)
        return protocol, 'Unknown', '0'

def generate_html(configs):
    rows = ""
    for idx, c in enumerate(configs):
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
            <td><button class="btn-copy" onclick="copyToClipboard('{link}')">Copy</button></td>
        </tr>"""
        
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Proxy Configs</title>
    <style>
        body {{ font-family: sans-serif; background: #121212; color: #eee; padding: 20px; }}
        table {{ width: 100%; border-collapse: collapse; background: #1e1e1e; }}
        th, td {{ padding: 10px; border-bottom: 1px solid #333; text-align: left; }}
        th {{ background: #2c2c2c; color: #4CAF50; }}
        .btn-copy {{ background: #2196F3; color: white; border: none; padding: 5px 10px; cursor: pointer; border-radius: 4px; }}
        .badge {{ padding: 2px 6px; border-radius: 4px; font-size: 0.8em; color: white; }}
        .vless {{ background: #9c27b0; }} .vmess {{ background: #e91e63; }} 
        .trojan {{ background: #ff9800; }} .ss {{ background: #607d8b; }}
    </style>
</head>
<body>
    <h1>🎒 Proxy List</h1>
    <p>Total: {len(configs)} | Updated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}</p>
    <table>
        <thead><tr><th>#</th><th>Flag</th><th>Country</th><th>ISP</th><th>Proto</th><th>Port/Tag</th><th>Action</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>
    <script>
        function copyToClipboard(text) {{ navigator.clipboard.writeText(text).then(() => alert('Copied!')); }}
    </script>
</body>
</html>"""
    with open(HTML_FILE, "w", encoding="utf-8") as f: f.write(html)

def update_readme(configs, stats):
    md = f"""# 🎒 Proxy Collector
**Last Update:** `{datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}`
**Total Configs:** `{len(configs)}`

## 🚀 Usage
- **All Configs:** [filtered_configs.txt](filtered_configs.txt)
- **Dashboard:** [View HTML Dashboard](https://github.com/{os.environ.get('GITHUB_REPOSITORY', 'your/repo')}/pages/)

## 📊 Stats by Country
| Flag | Country | Count |
|------|---------|-------|
"""
    sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)
    for country, count in sorted_stats:
        md += f"| {get_flag_emoji(country)} | {country} | {count} |\n"
        
    with open(README_FILE, "w", encoding="utf-8") as f: f.write(md)

def fetch_configs():
    channels = load_channels()
    if not channels: return

    raw_configs = []
    seen = set()
    processed = []
    stats = {}
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    print("📥 Scraping...")
    for url in channels:
        try:
            resp = requests.get(f"https://t.me/s/{url.split('/')[-1]}", headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            for wrap in soup.select('.tgme_widget_message_wrap'):
                if not is_recent_message(wrap): continue
                msg = wrap.select_one('.tgme_widget_message_text')
                if not msg: continue
                for br in msg.find_all("br"): br.replace_with("\n")
                for line in msg.get_text().split('\n'):
                    if line.strip().startswith(PREFIXES):
                        raw_configs.append(line.strip().split('#')[0] if 'vmess' not in line else line.strip())
        except: pass

    print(f"✅ Found {len(raw_configs)} raw configs. Processing...")
    
    counter = 1
    for config in raw_configs:
        proto, ip, port = parse_config_details(config)
        if not ip or not port or not is_valid_ip(ip): continue
        if f"{ip}:{port}" in seen: continue
        seen.add(f"{ip}:{port}")
        
        country, isp = get_ip_info(ip)
        if country in BLOCKED_COUNTRIES: continue
        
        # Stats
        stats[country if country else "Unknown"] = stats.get(country if country else "Unknown", 0) + 1
        
        # Limit check
        if stats.get(country, 0) > MAX_CONFIGS_PER_COUNTRY: continue
        
        print(f"Processing {counter}...", end="\r")
        
        flag = get_flag_emoji(country)
        features = "⚡Reality" if is_reality(config) else ""
        features += " 🔒" if str(port) == '443' else ""
        
        name = f"{flag} {isp} {counter} {features}"
        final = rename_config(config, name, proto)
        
        processed.append((country if country else "ZZZ", final, 
                         {'flag': flag, 'country': country, 'isp': isp, 'protocol': proto, 'port': port, 'features': features}))
        counter += 1
        time.sleep(0.2)

    processed.sort(key=lambda x: x[0])
    
    # Write Files
    with open(OUTPUT_FILE, "w") as f:
        f.write(base64.b64encode("\n".join([x[1] for x in processed]).encode('utf-8')).decode('utf-8'))
        
    for p in ['vless', 'vmess', 'trojan', 'ss']:
        subset = [x[1] for x in processed if x[2]['protocol'] == p]
        if subset:
            with open(f"{p}.txt", "w") as f:
                f.write(base64.b64encode("\n".join(subset).encode('utf-8')).decode('utf-8'))

    generate_html(processed)
    update_readme(processed, stats)
    print("\n🎉 Done!")

if __name__ == "__main__":
    fetch_configs()
