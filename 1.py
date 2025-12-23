import asyncio
import re
import os
import random
import time
from playwright.async_api import async_playwright

# --- 設定區域 ---
TARGET_ID = "" 
BASE_DOMAIN = "dramaq.xyz"
OUTPUT_FILE = "all_episodes_results.txt"
# ------------------

async def get_m3u8_for_ep(page, drama_id, ep):
    m3u8_links = set()
    play_url = f"https://{BASE_DOMAIN}/cn/{drama_id}/ep{ep}.html"
    
    def handle_request(req):
        if ".m3u8" in req.url.lower():
            m3u8_links.add(req.url)
    page.on("request", handle_request)

    try:
        print(f"🎬 正在全量解析第 {ep} 集所有線路...")
        await page.goto(play_url, wait_until="networkidle", timeout=60000)
        
        # 1. 偵測並模擬點擊「播放線路」按鈕
        # 這裡的選擇器針對 dramaq.xyz 常見的線路切換標籤
        sources = await page.query_selector_all(".play_source_tab a, .source-list a, .playlist_notfull li")
        if sources:
            print(f"   🔎 偵測到 {len(sources)} 個播放線路，嘗試切換...")
            for i in range(len(sources)):
                try:
                    # 重新獲取按鈕防止失效
                    current_sources = await page.query_selector_all(".play_source_tab a, .source-list a, .playlist_notfull li")
                    await current_sources[i].click()
                    await asyncio.sleep(5) # 每個線路給 5 秒加載 M3U8
                except:
                    continue
        else:
            # 如果沒有多線路按鈕，至少待 10 秒等待預設線路加載
            await asyncio.sleep(10)

        # 2. 最後掃描所有 frame 提取連結
        for frame in page.frames:
            try:
                content = await frame.content()
                found = re.findall(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', content)
                for link in found: m3u8_links.add(link)
            except: continue
            
    except Exception as e:
        print(f"⚠️ 第 {ep} 集解析異常: {e}")
    finally:
        page.remove_listener("request", handle_request)
    
    # 過濾掉明顯不是影片的連結 (可視需求調整)
    return sorted(list(m3u8_links))

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()

        # 偵測集數
        detail_url = f"https://{BASE_DOMAIN}/cn/{TARGET_ID}/"
        print(f"📡 前往詳情頁: {detail_url}")
        await page.goto(detail_url, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        content = await page.content()
        ep_list = sorted(list(set(map(int, re.findall(rf"/{TARGET_ID}/ep(\d+)\.html", content)))))

        if not ep_list:
            print("❌ 找不到集數"); await browser.close(); return

        print(f"✅ 找到 {len(ep_list)} 集，開始全量抓取...")

        # 覆寫模式寫入
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(f"--- 更新時間: {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")

        for ep in ep_list:
            links = await get_m3u8_for_ep(page, TARGET_ID, ep)
            with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                f.write(f"第 {ep} 集 ({len(links)} 個連結):\n")
                for link in links:
                    f.write(f"  - {link}\n")
            print(f"💾 第 {ep} 集完成，抓到 {len(links)} 個連結")
            await asyncio.sleep(random.uniform(1, 3))

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
