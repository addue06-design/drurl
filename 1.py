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
        response = requests.get(url, headers=headers, timeout=10)
        html = response.text

        # 找所有 var player_xxx = {...}
        matches = re.findall(r'var\s+player_\w+\s*=\s*({.*?});', html)
        results = []

        for json_str in matches:
            try:
                player_info = json.loads(json_str)
                raw_url = player_info.get("url", "")
                if raw_url:
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

        # 備案：直接找 m3u8
        if not results:
            m3u8_links = re.findall(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', html)
            results.extend([unquote(link) for link in m3u8_links])

        return results if results else "❌ 沒有找到任何影片地址"

    except Exception as e:
        return f"❌ 發生異常: {str(e)}"

# --- Streamlit 介面 ---
st.set_page_config(page_title="影片地址解析器", layout="wide")
st.title("🎬 影片地址提取工具 (診斷版)")

input_url = st.text_input("請輸入網址:", value="https://dramaq.xyz/cn/5597942/ep3.html")

if st.button("開始診斷與提取"):
    with st.spinner('正在分析網頁結構...'):
        res = extract_m3u8_debug(input_url)
        
        if isinstance(res, list) and res:
            st.success("✅ 提取成功！")
            for link in res:
                st.code(link, language="text")
                if "m3u8" in link:
                    st.video(link)
        else:
            st.error(res)
            st.info("💡 如果顯示「找不到變數」，代表該網頁可能使用了混淆或需要 JS 執行。")
