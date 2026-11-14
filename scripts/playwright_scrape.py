import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://www.turnpikeanalyst.com/blog-posts/page/2/')
        await page.wait_for_timeout(5000)
        links = await page.eval_on_selector_all('a', 'nodes => nodes.map(n => ({href: n.href, text: n.innerText}))')
        for l in links:
            if 'turnpikeanalyst.com' in l['href'] and l['text'].strip():
                print(l['href'], repr(l['text']))
        await browser.close()

asyncio.run(main())
