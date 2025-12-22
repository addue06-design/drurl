from playwright.async_api import async_playwright

# --- 設定區域 ---
# 這裡現在可以放 "非凡" (中文) 或 "202500838" (數字代碼)
TARGET_INPUT = "非凡"  
# 這裡可以放 "非凡" (中文) 或 "202500838" (數字代碼)
TARGET_INPUT = "202500838"  
# ------------------

async def get_m3u8_for_ep(page, drama_id, ep):
    """提取影片網址 (邏輯維持不變)"""
    m3u8_links = set()
    play_url = f"https://dramasq.io/vodplay/{drama_id}/ep{ep}.html"
    
    def handle_request(req):
        if ".m3u8" in req.url:
            m3u8_links.add(req.url)

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
                    for link in found:
                        m3u8_links.add(link)
                    for link in found: m3u8_links.add(link)
                except: continue
            if m3u8_links: break
            await asyncio.sleep(1)
            
        if not m3u8_links:
            await page.mouse.click(640, 360)
            await asyncio.sleep(8)
            
    except Exception as e:
        print(f"⚠️ 第 {ep} 集解析跳過: {e}")
        print(f"⚠️ 解析跳過: {e}")
    finally:
        page.remove_listener("request", handle_request)
        
    return list(m3u8_links)

async def run():

        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()

        drama_id = TARGET_INPUT if TARGET_INPUT.isdigit() else None
        drama_id = None

        # --- 1. 強化版搜尋邏輯 (支持中文字) ---
        if not drama_id:
            print(f"🔍 正在搜尋劇名: {TARGET_INPUT}...")
            # 掃描前 3 頁，防止新劇不在第一頁
            found_id = False
            for page_num in range(1, 4):
                search_url = f"https://dramasq.io/type-tv/cn/page/{page_num}.html"
                await page.goto(search_url, wait_until="domcontentloaded")
                
                # 抓取所有包含 detail 的連結
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
                            print(f"✅ 成功找到劇集: {text or title} (ID: {drama_id})")
                            found_id = True
                            print(f"✅ 匹配成功: {text or title} (ID: {drama_id})")
                            break
                if found_id: break
                print(f"第 {page_num} 頁未找到，繼續搜尋...")
            except Exception as e:
                print(f"❌ 搜尋出錯: {e}")

        if not drama_id:
            print(f"❌ 找不到劇名「{TARGET_INPUT}」，請確認名稱正確或改用數字代碼。")
            await browser.close(); return
            print(f"❌ 無法識別目標「{TARGET_INPUT}」"); await browser.close(); return

        # --- 2. 自動偵測總集數 ---
        # --- 後續執行提取 (自動偵測集數 + 增量更新) ---
        detail_url = f"https://dramasq.io/detail/{drama_id}.html"
        await page.goto(detail_url, wait_until="domcontentloaded")
        # 針對 DramasQ 的結構優化選擇器
        ep_links = await page.query_selector_all(".stui-content__playlist a, a[href*='/vodplay/']")
        
        all_eps = []
        for l in ep_links:
            text = await l.inner_text()
            num_match = re.search(r'(\d+)', text)
            if num_match: all_eps.append(int(num_match.group(1)))
        
        ep_links = await page.query_selector_all("a[href*='/vodplay/']")
        all_eps = [int(m.group(1)) for l in ep_links if (m := re.search(r'(\d+)', await l.inner_text()))]
        total_ep = max(all_eps) if all_eps else 1
        print(f"📊 偵測完成：共有 {total_ep} 集")
        
        print(f"📊 總集數: {total_ep}，準備同步...")

        # --- 3. 迴圈抓取 ---
        # 讀取已存在的集數，避免重複 (選擇性)
        existing_eps = set()
        if os.path.exists("alll_episodes_results.txt"):
            with open("all_episodes_results.txt", "r", encoding="utf-8") as f:
                done_eps = re.findall(r'第 (\d+) 集', f.read())
                done_eps = set(map(int, done_eps))
        else:
            done_eps = set()
                existing_eps = set(map(int, re.findall(r'第 (\d+) 集', f.read())))

        for ep in range(1, total_ep + 1):
            if ep in done_eps:
                print(f"⏭️ 第 {ep} 集已存在，跳過。")
                continue
                
            if ep in existing_eps: continue
            links = await get_m3u8_for_ep(page, drama_id, ep)
            with open("all_episodes_results.txt", "a", encoding="utf-8") as f:
                f.write(f"第 {ep} 集: {', '.join(links) if links else '未找到'}\n")
            await asyncio.sleep(2)
            await asyncio.sleep(1)

        await browser.close()
        print("🏁 任務完成！")
        print("🏁 同步任務完成！")

if __name__ == "__main__":
    asyncio.run(run())
