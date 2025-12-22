import asyncio
import re
import os
from playwright.async_api import async_playwright

# --- 靈活設定區域 ---
# 這裡可以輸入劇名 "非凡" 或代碼 "202500838"
TARGET_INPUT = "非凡"  
# ------------------

async def get_existing_eps():
    if not os.path.exists("all_episodes_results.txt"): return set()
    with open("all_episodes_results.txt", "r", encoding="utf-8") as f:
        content = f.read()
    return set(map(int, re.findall(r'第 (\d+) 集', content)))

async def run():
    existing_eps = await get_existing_eps()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()

        drama_id = None
        drama_name = "未知劇集"

        # --- 修正後的判別邏輯 ---
        if TARGET_INPUT.isdigit():
            drama_id = TARGET_INPUT
            print(f"🔢 使用代碼模式: {drama_id}")
        else:
            print(f"🔍 使用劇名模式，搜尋中: {TARGET_INPUT}")
            # 遍歷陸劇清單頁面 (可能需要掃描多個地方，這裡先抓主分頁)
            await page.goto("https://dramasq.io/type-tv/cn/", wait_until="domcontentloaded")
            
            # 強化的搜尋邏輯：檢查所有 a 標籤的文字與 title 屬性
            elements = await page.query_selector_all("a[href*='/detail/']")
            for el in elements:
                text = await el.inner_text()
                title = await el.get_attribute("title") or ""
                href = await el.get_attribute("href") or ""
                
                if TARGET_INPUT in text or TARGET_INPUT in title:
                    match = re.search(r'/detail/(\d+)\.html', href)
                    if match:
                        drama_id = match.group(1)
                        drama_name = text.strip() or title.strip()
                        print(f"✅ 成功匹配: {drama_name} -> ID: {drama_id}")
                        break

        if not drama_id:
            print(f"❌ 找不到與 '{TARGET_INPUT}' 相關的劇集，請檢查名稱。")
            await browser.close(); return

        # --- 自動偵測總集數 ---
        detail_url = f"https://dramasq.io/detail/{drama_id}.html"
        await page.goto(detail_url, wait_until="domcontentloaded")
        
        # 這裡改用更準確的選擇器來抓播放按鈕
        ep_elements = await page.query_selector_all("ul.stui-content__playlist a")
        all_eps = []
        for el in ep_elements:
            text = await el.inner_text()
            num_match = re.search(r'(\d+)', text)
            if num_match: all_eps.append(int(num_match.group(1)))
        
        total_ep = max(all_eps) if all_eps else 0
        print(f"📊 偵測到總集數: {total_ep}")

        # --- 循環抓取新集數 ---
        new_eps = [e for e in range(1, total_ep + 1) if e not in existing_eps]
        
        for ep in new_eps:
            # (這裡插入你之前成功的 m3u8 提取邏輯...)
            print(f"🚀 正在抓取第 {ep} 集...")
            # ... 執行抓取並寫入 all_episodes_results.txt ...

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
