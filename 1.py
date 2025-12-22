import streamlit as st
import requests
from bs4 import BeautifulSoup
import re

def extract_m3u8(url):
    # 抓取原始 HTML
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    html = response.text

    # 嘗試找 iframe
    soup = BeautifulSoup(html, "html.parser")
    iframe = soup.find("iframe")
    if iframe and iframe.get("src"):
        iframe_url = iframe["src"]
        # 再抓 iframe 的內容
        iframe_resp = requests.get(iframe_url, timeout=10)
        iframe_resp.raise_for_status()
        iframe_html = iframe_resp.text

        # 嘗試在 iframe 裡找 m3u8
        m3u8_links = re.findall(r"https?://[^\s'\"]+\.m3u8", iframe_html)
        return m3u8_links

    # 如果沒有 iframe，直接在原始碼裡找 m3u8
    m3u8_links = re.findall(r"https?://[^\s'\"]+\.m3u8", html)
    return m3u8_links

# Streamlit 介面
st.title("🎬 影片地址提取工具")
url = st.text_input("請輸入要解析的網址:")

if st.button("開始提取"):
    if url:
        try:
            results = extract_m3u8(url)
            if results:
                st.success("找到的影片地址：")
                for link in results:
                    st.write(link)
            else:
                st.warning("⚠️ 沒有找到任何影片地址")
        except Exception as e:
            st.error(f"發生錯誤: {e}")
