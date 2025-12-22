import asyncio
import re
import os
import random
from playwright.async_api import async_playwright

# --- 設定區域 ---
TARGET_ID = "5597942" 
BASE_DOMAIN = "dramaq.xyz"
OUTPUT_FILE = "all_episodes_results.txt"
# ------------------

async def get_m3u8_for_ep(page, drama_id, ep):
    m3u8_links = set()
    # 播放頁網址：/cn/5597942/ep1.html
    play_url = f"https://{BASE_DOMAIN}/cn/{drama_id}/ep{ep}.html"
    
    def handle_request(req):
        if ".m3u8" in req.url.lower():
            m3u8_links.add(req.url)
    page.on("request", handle_request)

    try:
        print(f"🎬 正在全量解析第 {ep} 集: {play_url}")
        # 使用 networkidle 確保非同步的影片請求有機會被攔截
        await page.goto(play_url, wait_until="networkidle", timeout=60000)
        
        # 輪詢掃描所有 frames 內的內容
        for _ in range(12):
            if m3u8_links: break
            for frame in page.frames:
                try:
                    content = await frame.content()
                    found = re.findall(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', content)
                    for link in found: m3u8_links.add(link)
                except: continue
            await asyncio.sleep(2)
            
    except Exception as e:
        print(f"⚠️ 第 {ep} 集解析異常: {e}")
    finally:
        page.remove_listener("request", handle_request)
    return list(m3u8_links)

async def run():
    async with async_playwright() as p:
        # 啟動參數：隱藏自動化特徵
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # 1. 偵測詳情頁獲取最新集數清單
        detail_url = f"https://{BASE_DOMAIN}/cn/{TARGET_ID}/"
        print(f"📡 前往詳情頁偵測清單: {detail_url}")
        
        await page.goto(detail_url, wait_until="domcontentloaded")
        await asyncio.sleep(3) # 等待列表加載

        all_eps = set()
        hrefs = await page.evaluate("() => Array.from(document.querySelectorAll('a')).map(a => a.href)")
        pattern = rf"/{TARGET_ID}/ep(\d+)\.html"
        
        for href in hrefs:
            match = re.search(pattern, href)
            if match:
                all_eps.add(int(match.group(1)))

        if not all_eps:
            # 備用暴力搜尋
            content = await page.content()
            all_eps.update([int(m) for m in re.findall(pattern, content)])

        if not all_eps:
            print("❌ 無法偵測到任何集數。")
            await browser.close(); return

        ep_list = sorted(list(all_eps))
        print(f"✅ 偵測成功：共 {len(ep_list)} 集，準備全量覆蓋抓取...")

        # 2. 清空/初始化輸出檔案 (使用 'w' 模式)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(f"--- {TARGET_ID} 全量同步結果 ---\n")

        # 3. 逐一抓取
        for ep in ep_list:
            links = await get_m3u8_for_ep(page, TARGET_ID, ep)
            
            # 使用 'a' 模式逐行存入，確保萬一當機也能保存已抓取的內容
            with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                f.write(f"第 {ep} 集: {', '.join(links) if links else '未找到'}\n")
            
            print(f"💾 第 {ep} 集完成")
            # 隨機延時保護
            await asyncio.sleep(random.uniform(1.5, 3.5))

        await browser.close()
        print(f"🏁 任務完成！結果已覆蓋儲存至 {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(run())
