import asyncio
import re
import os
from playwright.async_api import async_playwright

# --- 設定區域 ---
TARGET_INPUT = "非凡"  # 這裡可以放劇名或代碼
# ------------------

async def get_m3u8_for_ep(page, drama_id, ep):
    """提取影片網址邏輯"""
    m3u8_links = set()
    play_url = f"https://dramasq.io/vodplay/{drama_id}/ep{ep}.html"
    def handle_request(req):
        if ".m3u8" in req.url: m3u8_links.add(req.url)
    page.on("request", handle_request)
    
    try:
        print(f"🎬 正在解析第 {ep} 集...")
        await page.goto(play_url, wait_until="domcontentloaded", timeout=60000)
        for _ in range(15):
            for frame in page.frames:
                try:
                    content = await frame.content()
                    found = re.findall(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', content)
                    for link in found: m3u8_links.add(link)
                except: continue
            if m3u8_links: break
            await asyncio.sleep(1)
    except Exception as e:
        print(f"⚠️ 第 {ep} 集解析異常: {e}")
    finally:
        page.remove_listener("request", handle_request)
    return list(m3u8_links)

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        drama_id = None
        input_str = str(TARGET_INPUT).strip()

        # --- 雙軌搜尋邏輯 ---
        if input_str.isdigit():
            drama_id = input_str
            print(f"🔢 代碼模式: {drama_id}")
        else:
            print(f"🔍 劇名模式: 正在全劇清單搜尋「{input_str}」...")
            try:
                # 1. 前往總清單
                await page.goto("https://dramaq.xyz/all/", wait_until="domcontentloaded", timeout=60000)
                # 2. 縮小範圍，只抓取 detail 的 a 標籤
                links = await page.query_selector_all("a[href*='/detail/']")
                
                for link in links:
                    text = (await link.inner_text() or "").strip()
                    title = (await link.get_attribute("title") or "").strip()
                    href = (await link.get_attribute("href") or "")
                    
                    # 3. 模糊比對（忽略空格，支援包含關係）
                    combined_source = (text + title).replace(" ", "")
                    target_clean = input_str.replace(" ", "")
                    
                    if target_clean in combined_source:
                        match = re.search(r'/detail/(\d+)\.html', href)
                        if match:
                            drama_id = match.group(1)
                            print(f"✅ 成功命中: 「{text or title}」 (ID: {drama_id})")
                            break
            except Exception as e:
                print(f"❌ 搜尋過程發生錯誤: {e}")

        if not drama_id:
            print(f"❌ 搜尋不到「{TARGET_INPUT}」。請確認劇名是否正確或直接改用代碼。")
            await browser.close(); return

        # --- 自動偵測總集數 ---
        await page.goto(f"https://dramasq.io/detail/{drama_id}.html", wait_until="domcontentloaded")
        ep_links = await page.query_selector_all("a[href*='/vodplay/']")
        all_eps = []
        for l in ep_links:
            t = await l.inner_text()
            m = re.search(r'(\d+)', t)
            if m: all_eps.append(int(m.group(1)))
        
        total_ep = max(all_eps) if all_eps else 1
        print(f"📊 偵測完成：共 {total_ep} 集。開始增量同步...")

        # 增量寫入邏輯
        existing_eps = set()
        if os.path.exists("all_episodes_results.txt"):
            with open("all_episodes_results.txt", "r", encoding="utf-8") as f:
                existing_eps = set(map(int, re.findall(r'第 (\d+) 集', f.read())))

        for ep in range(1, total_ep + 1):
            if ep in existing_eps:
                print(f"⏭️ 第 {ep} 集已存在，跳過。")
                continue
            
            links = await get_m3u8_for_ep(page, drama_id, ep)
            with open("all_episodes_results.txt", "a", encoding="utf-8") as f:
                f.write(f"第 {ep} 集: {', '.join(links) if links else '未找到'}\n")
            await asyncio.sleep(2)

        await browser.close()
        print("🏁 同步結束！")

if __name__ == "__main__":
    asyncio.run(run())
