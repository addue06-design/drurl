import asyncio
import re
from playwright.async_api import async_playwright

# --- 設定區域 ---
TARGET_URL = "https://dramaq.xyz/all/"
OUTPUT_FILE = "drama_list.txt"
# ------------------

async def run():
    async with async_playwright() as p:
        print(f"📡 正在啟動瀏覽器並前往: {TARGET_URL}")
        browser = await p.chromium.launch(headless=True)
        # 模擬更真實的瀏覽器環境
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            # 1. 載入頁面，使用 networkidle 確保資料載入完成
            await page.goto(TARGET_URL, wait_until="networkidle", timeout=120000)
            print("📄 頁面初步載入完成，正在模擬捲動以確保所有非同步內容加載...")

            # 2. 模擬捲動頁面 (有些頁面是 lazy load)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(5) 

            # 3. 提取資料：改用更寬鬆的 Regex 匹配 href
            # 有些連結可能是絕對路徑，有些是相對路徑，我們統一處理
            drama_data = await page.evaluate("""
                () => {
                    const results = [];
                    // 掃描頁面上所有的 <a> 標籤
                    const links = document.querySelectorAll('a');
                    
                    links.forEach(a => {
                        const href = a.href || "";
                        const text = a.innerText.trim();
                        
                        // 匹配 /detail/12345.html 或 /cn/12345/ 這種格式
                        // 針對你提供的特定結構進行匹配
                        const match = href.match(/\\/(?:detail|cn)\\/(\\d+)\\/?/);
                        
                        if (match && text && text.length > 0) {
                            results.push({
                                title: text,
                                id: match[1]
                            });
                        }
                    });
                    return results;
                }
            """)

            # 4. 去除重複項 (同一個 ID 可能出現在不同的導覽位置)
            unique_dramas = {}
            for item in drama_data:
                unique_dramas[item['id']] = item['title']

            if not unique_dramas:
                print("❌ 依然找不到任何劇集資料。嘗試印出頁面標題確認狀態...")
                print(f"目前頁面標題: {await page.title()}")
                # 存下除錯截圖
                await page.screenshot(path="debug_list_page.png")
                return

            print(f"✅ 成功提取 {len(unique_dramas)} 部影片資訊！")

            # 5. 寫入檔案
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                f.write(f"--- 劇集總表 (共 {len(unique_dramas)} 部) ---\n")
                for drama_id, title in sorted(unique_dramas.items(), key=lambda x: x[0]):
                    f.write(f"名稱: {title} | 代碼: {drama_id}\n")

            print(f"🏁 任務完成！清單已存至 {OUTPUT_FILE}")

        except Exception as e:
            print(f"💥 發生錯誤: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
