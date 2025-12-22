import asyncio
import re
import os
from playwright.async_api import async_playwright

# --- 設定區域 ---
TARGET_INPUT = "5597942" 
# ------------------

async def get_m3u8_for_ep(page, drama_id, ep):
    m3u8_links = set()
    play_url = f"https://dramasq.io/vodplay/{drama_id}/ep{ep}.html"
    
    def handle_request(req):
        if ".m3u8" in req.url.lower():
            m3u8_links.add(req.url)
    
    page.on("request", handle_request)
    
    try:
        print(f"🎬 正在解析第 {ep} 集...")
        # 增加等待網路空閒，確保影片載入
        await page.goto(play_url, wait_until="networkidle", timeout=60000)
        
        # 嘗試從所有的 frame 內容中尋找
        for _ in range(10): 
            if m3u8_links: break
            for frame in page.frames:
                try:
                    content = await frame.content()
                    found = re.findall(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', content)
                    for link in found: m3u8_links.add(link)
                except: continue
            await asyncio.sleep(1.5) 
            
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

        drama_id = str(TARGET_INPUT).strip()
        
        # --- 自動偵測總集數 ---
        detail_url = f"https://dramasq.io/detail/{drama_id}.html"
        print(f"📡 正在從詳情頁偵測集數: {detail_url}")
        await page.goto(detail_url, wait_until="networkidle") # 改用 networkidle 確保列表載入
        
        # 等待播放連結出現
        await page.wait_for_selector("a[href*='/vodplay/']", timeout=15000)
        ep_links = await page.query_selector_all("a[href*='/vodplay/']")
        
        all_eps = set()
        for l in ep_links:
            t = await l.inner_text()
            m = re.search(r'(\d+)', t)
            if m: all_eps.add(int(m.group(1)))
        
        if not all_eps:
            print("❌ 無法偵測到集數，請確認代碼是否正確或頁面是否正常開啟。")
            await browser.close(); return

        total_ep = max(all_eps)
        print(f"📊 偵測完成：共 {total_ep} 集。開始全量抓取...")

        # 準備寫入檔案 (使用 'w' 模式清空舊資料)
        output_file = "all_episodes_results.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"--- 劇集 ID: {drama_id} 抓取結果 ---\n")

        for ep in range(1, total_ep + 1):
            links = await get_m3u8_for_ep(page, drama_id, ep)
            
            # 即時寫入每一集結果
            with open(output_file, "a", encoding="utf-8") as f:
                output = f"第 {ep} 集: {', '.join(links) if links else '未找到'}\n"
                f.write(output)
                print(f"✅ 第 {ep} 集解析完成")
            
            await asyncio.sleep(1) # 稍微緩衝，避免被網站封鎖

        await browser.close()
        print(f"🏁 同步結束！結果已儲存至 {output_file}")

if __name__ == "__main__":
    asyncio.run(run())
