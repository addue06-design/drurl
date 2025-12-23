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
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            # 1. 載入全劇集頁面
            # 由於此頁面資料量大，我們給予較長的超時時間
            await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=90000)
            print("📄 頁面已載入，開始解析 DOM...")

            # 2. 提取所有符合 /detail/ID.html 格式的連結
            # 我們使用 evaluate 在瀏覽器端執行 JS，效率最高
            drama_data = await page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('a[href*="/detail/"]'));
                    return links.map(a => {
                        const title = a.innerText.trim();
                        const href = a.getAttribute('href');
                        const match = href.match(/\\/detail\\/(\\d+)\\.html/);
                        const id = match ? match[1] : null;
                        return { title, id };
                    }).filter(item => item.id && item.title);
                }
            """)

            if not drama_data:
                print("❌ 找不到任何劇集資料。")
                return

            print(f"✅ 成功提取 {len(drama_data)} 部影片資訊！")

            # 3. 寫入檔案
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                f.write(f"--- 劇集總表 (共 {len(drama_data)} 部) ---\n")
                # 按照 ID 排序或保持原始順序
                for item in drama_data:
                    f.write(f"名稱: {item['title']} | 代碼: {item['id']}\n")

            print(f"🏁 任務完成！清單已存至 {OUTPUT_FILE}")

        except Exception as e:
            print(f"💥 發生錯誤: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
