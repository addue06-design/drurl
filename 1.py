import streamlit as st
import asyncio
import os
import subprocess
import sys

# 重點：確保導入了 async_playwright
try:
    from playwright.async_api import async_playwright
except ImportError:
    st.error("找不到 Playwright 模組，請確保 requirements.txt 中已加入 playwright")

# --- 自動安裝瀏覽器主體 ---
def install_playwright():
    try:
        # 在 Streamlit Cloud 上，我們只需要安裝 chromium 
        # 系統依賴必須寫在 packages.txt 中
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
    except Exception as e:
        st.error(f"瀏覽器驅動安裝失敗: {e}")

async def get_m3u8_via_browser(url):
    m3u8_links = []
    # 這裡必須確保 async_playwright 已正確導入
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            # 攔截包含 .m3u8 的請求
            page.on("request", lambda request: m3u8_links.append(request.url) if ".m3u8" in request.url else None)

            # 訪問網址
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # 給予一些緩衝時間讓播放器加載請求
            await asyncio.sleep(10)
            
            await browser.close()
        except Exception as e:
            st.error(f"瀏覽器執行中出錯: {e}")
            
    return list(set(m3u8_links))

# --- Streamlit 介面 ---
st.set_page_config(page_title="影片地址提取", page_icon="🎬")
st.title("🎬 影片地址提取工具")

# 初始化環境
if 'browser_installed' not in st.session_state:
    with st.spinner("正在為您初始化雲端瀏覽器環境..."):
        install_playwright()
        st.session_state['browser_installed'] = True

input_url = st.text_input("請輸入 Dramaq 網址:", value="https://dramaq.xyz/cn/5597942/ep3.html")

if st.button("開始掃描"):
    if input_url:
        with st.spinner("虛擬瀏覽器正在抓取封包... 請稍後..."):
            try:
                # 使用 asyncio.run 執行異步函數
                found_links = asyncio.run(get_m3u8_via_browser(input_url))
                
                if found_links:
                    st.success(f"成功找到 {len(found_links)} 個資源！")
                    for link in found_links:
                        st.code(link)
                        # 如果是 m3u8，嘗試在頁面播放
                        if ".m3u8" in link:
                            st.video(link)
                else:
                    st.warning("未能攔截到影片地址。可能是網站檢測到了自動化工具，或是該伺服器 IP 被屏蔽。")
            except Exception as e:
                st.error(f"程序執行失敗: {e}")
