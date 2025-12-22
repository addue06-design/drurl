async def get_m3u8_for_ep(page, drama_id, ep):
    m3u8_links = set()
    play_url = f"https://{BASE_DOMAIN}/cn/{drama_id}/ep{ep}.html"
    
    def handle_request(req):
        if ".m3u8" in req.url.lower():
            m3u8_links.add(req.url)
    page.on("request", handle_request)

    try:
        print(f"🎬 正在全量解析第 {ep} 集所有線路...")
        await page.goto(play_url, wait_until="domcontentloaded", timeout=60000)
        
        # 1. 先抓取預設載入的線路
        await asyncio.sleep(5) 
        
        # 2. 尋找所有線路切換按鈕 (Dramaq 常見的線路按鈕特徵)
        # 這些按鈕通常在 .play_source_tab 或包含線路名稱的 li/a
        source_buttons = await page.query_selector_all(".play_source_tab a, .playlist_notfull li, .source-list a")
        
        if source_buttons:
            print(f"📡 偵測到 {len(source_buttons)} 個潛在片源線路，開始切換抓取...")
            for i in range(len(source_buttons)):
                try:
                    # 重新獲取元素以防頁面刷新導致失聯
                    btns = await page.query_selector_all(".play_source_tab a, .playlist_notfull li, .source-list a")
                    if i < len(btns):
                        await btns[i].click()
                        print(f"   - 切換至線路 {i+1}")
                        await asyncio.sleep(4) # 等待新線路加載 M3U8
                except:
                    continue
        
        # 3. 掃描所有 frame 提取連結
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
    
    # 過濾重複或無效的連結 (例如廣告)
    unique_links = [l for l in list(m3u8_links) if "cache" not in l or "m3u8" in l]
    return unique_links
