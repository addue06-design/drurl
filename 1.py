import streamlit as st
import requests
import re
import json
import base64
from urllib.parse import unquote

def extract_m3u8_debug(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://dramaq.xyz/',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    
    try:
        # 1. 抓取網頁內容
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        if response.status_code != 200:
            return f"❌ 伺服器回傳錯誤代碼: {response.status_code} (可能是 IP 被封鎖)"
        
        html = response.text

        # 2. 廣泛搜尋所有可能是播放器數據的變數
        # 匹配 var player_xxxx = { ... }
        match = re.search(r'var\s+player_(\w+)\s*=\s*({.*?});', html)
        
        if not match:
            # 備案：搜尋 HTML 中是否有隱藏的 m3u8 特徵
            m3u8_links = re.findall(r'https?[%3A%2F%2F|://][^\s\'"]+\.m3u8[^\s\'"]*', html)
            if m3u8_links:
                return [unquote(link) for link in m3u8_links]
            return "❌ 找不到播放器數據變數 (player_data/aaaa)"

        # 3. 解析 JSON
        json_str = match.group(2)
        try:
            player_info = json.loads(json_str)
            raw_url = player_info.get("url", "")
            
            if not raw_url:
                return f"❌ 變數中沒有 url 欄位: {json_str[:100]}..."

            # 4. 解碼邏輯
            # 如果是 http 開頭，直接回傳
            if raw_url.startswith('http'):
                return [unquote(raw_url)]
            
            # 否則嘗試 Base64 解碼
            try:
                decoded = base64.b64decode(raw_url).decode('utf-8')
                return [unquote(decoded)]
            except:
                # 有些網站會自定義加密，這裏如果失敗代表需要更深入的 JS 分析
                return [f"⚠️ 發現加密字串但無法標準解碼: {raw_url}"]

        except json.JSONDecodeError:
            return "❌ JSON 解析失敗"

    except Exception as e:
        return f"❌ 發生異常: {str(e)}"

# --- Streamlit 介面 ---
st.set_page_config(page_title="影片地址解析器", layout="wide")
st.title("🎬 影片地址提取工具 (診斷版)")

input_url = st.text_input("請輸入網址:", value="https://dramaq.xyz/cn/5597942/ep3.html")

if st.button("開始診斷與提取"):
    with st.spinner('正在分析網頁結構...'):
        res = extract_m3u8_debug(input_url)
        
        if isinstance(res, list):
            st.success("✅ 提取成功！")
            for link in res:
                st.code(link, language="text")
                if "m3u8" in link:
                    st.video(link)
        else:
            st.error(res)
            st.info("💡 如果顯示「找不到變數」，代表該網頁可能使用了混淆腳本，或者正在跳轉中。")
