import asyncio
import re
import os
from playwright.async_api import async_playwright

async def get_dramasq_m3u8_github_ver(drama_id, ep=5):
    m3u8_links = set()
    play_url = f"https://dramasq.io/vodplay/{drama_id}/ep{ep}.html"
    
    async with async_playwright() as p:
        print(f"🚀 啟動深度解析: {play_url}")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 720}
        )
        page = await context.new_page()

        # 1. 監聽網路封包
        page.on("request", lambda request: m3u8_links.add(request.url) if ".m3u8" in request.url else None)

        try:
            # 2. 訪問頁面
            await page.goto(play_url, wait_until="domcontentloaded", timeout=60000)
            
            # 3. 深度掃描所有 Frames 的內容 (你原本最強的邏輯)
            print("🔍 正在掃描頁面內所有框架內容...")
            for _ in range(15):  # 延長到 15 秒，確保雲端加載完成
                for frame in page.frames:
                    try:
                        content = await frame.content()
                        # 正則抓取隱藏網址
                        found = re.findall(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', content)
                        for link in found:
                            # 排除掉廣告或無效的連結
                            if "m3u8" in link:
                                m3u8_links.add(link)
                    except:
                        continue
                
                if m3u8_links: break
                await asyncio.sleep(1)

            # 4. 如果還是沒找到，嘗試模擬點擊觸發請求
            if not m3u8_links:
                print("🖱 未偵測到流媒體，嘗試模擬點擊播放器中央...")
                await page.mouse.click(640, 360)
                await asyncio.sleep(10)

            # 5. 將結果寫入檔案，讓 GitHub Actions 能存回去
            with open("action_report.txt", "w", encoding="utf-8") as f:
                if m3u8_links:
                    f.write(f"✅ 成功提取網址 (非凡 EP{ep}):\n")
                    for link in m3u8_links:
                        f.write(f"{link}\n")
                    print(f"✅ 找到 {len(m3u8_links)} 個連結")
                else:
                    f.write(f"❌ 解析失敗。頁面標題: {await page.title()}\n")
                    print("❌ 依舊解析失敗")

        except Exception as e:
            print(f"❌ 程式執行異常: {e}")
            with open("action_report.txt", "w") as f:
                f.write(f"💥 錯誤: {str(e)}")
        finally:
            await browser.close()

if __name__ == "__main__":
    # 執行非凡第 5 集測試
    asyncio.run(get_dramasq_m3u8_github_ver("202500838", ep=5))
