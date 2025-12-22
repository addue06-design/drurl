import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # 模擬更真實的視窗大小
        context = await browser.new_context(viewport={'width': 1280, 'height': 720})
        page = await context.new_page()
        
        url = "https://dramasq.io/vodplay/202500838/ep5.html"
        print(f"📡 深度掃描中: {url}")
        
        m3u8_links = set()
        page.on("request", lambda req: m3u8_links.add(req.url) if ".m3u8" in req.url else None)
        
        try:
            # 1. 進入頁面
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # 2. 模擬人為滾動 (觸發懶加載)
            await page.evaluate("window.scrollTo(0, 500)")
            await asyncio.sleep(2)
            
            # 3. 嘗試在播放器可能的區域點擊多次 (DramasQ 的播放器通常在中央)
            # 我們嘗試三個不同的中心點
            click_points = [(640, 360), (640, 400), (600, 360)]
            for x, y in click_points:
                await page.mouse.click(x, y)
                await asyncio.sleep(1)

            # 4. 給予足夠的播放載入時間
            print("⏳ 正在等待 m3u8 請求彈出...")
            await asyncio.sleep(25) 
            
            # 5. 強制產出報告
            with open("action_report.txt", "w", encoding="utf-8") as f:
                if m3u8_links:
                    f.write(f"✅ 成功! 在 {url} 找到網址:\n")
                    for link in m3u8_links:
                        f.write(f"{link}\n")
                else:
                    f.write(f"❌ 依舊未發現 m3u8。頁面標題: {await page.title()}\n")
                    # 這是終極絕招：輸出頁面所有 iframe 的網址，看看播放器在哪
                    f.write("\n--- 偵錯資訊: Iframe 列表 ---\n")
                    for frame in page.frames:
                        f.write(f"Frame URL: {frame.url}\n")

        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
