import asyncio
import re
import os
from playwright.async_api import async_playwright

# --- 設定區域 ---
# 如果是數字，系統會直接進入代碼模式；如果是文字，會去 /all/ 搜尋
TARGET_INPUT = "202500838"  
DOMAIN = "dramaq.xyz" # 建議使用主站搜尋
# ------------------

async def get_m3u8_for_ep(page, drama_id, ep):
    """提取影片網址"""
    m3u8_links = set()
    # 播放頁通常在 dramasq.io
    play_url = f"https://dramasq.io/vodplay/{drama_id}/ep{ep}.html"
    
    def handle_request(req):
        if ".m3u8" in req.url.lower():
            m3u8_links.add(req.url)

    page.on("request", handle_request)

    try:
        print(f"🎬 正在解析第 {ep} 集...")
        # 使用 networkidle 較能確保 iframe 內的影片載入
        await page.goto(play_url, wait_until="commit", timeout=60000)
        
        # 等待影片插件載入
        for _ in range(15):
            if m3u8_links: break
            for frame in page.frames:
                try:
                    content = await frame.content()
                    found = re.findall(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', content)
                    for link in found: m3u8_links.add(link)
                except: continue
            await asyncio.sleep(1.5)
            
        # 如果還是沒找到，嘗試點擊播放器區域觸發請求
        if not m3u8_links:
            await page.mouse.click(640, 360)
            await asyncio.sleep(5)
            
    except Exception as e:
        print(f"⚠️ 第 {ep} 集解析異常: {e}")
    finally:
        page.remove_listener("request", handle_request)
        
    return list(m3u8_links)

async def run():
    async with async_playwright() as p:
        # 啟動瀏覽器 (修正原本漏掉的啟動碼)
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        drama_id = None
        input_str = str(TARGET_INPUT).strip()

        # --- 1. 識別輸入內容 ---
        if input_str.isdigit():
            drama_id = input_str
            print(f"🔢 代碼模式: {drama_id}")
        else:
            print(f"🔍 劇名模式: 正在搜尋「{input_str}」...")
            try:
                await page.goto(f"https://{DOMAIN}/all/", wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_selector("a[href*='/detail/']")
                links = await page.query_selector_all("a[href*='/detail/']")
                
                for link in links:
                    text = (await link.inner_text() or "").strip()
                    title = (await link.get_attribute("title") or "").strip()
                    if input_str in text or input_str in title:
                        href = await link.get_attribute("href")
                        match = re.search(r'/detail/(\d+)\.html', href)
                        if match:
                            drama_id = match.group(1)
                            print(f"✅ 匹配成功: {text} (ID: {drama_id})")
                            break
            except Exception as e:
                print(f"❌ 搜尋過程發生錯誤: {e}")

        if not drama_id:
            print(f"❌ 無法識別或找不到: {TARGET_INPUT}")
            await browser.close(); return

        # --- 2. 自動偵測總集數 ---
        detail_url = f"https://dramasq.io/detail/{drama_id}.html"
        await page.goto(detail_url, wait_until="domcontentloaded")
        
        # 確保集數列表已載入
        try:
            await page.wait_for_selector("a[href*='/vodplay/']", timeout=10000)
            ep_links = await page.query_selector_all("a[href*='/vodplay/']")
            all_eps = []
            for l in ep_links:
                t = await l.inner_text()
                m = re.search(r'(\d+)', t)
                if m: all_eps.append(int(m.group(1)))
            
            total_ep = max(all_eps) if all_eps else 1
        except:
            total_ep = 1

        print(f"📊 偵測完成：共 {total_ep} 集。")

        # --- 3. 執行抓取 ---
        output_file = "all_episodes_results.txt"
        # 讀取現有進度
        existing_eps = set()
        if os.path.exists(output_file):
            with open(output_file, "r", encoding="utf-8") as f:
                existing_eps = set(map(int, re.findall(r'第 (\d+) 集', f.read())))

        for ep in range(1, total_ep + 1):
#            if ep in existing_eps:
 #               print(f"⏭️ 第 {ep} 集已存在，跳過。")
  #              continue
                
            links = await get_m3u8_for_ep(page, drama_id, ep)
            with open(output_file, "a", encoding="utf-8") as f:
                f.write(f"第 {ep} 集: {', '.join(links) if links else '未找到'}\n")
            
            await asyncio.sleep(random.uniform(1, 3) if 'random' in globals() else 2)

        await browser.close()
        print("🏁 同步任務完成！")

if __name__ == "__main__":
    asyncio.run(run())
