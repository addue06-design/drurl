import streamlit as st
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def extract_m3u8(url):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)
    time.sleep(5)
    links = driver.find_elements(By.XPATH, '//a[@play-data]')
    m3u8_list = [link.get_attribute("play-data") for link in links if link.get_attribute("play-data")]
    driver.quit()
    return m3u8_list

# Streamlit 介面
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
            st.warning("⚠️ 沒有找到任何影片地址，可能需要增加等待時間或檢查網頁。")
