import streamlit as st
import requests
import re
import json
import base64
from urllib.parse import unquote
from bs4 import BeautifulSoup

def extract_m3u8(url):
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': 'https://dramaq.xyz/'
    }
    resp = requests.get(url, headers=headers, timeout=10)
    html = resp.text

    # 1. 找 iframe
    soup = BeautifulSoup(html, "html.parser")
    iframe = soup.find("iframe")
    if not iframe or not iframe.get("src"):
        return ["❌ 沒有找到 iframe"]

    iframe_url = iframe["src"]
    iframe_resp = requests.get(iframe_url, headers=headers, timeout=10)
    iframe_html = iframe_resp.text

    # 2. 嘗試找 player_xxx 變數
    matches = re.findall(r'var\s+player_\w+\s*=\s*({.*?});', iframe_html)
    results = []
    for js in matches:
        try:
            data = json.loads(js)
            raw_url = data.get("url", "")
            if raw_url.startswith("http"):
                results.append(unquote(raw_url))
            else:
                try:
                    decoded = base64.b64decode(raw_url).decode("utf-8")
                    results.append(unquote(decoded))
                except:
                    results.append(f"⚠️ 無法解碼: {raw_url}")
        except:
            continue

    # 3. 備案：直接搜尋 m3u8
    if not results:
        m3u8_links = re.findall(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', iframe_html)
        results.extend(m3u8_links)

    return results

# --- Streamlit 介面 ---
st.title("🎬 dramaq.xyz 影片地址提取工具")
url = st.text_input("請輸入網址:", value="https://dramaq.xyz/cn/5597942/ep3.html")

if st.button("開始提取"):
    res = extract_m3u8(url)
    if res:
        st.success("✅ 找到影片地址：")
        for link in res:
            st.code(link, language="text")
            if "m3u8" in link:
                st.video(link)
    else:
        st.error("❌ 沒有找到任何影片地址")
