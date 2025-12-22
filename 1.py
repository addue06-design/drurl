import asyncio
import re
import os
from playwright.async_api import async_playwright

# --- 設定區域 ---
# 這裡可以放 "非凡" (中文) 或 "202500838" (數字代碼)
TARGET_INPUT = "202500838"  
# ------------------

async def get_m3u8_for_ep(page, drama_id, ep):
    """提取影片網址 (邏輯維持不變)"""
    m3u8_links = set()
    play_url = f"https://dramasq.io/vodplay/{drama_id}/ep{ep}.html"
    def handle_request(req):
        if ".m3u8" in req.url: m3u8_links.add(req.url)
    page.on("request", handle_request)
    
    try:
        print(f"🎬 正在解析第 {ep} 集...")
        await page.goto(play_url, wait_until="domcontentloaded", timeout=60000)
        for _ in range(12):
            for frame in page.frames:
                try:
                    content = await frame.content()
                    found = re.findall(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', content)
                    for link in found: m3u8_links.add(link)
                except: continue
            if m3u8_links: break
            await asyncio.sleep(1)
        if not m3u8_links:
            await page.mouse.click(640, 360)
            await asyncio.sleep(8)
    except Exception as e:
        print(f"⚠️ 解析跳過: {e}")
    finally:
        page.remove_listener("request", handle_request)
    return list(m3u8_links)

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()

        drama_id = None
        
        # --- 關鍵判別邏輯 ---
        if str(TARGET_INPUT).isdigit():
            # 1. 如果輸入全是數字，直接當作 ID
            drama_id = str(TARGET_INPUT)
            print(f"🔢 偵測到數字，直接使用代碼模式: {drama_id}")
        else:
            # 2. 如果是中文，才去 /all/ 頁面搜尋
            print(f"🔍 偵測到劇名，正在全劇清單搜尋: {TARGET_INPUT} ...")
            try:
                await page.goto("https://dramaq.xyz/all/", wait_until="domcontentloaded")
                links = await page.query_selector_all("a[href*='/detail/']")
                for link in links:
                    text = await link.inner_text()
                    title = await link.get_attribute("title") or ""
                    if TARGET_INPUT in text or TARGET_INPUT in title:
                        href = await link.get_attribute("href")
                        match = re.search(r'/detail/(\d+)\.html', href)
                        if match:
                            drama_id = match.group(1)
                            print(f"✅ 匹配成功: {text or title} (ID: {drama_id})")
                            break
            except Exception as e:
                print(f"❌ 搜尋出錯: {e}")

        if not drama_id:
            print(f"❌ 無法識別目標「{TARGET_INPUT}」"); await browser.close(); return

        # --- 後續執行提取 (自動偵測集數 + 增量更新) ---
        detail_url = f"https://dramasq.io/detail/{drama_id}.html"
        await page.goto(detail_url, wait_until="domcontentloaded")
        ep_links = await page.query_selector_all("a[href*='/vodplay/']")
        all_eps = [int(m.group(1)) for l in ep_links if (m := re.search(r'(\d+)', await l.inner_text()))]
        total_ep = max(all_eps) if all_eps else 1
        
        print(f"📊 總集數: {total_ep}，準備同步...")

        existing_eps = set()
        if os.path.exists("all_episodes_results.txt"):
            with open("all_episodes_results.txt", "r", encoding="utf-8") as f:
                existing_eps = set(map(int, re.findall(r'第 (\d+) 集', f.read())))

        for ep in range(1, total_ep + 1):
            if ep in existing_eps: continue
            links = await get_m3u8_for_ep(page, drama_id, ep)
            with open("all_episodes_results.txt", "a", encoding="utf-8") as f:
                f.write(f"第 {ep} 集: {', '.join(links) if links else '未找到'}\n")
            await asyncio.sleep(1)

        await browser.close()
        print("🏁 同步任務完成！")

if __name__ == "__main__":
    asyncio.run(run())
