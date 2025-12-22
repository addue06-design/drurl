import streamlit as st
import requests
import re
import json
import base64
from urllib.parse import unquote

def extract_m3u8_advanced(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://dramaq.xyz/'
    }
    
    try:
        # 1. 抓取網頁內容
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        html = response.text

        # 2. 使用正則表達式尋找播放器數據 (這類網站的核心數據所在)
        # 它通常長這樣：var player_aaaa = {"url":"BASE64_STRING", ...}
        match = re.search(r'var\s+player_(?:aaaa|data)\s*=\s*({.*?});', html)
        
        if not match:
            # 如果找不到 JSON，嘗試直接搜尋源碼中的 m3u8
            m3u8_links = re.findall(r'https?%3A%2F%2F[^\s\'"]+\.m3u8', html)
            if not m3u8_links:
                m3u8_links = re.findall(r'https?://[^\s\'"]+\.m3u8', html)
            return [unquote(link) for link in m3u8_links]

        # 3. 解析 JSON 數據
        player_info = json.loads(match.group(1))
        raw_url = player_info.get("url", "")
        
        # 4. 解碼邏輯
        # 判斷是否為 Base64 (通常不包含 http 且有特定的編碼特徵)
        if raw_url and not raw_url.startswith('http'):
            try:
                # 嘗試 Base64 解碼
                decoded_url = base64.b64decode(raw_url).decode('utf-8')
                # 再次進行 URL 解碼以防萬一
                final_url = unquote(decoded_url)
                return [final_url]
            except Exception:
                return [f"找到加密字串但解碼失敗: {raw_url}"]
        
        return [unquote(raw_url)] if raw_url else []

    except Exception as e:
        return [f"解析過程中發生錯誤: {str(e)}"]

# --- Streamlit 介面 ---
st.set_page_config(page_title="影片地址提取器", page_icon="🎬")

st.title("🎬 影片地址提取工具")
st.info("專門針對 Dramaq 等採用加密技術的影視網站優化")

input_url = st.text_input("請輸入要解析的網址:", placeholder="https://dramaq.xyz/...")

if st.button("開始提取"):
    if input_url:
        with st.spinner('正在分析網頁數據，請稍候...'):
            results = extract_m3u8_advanced(input_url)
            
            if results and not results[0].startswith("錯誤") and not results[0].startswith("找到加密"):
                st.success("🎉 成功提取到影片位址！")
                for i, link in enumerate(results):
                    st.code(link, language="text")
                    st.video(link) if ".m3u8" in link else None
                
                st.warning("💡 提示：若影片無法播放，可能是因為該伺服器阻擋了直接訪問，需在播放器中設定 Referer 為原網站域名。")
            else:
                st.error("⚠️ 未能提取到有效的影片位址")
                if results:
                    st.write(results[0])
    else:
        st.warning("請先輸入網址")
