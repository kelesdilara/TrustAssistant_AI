"""
Tüm Playwright kullanımı için merkezi stealth browser fabrikası.
Bot tespitini azaltmak için tüm scraperlar bu modülü kullanmalı.
"""
from playwright.sync_api import Browser, BrowserContext, Page, Playwright


_STEALTH_JS = """
() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    Object.defineProperty(navigator, 'languages', { get: () => ['tr-TR', 'tr', 'en-US', 'en'] });
    window.chrome = { runtime: {} };
    try {
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) =>
            parameters.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : originalQuery(parameters);
    } catch(e) {}
}
"""

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

_EXTRA_HEADERS = {
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    "sec-ch-ua-platform": '"macOS"',
}


def launch_stealth_browser(p: Playwright, headless: bool = True) -> Browser:
    return p.chromium.launch(
        headless=headless,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ],
    )


def new_stealth_context(browser: Browser) -> BrowserContext:
    context = browser.new_context(
        user_agent=_USER_AGENT,
        viewport={"width": 1440, "height": 900},
        locale="tr-TR",
        timezone_id="Europe/Istanbul",
        extra_http_headers=_EXTRA_HEADERS,
    )
    return context


def new_stealth_page(browser: Browser) -> Page:
    context = new_stealth_context(browser)
    page = context.new_page()
    page.add_init_script(_STEALTH_JS)
    return page
