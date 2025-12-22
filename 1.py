import streamlit as st
import asyncio
from playwright.async_api import async_playwright

async def get_m3u8_via_browser(url):
    m3u8_links = []
    
    async with async_playwright() as p:
        # 啟動瀏覽器
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # 監聽網路請求
        def handle_request(request):
            if ".m3u8" in request.url:
                m3u8_links.append(request.url)

        page.on("request", handle_request)

        try:
            # 導向網址，等待影片加載 (最多等 15 秒)
            await page.goto(url, wait_until="networkidle", timeout=15000)
            # 模擬點擊播放器區域（有時需要觸發才會加載 m3u8）
            await page.mouse.click(500, 400)
            await asyncio.sleep(5) 
        except Exception as e:
            st.error(f"瀏覽器加載超時或錯誤: {e}")
        finally:
            await browser.close()
            
    return list(set(m3u8_links))

# --- Streamlit UI ---
st.title("🚀 終極影片提取工具 (瀏覽器模擬版)")

target_url = st.text_input("請輸入 Dramaq 網址:", value="https://dramaq.xyz/cn/5597942/ep3.html")

if st.button("深度掃描"):
    if target_url:
        with st.spinner("正在啟動虛擬瀏覽器進行掃描... 這可能需要 20-30 秒"):
            found_links = asyncio.run(get_m3u8_via_browser(target_url))
            
            if found_links:
                st.success(f"找到 {len(found_links)} 個影片資源：")
                for link in found_links:
                    st.code(link)
                    st.video(link)
            else:
                st.warning("⚠️ 瀏覽器掃描完畢，但未偵測到 .m3u8 請求。可能是網站阻擋了虛擬瀏覽器。")
