import streamlit as st
import requests
from bs4 import BeautifulSoup

def extract_m3u8(url):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    links = soup.find_all("a", attrs={"play-data": True})
    return [link["play-data"] for link in links if link.get("play-data")]

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
