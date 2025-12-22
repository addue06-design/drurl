import streamlit as st
import asyncio
import os
import subprocess
from playwright.async_api import async_playwright

# --- 核心：自動安裝 Playwright 瀏覽器 ---
def install_playwright():
    try:
        # 僅安裝 chromium 瀏覽器，不安裝系統依賴 (因為沒 sudo 權限)
        # --with-deps 換成由 packages.txt 處理
        subprocess.run(["python", "-m", "playwright", "install", "chromium"], check=True)
    except Exception as e:
        st.error(f"安裝瀏覽器主體失敗: {e}")

async def get_m3u8_via_browser(url):
    m3u8_links = []
    async with async_playwright() as p:
        try:
            # 啟動時加入關鍵參數以在容器內運行
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox", 
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage", # 防止記憶體不足
                    "--disable-gpu"
                ]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            # 攔截請求
            def handle_request(request):
                if ".m3u8" in request.url:
                    m3u8_links.append(request.url)

            page.on("request", handle_request)

            # 訪問網址
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            
            # 等待一段時間讓 JS 執行
            await asyncio.sleep(8) 
            
            await browser.close()
        except Exception as e:
            st.error(f"瀏覽器運行出錯: {e}")
            
    return list(set(m3u8_links))

# --- Streamlit UI 保持不變 ---
st.title("🎬 影片地址解析 (Cloud 環境優化版)")

if 'browser_installed' not in st.session_state:
    with st.spinner("正在初始化雲端環境..."):
        install_playwright()
        st.session_state['browser_installed'] = True

input_url = st.text_input("請輸入 Dramaq 網址:", value="https://dramaq.xyz/cn/5597942/ep3.html")

if st.button("開始掃描"):
    if input_url:
        with st.spinner("虛擬瀏覽器運作中..."):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(get_m3u8_via_browser(input_url))
            
            if results:
                st.success(f"找到 {len(results)} 個地址")
                for r in results:
                    st.code(r)
            else:
                st.warning("未能掃描到影片地址。可能是網站 IP 封鎖或檢測到自動化工具。")
