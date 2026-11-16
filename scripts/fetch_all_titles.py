import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        titles = []
        for p_num in [1, 2, 3]:
            url = f'https://www.turnpikeanalyst.com/blog-posts/' if p_num == 1 else f'https://www.turnpikeanalyst.com/blog-posts/page/{p_num}/'
            await page.goto(url)
            await page.wait_for_timeout(3000)
            # We just need the titles to generate content
            links = await page.eval_on_selector_all('a', 'nodes => nodes.map(n => ({href: n.href, text: n.innerText}))')
            for l in links:
                if 'turnpikeanalyst.com' in l['href'] and l['text'].strip() and 'Read More' not in l['text']:
                    titles.append(l['text'].strip())
            
        print("Found titles:", set(titles))
        await browser.close()

asyncio.run(main())
