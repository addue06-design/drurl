import streamlit as st
from playwright.sync_api import sync_playwright

def extract_m3u8(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        page.wait_for_timeout(5000)  # 等待 JS 載入
        links = page.query_selector_all("a[play-data]")
        m3u8_list = [link.get_attribute("play-data") for link in links if link.get_attribute("play-data")]
        browser.close()
        return m3u8_list

st.title("🎬 影片地址提取工具")
url = st.text_input("請輸入要解析的網址:")

if st.button("開始提取"):
    if url:
        results = extract_m3u8(url)
        if results:
            st.success("找到的影片地址：")
            for link in results:
                st.write(link)
        else:
            st.warning("⚠️ 沒有找到任何影片地址")
