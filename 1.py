import asyncio
import re
import os
from playwright.async_api import async_playwright

# --- 設定區域 ---
TARGET_INPUT = "非凡"  # 這裡可以放 "非凡" 或 "202500838"
# ------------------

async def get_m3u8_for_ep(page, drama_id, ep):
    """提取影片網址邏輯 (維持不變)"""
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
        # 增加 User-Agent 模擬真實使用者，避免被封鎖
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        drama_id = None
        
        # --- 強化判別邏輯 ---
        input_str = str(TARGET_INPUT).strip()
        if input_str.isdigit():
            drama_id = input_str
            print(f"🔢 代碼模式啟動: {drama_id}")
        else:
            print(f"🔍 劇名模式啟動，正在全劇清單搜尋: {input_str} ...")
            try:
                # 嘗試全劇清單頁面
                await page.goto("https://dramaq.xyz/all/", wait_until="networkidle", timeout=60000)
                await asyncio.sleep(3) # 多等 3 秒確保 JS 渲染
                
                # 獲取頁面上所有的 A 標籤
                links = await page.query_selector_all("a")
                print(f"ℹ️ 頁面掃描完成，共發現 {len(links)} 個連結，開始比對關鍵字...")
                
                for link in links:
                    # 抓取所有可能的辨識屬性
                    text = await link.inner_text() or ""
                    title = await link.get_attribute("title") or ""
                    href = await link.get_attribute("href") or ""
                    
                    # 只要關鍵字出現在文字或標題中
                    if input_str in text or input_str in title:
                        match = re.search(r'/detail/(\d+)\.html', href)
                        if match:
                            drama_id = match.group(1)
                            actual_name = text.strip() or title.strip()
                            print(f"✅ 匹配成功！劇名: 「{actual_name}」, 代碼: {drama_id}")
                            break
            except Exception as e:
                print(f"❌ 搜尋過程發生錯誤: {e}")

        if not drama_id:
            print(f"❌ 無法識別目標「{TARGET_INPUT}」。")
            print("💡 建議：如果劇名搜尋失敗，請手動前往網站複製該劇的代碼 (網址中的數字) 並填入 TARGET_INPUT。")
            await browser.close(); return

        # --- 自動偵測與抓取 ---
        detail_url = f"https://dramasq.io/detail/{drama_id}.html"
        await page.goto(detail_url, wait_until="domcontentloaded")
        
        # 抓取播放清單中的所有數字
        ep_links = await page.query_selector_all("a[href*='/vodplay/']")
        all_eps = []
        for l in ep_links:
            t = await l.inner_text()
            m = re.search(r'(\d+)', t)
            if m: all_eps.append(int(m.group(1)))
        
        total_ep = max(all_eps) if all_eps else 1
        print(f"📊 偵測完成：共 {total_ep} 集。開始進行增量同步...")

        # 讀取現有進度
        existing_eps = set()
        if os.path.exists("all_episodes_results.txt"):
            with open("all_episodes_results.txt", "r", encoding="utf-8") as f:
                existing_eps = set(map(int, re.findall(r'第 (\d+) 集', f.read())))

        for ep in range(1, total_ep + 1):
            if ep in existing_eps: continue
            
            links = await get_m3u8_for_ep(page, drama_id, ep)
            with open("all_episodes_results.txt", "a", encoding="utf-8") as f:
                if links:
                    f.write(f"第 {ep} 集: {', '.join(links)}\n")
                else:
                    f.write(f"第 {ep} 集: 抓取失敗\n")
            await asyncio.sleep(2)

        await browser.close()
        print("🏁 同步任務結束。")

if __name__ == "__main__":
    asyncio.run(run())
