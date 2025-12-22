import streamlit as st
import asyncio
import os
import subprocess
import sys

# --- 核心：自動安裝 Playwright 瀏覽器 ---
def install_playwright():
    try:
        # 使用 sys.executable 確保使用當前環境的 Python
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
    except Exception as e:
        st.error(f"瀏覽器主體下載失敗，請檢查網路或日誌。錯誤: {e}")

# --- 核心：抓取邏輯 ---
async def get_m3u8_via_browser(url):
    m3u8_links = []
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            # 設定較長的請求超時與模擬真實視窗大小
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            # 監聽所有網路請求
            page.on("request", lambda request: m3u8_links.append(request.url) if ".m3u8" in request.url else None)

            # 增加載入等待時間
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(10) # 給予足夠時間讓播放器初始化
            
            await browser.close()
        except Exception as e:
            st.error(f"掃描時發生錯誤: {e}")
            
    return list(set(m3u8_links))

# --- Streamlit UI ---
st.set_page_config(page_title="影片地址解析", layout="wide")
st.title("🎬 影片地址提取工具 (穩定版)")

if 'browser_installed' not in st.session_state:
    with st.spinner("正在初始化環境 (僅需執行一次)..."):
        install_playwright()
        st.session_state['browser_installed'] = True

input_url = st.text_input("請輸入網址:", value="https://dramaq.xyz/cn/5597942/ep3.html")

if st.button("開始深度提取"):
    if input_url:
        with st.spinner("正在模擬瀏覽器訪問並攔截封包..."):
            # 在 Streamlit 中正確執行異步任務
            found_links = asyncio.run(get_m3u8_via_browser(input_url))
            
            if found_links:
                st.success(f"成功！找到 {len(found_links)} 個資源位址：")
                for link in found_links:
                    st.code(link)
                    if "m3u8" in link:
                        st.video(link)
            else:
                st.warning("未能偵測到影片地址。可能是該頁面需要手動點擊，或網站阻擋了此伺服器的存取。")
