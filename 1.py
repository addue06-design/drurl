import asyncio
import re
import os
import time
from playwright.async_api import async_playwright

# --- 設定區域 ---
TARGET_ID = "202587131"  # 你提供的最新 ID
BASE_DOMAIN = "dramasq.io"
OUTPUT_FILE = "all_episodes_results.txt"
# ------------------

async def get_m3u8_for_ep(page, drama_id, ep):
    results = []
    play_url = f"https://{BASE_DOMAIN}/vodplay/{drama_id}/ep{ep}.html"
    
    try:
        print(f"🎬 正在解析第 {ep} 集: {play_url}")
        # 只需要加載 DOM 即可，不用等網路閒置
        await page.goto(play_url, wait_until="domcontentloaded", timeout=60000)
        
        # 使用 JavaScript 直接提取所有包含 v_data 的 a 標籤資訊
        sources = await page.evaluate("""
            () => {
                const links = Array.from(document.querySelectorAll('a[v_data]'));
                return links.map(a => ({
                    name: a.querySelector('strong') ? a.querySelector('strong').innerText : '未知片源',
                    cloud: a.querySelector('small') ? a.querySelector('small').innerText : '',
                    url: a.getAttribute('v_data')
                }));
            }
        """)
        
        for s in sources:
            results.append(f"{s['name']}({s['cloud']}): {s['url']}")
            
    except Exception as e:
        print(f"⚠️ 第 {ep} 集解析異常: {e}")
        
    return results

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        page = await context.new_page()

        # 1. 偵測總集數
        detail_url = f"https://{BASE_DOMAIN}/detail/{TARGET_ID}.html"
        print(f"📡 偵測詳情頁: {detail_url}")
        await page.goto(detail_url, wait_until="domcontentloaded")
        
        # 提取所有 ep{N}.html 的數字
        content = await page.content()
        ep_numbers = [int(n) for n in re.findall(rf"/{TARGET_ID}/ep(\d+)\.html", content)]
        
        if not ep_numbers:
            # 備用方案：如果沒抓到，嘗試直接從播放按鈕文字抓
            ep_links = await page.query_selector_all("a[href*='/ep']")
            for link in ep_links:
                text = await link.inner_text()
                num = re.search(r'(\d+)', text)
                if num: ep_numbers.append(int(num.group(1)))

        if not ep_numbers:
            print("❌ 找不到集數列表"); await browser.close(); return

        ep_list = sorted(list(set(ep_numbers)))
        print(f"✅ 偵測成功：共 {len(ep_list)} 集 (清單: {ep_list})")

        # 2. 全量覆蓋寫入
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(f"--- 劇集 ID: {TARGET_ID} 全量同步 ({time.strftime('%Y-%m-%d %H:%M:%S')}) ---\n")

        # 3. 逐集提取所有片源
        for ep in ep_list:
            sources = await get_m3u8_for_ep(page, TARGET_ID, ep)
            
            with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                f.write(f"\n第 {ep} 集 (共 {len(sources)} 個片源):\n")
                if sources:
                    for s in sources:
                        f.write(f"  - {s}\n")
                else:
                    f.write("  - (未找到片源)\n")
            
            print(f"💾 第 {ep} 集完成，抓到 {len(sources)} 個片源")
            await asyncio.sleep(1) # 這種方法很快，不需要等太久

        await browser.close()
        print(f"🏁 任務完成！結果已存至 {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(run())
