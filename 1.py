import streamlit as st
import asyncio
import os
import subprocess
from playwright.async_api import async_playwright

# --- 核心：自動安裝 Playwright 瀏覽器 ---
def install_playwright():
    try:
        # 檢查是否已經安裝過（檢查特定路徑或標記檔）
        if not os.path.exists("/home/adminuser/.cache/ms-playwright"):
            subprocess.run(["playwright", "install", "chromium"], check=True)
            subprocess.run(["playwright", "install-deps"], check=True)
    except Exception as e:
        st.error(f"安裝瀏覽器驅動失敗: {e}")

async def get_m3u8_via_browser(url):
    m3u8_links = []
    
    # 初始化 Playwright
    async with async_playwright() as p:
        try:
            # 啟動時加入 --no-sandbox 以適應 Linux 容器環境
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            # 監聽網路請求
            def handle_request(request):
                if ".m3u8" in request.url:
                    m3u8_links.append(request.url)

            page.on("request", handle_request)

            # 導向網址，增加等待時間
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # 額外等待 5 秒讓隱藏的播放器加載
            await asyncio.sleep(5) 
            
            await browser.close()
        except Exception as e:
            st.error(f"虛擬瀏覽器執行錯誤: {e}")
            
    return list(set(m3u8_links))

# --- Streamlit UI ---
st.set_page_config(page_title="影片提取工具", layout="wide")
st.title("🚀 終極影片提取工具 (Cloud 修復版)")

# 在 App 啟動時先執行安裝 (這只會運行一次)
if 'browser_installed' not in st.session_state:
    with st.spinner("首次啟動：正在配置雲端瀏覽器環境... 這可能需要一分鐘"):
        install_playwright()
        st.session_state['browser_installed'] = True

target_url = st.text_input("請輸入網址:", value="https://dramaq.xyz/cn/5597942/ep3.html")

if st.button("深度掃描"):
    if target_url:
        with st.spinner("虛擬瀏覽器掃描中... 請稍候..."):
            # 在 Streamlit 中運行異步代碼的正確方式
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            found_links = loop.run_until_complete(get_m3u8_via_browser(target_url))
            
            if found_links:
                st.success(f"找到 {len(found_links)} 個影片資源！")
                for link in found_links:
                    st.code(link)
                    st.video(link)
            else:
                st.warning("⚠️ 掃描完成但未找到連結。原因可能是：1. 網站 IP 封鎖 2. 影片需要手動點擊才能加載。")
