import streamlit as st
import asyncio
import os
import subprocess
import sys

try:
    from playwright.async_api import async_playwright
except ImportError:
    st.error("請確保 requirements.txt 中已加入 playwright")

def install_playwright():
    try:
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
    except Exception as e:
        st.error(f"安裝失敗: {e}")

async def get_all_m3u8(url):
    all_links = set()
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            # 1. 攔截網路請求 (Network Sniffing)
            page.on("request", lambda request: all_links.add(request.url) if ".m3u8" in request.url else None)

            # 2. 訪問主頁面
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # 3. 嘗試找出所有可能的「線路」按鈕並點擊
            # 這是針對 Dramaq 結構優化的選取器，嘗試點擊不同播放來源
            try:
                # 尋找像是「線路1」、「線路2」或 Tab 標籤
                tabs = await page.query_selector_all("ul.stui-content__playlist li a, .play_source_tab a")
                for i, tab in enumerate(tabs[:5]): # 限制點擊前 5 個線路避免過久
                    try:
                        await tab.click()
                        await asyncio.sleep(3) # 每點一個線路等 3 秒抓取新請求
                    except:
                        continue
            except:
                pass

            # 4. 掃描所有 Iframe 的內容 (有些地址在靜態內容中)
            iframes = page.frames
            for frame in iframes:
                try:
                    content = await frame.content()
                    # 使用正則從內嵌代碼中尋找 m3u8
                    import re
                    found = re.findall(r'https?://[^\s\'"]+\.m3u8', content)
                    for f in found:
                        all_links.add(f)
                except:
                    continue

            await browser.close()
        except Exception as e:
            st.error(f"提取過程中發生問題: {e}")
            
    return list(all_links)

# --- Streamlit UI ---
st.set_page_config(page_title="影片地址全提取", layout="wide")
st.title("🎬 影片地址深度提取工具")

if 'browser_installed' not in st.session_state:
    with st.spinner("環境初始化中..."):
        install_playwright()
        st.session_state['browser_installed'] = True

input_url = st.text_input("請輸入 Dramaq 網址:", value="https://dramaq.xyz/cn/5597942/ep3.html")

if st.button("深度全掃描"):
    if input_url:
        with st.spinner("正在切換線路並攔截所有潛在位址，請稍候..."):
            results = asyncio.run(get_all_m3u8(input_url))
            
            if results:
                st.success(f"掃描完畢！共發現 {len(results)} 個不同資源：")
                # 分類顯示 (有些可能是重複的或者不同畫質)
                for i, link in enumerate(results):
                    with st.expander(f"資源 {i+1}"):
                        st.code(link)
                        if ".m3u8" in link:
                            st.write("測試播放：")
                            st.video(link)
            else:
                st.warning("未能發現更多位址。")
