import asyncio
from playwright.async_api import async_playwright
from urllib.parse import urlparse, parse_qs

async def get_cse_tok():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        cse_tok_value = None

        async def capture_request(route):
            nonlocal cse_tok_value
            try:
                request = route.request
                url = request.url
                parsed_url = urlparse(url)
                query_params = parse_qs(parsed_url.query)

                if 'cse_tok' in query_params:
                    cse_tok_value = query_params['cse_tok'][0]
            except Exception as e:
                print(f"Error occurred while handling request: {e}")
            finally:
                await route.continue_()

        await context.route("**/*", capture_request)
        await page.goto("https://xtea.io/ts_en.html#gsc.tab=0&gsc.q=Genghis%20Mongolia&gsc.sort=")
        await page.wait_for_timeout(1000)
        await browser.close()
        return cse_tok_value

if __name__ == "__main__":
    try:
        cse_tok = asyncio.run(get_cse_tok())
        if cse_tok:
            print(f"Final captured cse_tok: {cse_tok}")
        else:
            print("cse_tok not found.")
    except Exception as e:
        print(f"An error occurred: {e}")
