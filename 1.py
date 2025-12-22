import asyncio
import re
from playwright.async_api import async_playwright

# --- 設定區域 ---
TARGET_INPUT = "風雨潮"  # 劇名或代碼
# ------------------

async def get_m3u8_for_ep(page, drama_id, ep):
    """專門負責抓取單一集數網址的函數"""
    m3u8_links = set()
    play_url = f"https://dramasq.io/vodplay/{drama_id}/ep{ep}.html"
    
    # 重新監聽請求（每一集都要重新收集）
    def handle_request(req):
        if ".m3u8" in req.url:
            m3u8_links.add(req.url)

    page.on("request", handle_request)
    
    try:
        print(f"🎬 正在解析第 {ep} 集...")
        await page.goto(play_url, wait_until="domcontentloaded", timeout=60000)
        
        # 深度掃描內容 (重複之前的成功邏輯)
        for _ in range(12):
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
            await asyncio.sleep(8)
            
    except Exception as e:
        print(f"⚠️ 第 {ep} 集解析跳過: {e}")
    finally:
        page.remove_listener("request", handle_request)
        
    return list(m3u8_links)

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()

        drama_id = TARGET_INPUT if TARGET_INPUT.isdigit() else None
        
        # 1. 如果是劇名，先找 ID
        if not drama_id:
            await page.goto("https://dramasq.io/type-tv/cn/", wait_until="domcontentloaded")
            links = await page.query_selector_all("a")
            for link in links:
                if TARGET_INPUT in (await link.inner_text()):
                    href = await link.get_attribute("href")
                    drama_id = re.search(r'/detail/(\d+)\.html', href).group(1)
                    break

        if not drama_id:
            print("❌ 找不到該劇集"); await browser.close(); return

        # 2. 自動偵測總集數
        detail_url = f"https://dramasq.io/detail/{drama_id}.html"
        await page.goto(detail_url, wait_until="domcontentloaded")
        ep_links = await page.query_selector_all("a[href*='/vodplay/']")
        all_eps = []
        for l in ep_links:
            text = await l.inner_text()
            num_match = re.search(r'(\d+)', text)
            if num_match: all_eps.append(int(num_match.group(1)))
        
        total_ep = max(all_eps) if all_eps else 1
        print(f"✅ 偵測完成：共有 {total_ep} 集")

        # 3. 迴圈抓取每一集
        final_results = []
        for ep in range(1, total_ep + 1):
            links = await get_m3u8_for_ep(page, drama_id, ep)
            final_results.append({"ep": ep, "links": links})
            # 存入檔案 (跑一集存一集，防止中斷)
            with open("all_episodes_results.txt", "a", encoding="utf-8") as f:
                f.write(f"第 {ep} 集: {', '.join(links) if links else '未找到'}\n")
            await asyncio.sleep(2) # 稍微休息避免被鎖

        await browser.close()
        print("🏁 全集抓取任務完成！")

if __name__ == "__main__":
    asyncio.run(run())
