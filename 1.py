import asyncio
import os
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        url = "https://dramasq.io/vodplay/202500838/ep5.html"
        print(f"🔗 掃描中: {url}")
        
        m3u8_links = []
        page.on("request", lambda req: m3u8_links.append(req.url) if ".m3u8" in req.url else None)
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(20) # 雲端建議等久一點
            
            # 強制產生一個檔案，方便我們檢查 Action 是否有權限寫入
            with open("action_report.txt", "w", encoding="utf-8") as f:
                f.write("掃描任務已完成\n")
                if m3u8_links:
                    f.write(f"✅ 成功抓取到 {len(m3u8_links)} 個連結：\n")
                    for link in set(m3u8_links):
                        f.write(f"{link}\n")
                else:
                    f.write("❌ 遺憾，本次掃描未發現 m3u8 連結。\n")
                    f.write(f"頁面標題: {await page.title()}\n")
            
            print("📝 報告已寫入 action_report.txt")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
