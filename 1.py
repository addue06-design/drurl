import asyncio
import re
from playwright.async_api import async_playwright

async def get_dramasq_m3u8_advanced(drama_id, ep=5):
    m3u8_links = set()
    play_url = f"https://dramasq.io/vodplay/{drama_id}/ep{ep}.html"
    
    async with async_playwright() as p:
        print(f"🚀 啟動深度解析: {play_url}")
        # 建議先用 headless=False 在本地觀察，看看是否卡在 Cloudflare 驗證
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 720}
        )
        page = await context.new_page()

        # 1. 持續監聽封包
        page.on("request", lambda request: m3u8_links.add(request.url) if ".m3u8" in request.url else None)

        try:
            # 2. 訪問頁面
            await page.goto(play_url, wait_until="domcontentloaded", timeout=60000)
            
            # 3. 掃描所有存在的 Frames (播放器通常在 iframe 裡)
            print("🔍 正在掃描頁面內所有框架...")
            for _ in range(10):  # 迴圈等待 10 秒，每秒檢查一次
                # 遍歷所有框架搜尋內容中的 m3u8 關鍵字
                for frame in page.frames:
                    try:
                        content = await frame.content()
                        # 使用正規表達式搜尋隱藏在 JS 中的 m3u8 連結
                        found = re.findall(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', content)
                        for link in found:
                            m3u8_links.add(link)
                    except:
                        continue
                
                if m3u8_links: break
                await asyncio.sleep(1)

            # 4. 如果還是沒找到，模擬點擊螢幕中央（觸發播放器加載）
            if not m3u8_links:
                print("🖱 未偵測到流媒體，嘗試模擬點擊播放器...")
                await page.mouse.click(640, 360)
                await asyncio.sleep(5)

            # 5. 結果輸出
            if m3u8_links:
                print(f"✅ 成功攔截到 {len(m3u8_links)} 個資源：")
                for i, link in enumerate(m3u8_links):
                    # 過濾掉一些無用的短片頭（如果有的話）
                    print(f"   [{i+1}] {link}")
            else:
                # 最終診斷：截圖看看到底畫面長怎樣
                await page.screenshot(path="fail_screenshot.png")
                print("❌ 依舊解析失敗。請查看同目錄下的 fail_screenshot.png，確認是否出現驗證碼或播放器未載入。")

        except Exception as e:
            print(f"❌ 程式執行異常: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    # 測試非凡第 5 集
    asyncio.run(get_dramasq_m3u8_advanced("202500838", ep=5))
