import asyncio
from playwright.async_api import async_playwright

class VPSScraper:
    def __init__(self):
        self.browser = None
        self.context = None
        self.pages = []
        self.data_store = []
        self.is_running = False

    async def start_browser(self, total_tabs=11):
        """
        Launches browser and opens 'total_tabs' to cover the full list length.
        Defaults to 15 tabs to cover ~12-13 pages of data.
        """
        self.playwright = await async_playwright().start()
        
        # HEADLESS=TRUE is highly recommended for 15 tabs to save resources.
        # Set to False only if you have a powerful PC and want to debug.
        self.browser = await self.playwright.chromium.launch(headless=True)
        
        # Large viewport to minimize horizontal scrolling issues
        self.context = await self.browser.new_context(viewport={"width": 1920, "height": 1080})

        base_url = "https://banggia.vps.com.vn/chung-khoan/chung-quyen"
        print(f"Initializing {total_tabs} tabs to cover the full list...")

        for i in range(total_tabs):
            page = await self.context.new_page()
            
            try:
                # Go to page
                await page.goto(base_url, timeout=60000)
                
                # 1. Wait for rows to load
                try:
                    await page.wait_for_selector(".table-row", timeout=30000)
                except:
                    print(f"Tab {i+1}: Timeout waiting for data (retrying scrape later).")

                # 2. Calculate Scroll Position
                # We assume 1 'Page' is approx 800px height (roughly 20-25 rows).
                # Tab 1: 0px, Tab 2: 800px, Tab 13: 9600px...
                target_scroll = i * 800

                if target_scroll > 0:
                    print(f"Tab {i+1}: positioning at {target_scroll}px...")
                    
                    # JS Logic to force the internal container to scroll
                    await page.evaluate(f"""() => {{
                        const row = document.querySelector('.table-row');
                        if (!row) return;

                        let el = row.parentElement;
                        // Traverse up to find the scrollable container
                        while (el) {{
                            const style = window.getComputedStyle(el);
                            if ((el.scrollHeight > el.clientHeight) && 
                                (style.overflowY === 'auto' || style.overflowY === 'scroll' || style.overflow === 'auto')) {{
                                
                                el.scrollTop = {target_scroll}; 
                                return;
                            }}
                            el = el.parentElement;
                        }}
                        // Fallback
                        window.scrollTo(0, {target_scroll});
                    }}""")
                    
                    # Brief wait for virtual rows to render
                    await asyncio.sleep(1)

            except Exception as e:
                print(f"Tab {i+1} error: {e}")

            self.pages.append(page)
            
            # CRITICAL: Stagger the launches. 
            # Opening 15 tabs instantly usually crashes the connection or CPU.
            await asyncio.sleep(1.5)

        self.is_running = True
        print(f"All {total_tabs} tabs launched. Starting continuous updates...")

    async def scrape_loop(self):
        while self.is_running:
            temp_data = []
            
            # Scrape all tabs
            for index, page in enumerate(self.pages):
                try:
                    page_data = await page.evaluate("""() => {
                        const rows = Array.from(document.querySelectorAll('.table-row'));
                        return rows.map(row => {
                            const cells = Array.from(row.querySelectorAll('span'));
                            if (cells.length === 0) return null;
                            
                            // Adjust indices based on visual check of VPS
                            // Typically: Symbol, Issuer, ... Price ...
                            return {
                                symbol: cells[0]?.innerText?.trim() || "",
                                issuer: cells[8]?.innerText?.trim() || "",
                                price: cells[9]?.innerText?.trim() || "",
                                volume: cells[10]?.innerText?.trim() || "",
                                change: cells[11]?.innerText?.trim() || "",
                            };
                        }).filter(item => item !== null && item.symbol !== ""); 
                    }""")
                    
                    if page_data:
                        for item in page_data:
                            item['source_page'] = index + 1
                        temp_data.extend(page_data)
                    
                except Exception as e:
                    # Tabs might be reloading or busy
                    pass

            # Deduplicate Logic
            # Since Tab 1 (0-800px) and Tab 2 (800-1600px) might overlap,
            # we use a dictionary keyed by 'symbol' to keep only unique rows.
            unique_data = {item['symbol']: item for item in temp_data}
            
            # Convert back to list and sort (optional, e.g., by Symbol)
            self.data_store = list(unique_data.values())
            
            # Wait 1 second before next update cycle
            await asyncio.sleep(1)

    async def stop(self):
        self.is_running = False
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()