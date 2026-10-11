import asyncio, os
from playwright.async_api import async_playwright
OUT="/workspace/upwork-portfolio"
URL="file:///workspace/inbox-triage-demo/demo.html"
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="chrome", headless=True, args=["--hide-scrollbars"])
        pg = await b.new_page(viewport={"width":1760,"height":1100}, device_scale_factor=1600/1760)
        await pg.goto(URL); await pg.wait_for_timeout(600)
        await pg.screenshot(path=f"{OUT}/15-triage-cover.png")
        # close view of a NOT SURE card (the smell-near-furnace one), 2x for crispness
        pg2 = await b.new_page(viewport={"width":1600,"height":1000}, device_scale_factor=2)
        await pg2.goto(URL); await pg2.wait_for_timeout(400)
        await pg2.click('.tab[data-tab="unsure"]'); await pg2.wait_for_timeout(300)
        el = pg2.locator("#mail-7"); await el.scroll_into_view_if_needed()
        await el.screenshot(path=f"{OUT}/16-triage-not-sure.png")
        al = pg2.locator("#alerts")
        await pg2.click('.tab[data-tab="all"]'); await pg2.evaluate("window.scrollTo(0,0)")
        await al.screenshot(path=f"{OUT}/17-triage-alerts.png")
        await b.close()
asyncio.run(main())
