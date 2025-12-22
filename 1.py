import asyncio
import re
import os
import random
from playwright.async_api import async_playwright

# --- 設定區域 ---
TARGET_ID = "5597942" 
BASE_DOMAIN = "dramaq.xyz"
# ------------------

async def get_m3u8_for_ep(page, drama_id, ep):
    m3u8_links = set()
    # 播放頁路徑：/cn/5597942/1.html
    play_url = f"https://{BASE_DOMAIN}/cn/{drama_id}/{ep}.html"
    
    def handle_request(req):
        if ".m3u8" in req.url.lower():
            m3u8_links.add(req.url)
    page.on("request", handle_request)

    try:
        print(f"🎬 正在解析第 {ep} 集...")
        # 這裡改用 wait_until="networkidle"，確保影片解析 JS 跑完
        await page.goto(play_url, wait_until="networkidle", timeout=60000)
        
        # 輪詢檢查所有 frames
        for _ in range(10):
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
        # 啟動並加入偽裝參數
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        detail_url = f"https://{BASE_DOMAIN}/cn/{TARGET_ID}/"
        print(f"📡 前往詳情頁: {detail_url}")
        
        await page.goto(detail_url, wait_until="domcontentloaded")
        await asyncio.sleep(5) # 給予足夠時間讓 JS 渲染清單

        # --- 核心偵測邏輯：直接抓取頁面所有連結並用正則篩選 ---
        all_eps = set()
        
        # 抓取頁面上所有的 <a> 標籤的 href
        hrefs = await page.evaluate("""
            () => Array.from(document.querySelectorAll('a')).map(a => a.href)
        """)
        
        # 匹配格式：/cn/5597942/1.html
        pattern = rf"/{TARGET_ID}/(\d+)\.html"
        for href in hrefs:
            match = re.search(pattern, href)
            if match:
                all_eps.add(int(match.group(1)))

        if not all_eps:
            # 備用：如果連結沒出來，可能在某些隱藏的 JSON 裡
            print("🕵️ 嘗試從原始碼直接提取集數數字...")
            content = await page.content()
            matches = re.findall(rf"/{TARGET_ID}/(\d+)\.html", content)
            all_eps.update([int(m) for m in matches])

        if not all_eps:
            print("❌ 依然找不到集數。請確認 ID 是否正確，或網域是否有跳轉。")
            await browser.close(); return

        ep_list = sorted(list(all_eps))
        print(f"✅ 偵測完成：找到共 {len(ep_list)} 集 (集數: {ep_list})")

        # --- 執行抓取 ---
        output_file = "all_episodes_results.txt"
        for ep in ep_list:
            # 檢查增量
            if os.path.exists(output_file):
                with open(output_file, "r", encoding="utf-8") as f:
                    if f"第 {ep} 集:" in f.read():
                        print(f"⏭️ 第 {ep} 集已存在，跳過。")
                        continue

            links = await get_m3u8_for_ep(page, TARGET_ID, ep)
            with open(output_file, "a", encoding="utf-8") as f:
                f.write(f"第 {ep} 集: {', '.join(links) if links else '未找到'}\n")
            print(f"💾 第 {ep} 集資料已存檔")
            await asyncio.sleep(random.uniform(2, 4))

        await browser.close()
        print("🏁 全部任務結束")

if __name__ == "__main__":
    asyncio.run(run())
