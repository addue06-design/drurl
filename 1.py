import asyncio
import re
import sys
from playwright.async_api import async_playwright

# --- 靈活設定區域 ---
# 這裡可以直接輸入劇名（例如 "非凡"）或代碼（例如 "202500838"）
TARGET_INPUT = "202500838"  
TARGET_EP = 5
# ------------------

async def run_integrated_scraper():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 720}
        )
        page = await context.new_page()

        drama_id = None
        drama_name = "未知劇集"

        # --- 判別式邏輯 ---
        if TARGET_INPUT.isdigit():
            # 1. 如果輸入是純數字，直接當作 ID
            drama_id = TARGET_INPUT
            print(f"🔢 偵測到數字輸入，直接使用代碼模式: {drama_id}")
        else:
            # 2. 如果是文字，先去清單尋找 ID
            print(f"🔍 偵測到劇名輸入，正在清單中搜尋: {TARGET_INPUT}")
            list_url = "https://dramasq.io/type-tv/cn/"
            await page.goto(list_url, wait_until="domcontentloaded")
            
            links = await page.query_selector_all("a")
            for link in links:
                href = await link.get_attribute("href")
                text = (await link.inner_text() or "").strip()
                title = (await link.get_attribute("title") or "").strip()
                
                if TARGET_INPUT in text or TARGET_INPUT in title:
                    match = re.search(r'/detail/(\d+)\.html', href or "")
                    if match:
                        drama_id = match.group(1)
                        drama_name = text or title
                        print(f"✅ 找到匹配劇集: {drama_name} (ID: {drama_id})")
                        break
        
        # --- 影片解析階段 ---
        if drama_id:
            play_url = f"https://dramasq.io/vodplay/{drama_id}/ep{TARGET_EP}.html"
            print(f"🚀 啟動影片解析: {play_url}")
            
            m3u8_links = set()
            page.on("request", lambda req: m3u8_links.add(req.url) if ".m3u8" in req.url else None)
            
            try:
                await page.goto(play_url, wait_until="domcontentloaded", timeout=60000)
                
                # 循環掃描 Frame (保持之前成功的深度解析邏輯)
                for _ in range(15):
                    for frame in page.frames:
                        try:
                            content = await frame.content()
                            found = re.findall(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', content)
                            for link in found:
                                m3u8_links.add(link)
                        except: continue
                    if m3u8_links: break
                    await asyncio.sleep(1)

                if not m3u8_links:
                    await page.mouse.click(640, 360)
                    await asyncio.sleep(10)

                # 儲存結果
                with open("video_results.txt", "w", encoding="utf-8") as f:
                    if m3u8_links:
                        f.write(f"結果: {drama_name} (ID: {drama_id}) 第 {TARGET_EP} 集\n")
                        for link in m3u8_links:
                            f.write(f"{link}\n")
                    else:
                        f.write(f"❌ 抓取失敗: {drama_name} (ID: {drama_id})")
                print("✅ 任務結束，請查看 video_results.txt")

            except Exception as e:
                print(f"❌ 影片解析錯誤: {e}")
        else:
            print(f"❌ 無法識別劇集: {TARGET_INPUT}，請檢查名稱是否正確。")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_integrated_scraper())
