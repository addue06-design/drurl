import asyncio
import re
from playwright.async_api import async_playwright

# --- 設定區域 ---
TARGET_DRAMA_NAME = "風雨潮"  # 想要抓取影片網址的劇名
TARGET_EP = 23              # 想要抓取的集數
# ----------------

async def run_integrated_scraper():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 720}
        )
        page = await context.new_page()

        # --- 第一階段：提取劇集清單 ---
        list_url = "https://dramasq.io/type-tv/cn/"
        print(f"📂 正在掃描清單獲取代碼: {list_url}")
        
        drama_map = {} # 用來存放 {劇名: 代碼}
        try:
            await page.goto(list_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)
            
            links = await page.query_selector_all("a")
            for link in links:
                href = await link.get_attribute("href")
                title = await link.get_attribute("title")
                text = await link.inner_text()
                
                # 匹配 /detail/數字.html
                match = re.search(r'/detail/(\d+)\.html', href or "")
                if match:
                    d_id = match.group(1)
                    d_name = (title or text).strip()
                    if d_name and not d_name.isdigit() and "EP" not in d_name:
                        drama_map[d_name] = d_id
            
            # 儲存清單到檔案
            with open("all_dramas.txt", "w", encoding="utf-8") as f:
                for name, d_id in drama_map.items():
                    f.write(f"{name} : {d_id}\n")
            print(f"✅ 已成功更新劇集清單，共 {len(drama_map)} 部。")

        except Exception as e:
            print(f"❌ 清單掃描出錯: {e}")

        # --- 第二階段：提取指定劇集的影片網址 ---
        # 檢查清單中是否有我們想要的劇
        target_id = drama_map.get(TARGET_DRAMA_NAME)
        
        if target_id:
            play_url = f"https://dramasq.io/vodplay/{target_id}/ep{TARGET_EP}.html"
            print(f"🚀 啟動深度解析影片: {play_url}")
            
            m3u8_links = set()
            page.on("request", lambda req: m3u8_links.add(req.url) if ".m3u8" in req.url else None)
            
            try:
                await page.goto(play_url, wait_until="domcontentloaded", timeout=60000)
                
                # 深度掃描 Frame 內容 (你之前成功的邏輯)
                for _ in range(15):
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
                    await asyncio.sleep(10)

                # 儲存影片網址到檔案
                with open("video_results.txt", "w", encoding="utf-8") as f:
                    if m3u8_links:
                        f.write(f"【{TARGET_DRAMA_NAME}】第 {TARGET_EP} 集 m3u8 網址:\n")
                        for link in m3u8_links:
                            f.write(f"{link}\n")
                    else:
                        f.write(f"❌ 未能找到 【{TARGET_DRAMA_NAME}】 的影片網址。")
                print(f"✅ 影片網址解析完成，請查看 video_results.txt")

            except Exception as e:
                print(f"❌ 影片解析出錯: {e}")
        else:
            print(f"⚠️ 在清單中找不到劇名: {TARGET_DRAMA_NAME}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_integrated_scraper())
