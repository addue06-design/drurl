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
    # 修正播放網址：加入 /ep{ep}.html
    play_url = f"https://{BASE_DOMAIN}/cn/{drama_id}/ep{ep}.html"
    
    def handle_request(req):
        if ".m3u8" in req.url.lower():
            m3u8_links.add(req.url)
    page.on("request", handle_request)

    try:
        print(f"🎬 正在解析第 {ep} 集: {play_url}")
        # 使用 networkidle 確保 M3U8 請求發出
        await page.goto(play_url, wait_until="networkidle", timeout=60000)
        
        # 掃描多層 frame 內容
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
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        detail_url = f"https://{BASE_DOMAIN}/cn/{TARGET_ID}/"
        print(f"📡 前往詳情頁: {detail_url}")
        
        await page.goto(detail_url, wait_until="domcontentloaded")
        await asyncio.sleep(5) # 等待列表動態加載

        # --- 核心偵測邏輯：更新為 /ep(\d+)\.html ---
        all_eps = set()
        
        # 1. 從頁面現有連結提取
        hrefs = await page.evaluate("() => Array.from(document.querySelectorAll('a')).map(a => a.href)")
        pattern = rf"/{TARGET_ID}/ep(\d+)\.html"
        
        for href in hrefs:
            match = re.search(pattern, href)
            if match:
                all_eps.add(int(match.group(1)))

        # 2. 如果連結沒被渲染，直接從原始碼暴力搜尋
        if not all_eps:
            print("🕵️ 嘗試從原始碼直接提取 ep 數字...")
            content = await page.content()
            matches = re.findall(pattern, content)
            all_eps.update([int(m) for m in matches])

        if not all_eps:
            print("❌ 依然找不到集數。請確認該 ID 在網站上是否有集數列表。")
            await browser.close(); return

        ep_list = sorted(list(all_eps))
        print(f"✅ 偵測成功：共 {len(ep_list)} 集 (清單: {ep_list})")

        # --- 3. 執行抓取 ---
        output_file = "all_episodes_results.txt"
        for ep in ep_list:
            # 增量判斷
            if os.path.exists(output_file):
                with open(output_file, "r", encoding="utf-8") as f:
                    if f"第 {ep} 集:" in f.read():
                        print(f"⏭️ 第 {ep} 集已存在，跳過。")
                        continue

            links = await get_m3u8_for_ep(page, TARGET_ID, ep)
            with open(output_file, "a", encoding="utf-8") as f:
                f.write(f"第 {ep} 集: {', '.join(links) if links else '未找到'}\n")
            print(f"💾 第 {ep} 集解析完成並記錄")
            
            # 延時避免被封鎖
            await asyncio.sleep(random.uniform(2, 4))

        await browser.close()
        print("🏁 全部同步任務完成！")

if __name__ == "__main__":
    asyncio.run(run())
