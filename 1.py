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
    # 修正：.xyz 的播放頁網址通常是 /cn/ID/EP.html
    play_url = f"https://{BASE_DOMAIN}/cn/{drama_id}/{ep}.html"
    
    def handle_request(req):
        if ".m3u8" in req.url.lower():
            m3u8_links.add(req.url)
    page.on("request", handle_request)

    try:
        print(f"🎬 正在解析第 {ep} 集: {play_url}")
        # 增加隨機 User-Agent 避免被擋
        await page.goto(play_url, wait_until="commit", timeout=60000)
        
        # 關鍵：.xyz 經常需要手動點擊或等待 iframe 真正載入
        for _ in range(15):
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
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # 1. 直接前往你提供的網址
        detail_url = f"https://{BASE_DOMAIN}/cn/{TARGET_ID}/"
        print(f"📡 前往詳情頁: {detail_url}")
        
        await page.goto(detail_url, wait_until="domcontentloaded")
        
        # 2. 修正偵測邏輯：.xyz 的集數連結通常在特定的 class 或包含數字的 .html
        # 我們抓取所有 href 格式為 /cn/ID/數字.html 的連結
        await asyncio.sleep(3) # 等待 JavaScript 渲染列表
        
        href_pattern = f"/cn/{TARGET_ID}/"
        links = await page.query_selector_all(f"a[href^='{href_pattern}']")
        
        all_eps = set()
        for l in links:
            href = await l.get_attribute("href")
            # 提取如 /cn/5597942/1.html 中的 '1'
            match = re.search(r'/(\d+)\.html$', href)
            if match:
                all_eps.add(int(match.group(1)))
        
        if not all_eps:
            print("❌ 無法偵測到集數列表，嘗試備用方案...")
            # 備用方案：直接找文字包含數字的連結
            elements = await page.query_selector_all("ul li a")
            for el in elements:
                t = await el.inner_text()
                if t.isdigit(): all_eps.add(int(t))

        if not all_eps:
            print("❌ 依然找不到集數，請檢查網頁是否被 Cloudflare 阻擋。")
            await browser.close(); return

        total_ep = max(all_eps)
        print(f"📊 偵測完成：共 {total_ep} 集 ({sorted(list(all_eps))})")

        # 3. 執行全量或增量抓取
        output_file = "all_episodes_results.txt"
        for ep in range(1, total_ep + 1):
            # 檢查是否已存在
            existing_eps = set()
            if os.path.exists(output_file):
                with open(output_file, "r", encoding="utf-8") as f:
                    existing_eps = set(map(int, re.findall(r'第 (\d+) 集', f.read())))
            
            if ep in existing_eps:
                print(f"⏭️ 第 {ep} 集已跳過")
                continue

            links = await get_m3u8_for_ep(page, TARGET_ID, ep)
            with open(output_file, "a", encoding="utf-8") as f:
                f.write(f"第 {ep} 集: {', '.join(links) if links else '未找到'}\n")
            
            await asyncio.sleep(random.uniform(2, 5))

        await browser.close()
        print("🏁 同步結束！")

if __name__ == "__main__":
    asyncio.run(run())
