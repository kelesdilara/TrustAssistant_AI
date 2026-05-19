from datetime import datetime, timedelta
import logging
import random
import re
import unicodedata
from urllib.parse import quote_plus, urljoin

from playwright.sync_api import sync_playwright


logger = logging.getLogger(__name__)


AKAKCE_BASE_URL = "https://www.akakce.com"
AKAKCE_SEARCH_URL = f"{AKAKCE_BASE_URL}/arama/?q={{query}}"
CIMRI_BASE_URL = "https://www.cimri.com"
CIMRI_SEARCH_URL = f"{CIMRI_BASE_URL}/arama?q={{query}}"


def parse_price_to_float(price_text: str | None) -> float | None:
    if not price_text:
        return None

    raw = str(price_text).lower()
    price_matches = re.findall(
        r"\d{1,3}(?:\.\d{3})*(?:,\d{2})?\s*(?:tl|₺)",
        raw,
        flags=re.IGNORECASE,
    )
    if price_matches:
        return _price_match_to_float(price_matches[-1])

    cleaned = raw.replace("tl", "").replace("₺", "").strip()
    cleaned = cleaned.replace(".", "").replace(",", ".")
    number_matches = re.findall(r"\d+(?:\.\d+)?", cleaned)
    if not number_matches:
        return None

    return float(number_matches[-1])


def get_price_history(
    product_url: str | None = None,
    current_price_text: str | None = None,
    product_name: str | None = None,
) -> list:
    price_result = get_price_signals(
        product_name=product_name,
        current_price_text=current_price_text,
    )
    return price_result["price_history"]


def get_price_signals(
    product_name: str | None = None,
    current_price_text: str | None = None,
    max_prices: int = 12,
) -> dict:
    current_price = parse_price_to_float(current_price_text)
    akakce_result = scrape_akakce_prices(
        product_name=product_name,
        max_prices=max_prices,
    )
    cimri_result = scrape_cimri_prices(
        product_name=product_name,
        max_prices=max_prices,
    )

    market_prices = merge_market_prices(
        akakce_result.get("market_prices", []),
        cimri_result.get("market_prices", []),
        max_prices=max_prices * 2,
    )
    if current_price:
        market_prices = filter_market_prices_by_current_price(
            market_prices=market_prices,
            current_price=current_price,
        )

    if market_prices:
        price_sources = sorted({item["source"] for item in market_prices if item.get("source")})
        history = build_history_from_market_prices(
            market_prices=market_prices,
            current_price=current_price,
        )
        return {
            "price_history": history,
            "price_sources": price_sources,
            "price_history_source": "market_price_sources",
            "price_history_days": 0,
            "price_history_is_estimated": False,
            "current_market_prices": market_prices,
            "price_search_url": akakce_result.get("price_search_url") or cimri_result.get("price_search_url"),
            "price_search_urls": {
                "akakce": akakce_result.get("price_search_url"),
                "cimri": cimri_result.get("price_search_url"),
            },
        }

    return {
        "price_history": build_simulated_price_history(current_price),
        "price_sources": [],
        "price_history_source": "simulated",
        "price_history_days": 90,
        "price_history_is_estimated": True,
        "current_market_prices": [],
        "price_search_url": akakce_result.get("price_search_url"),
        "price_search_urls": {
            "akakce": akakce_result.get("price_search_url"),
            "cimri": cimri_result.get("price_search_url"),
        },
    }


def scrape_akakce_prices(product_name: str | None, max_prices: int = 8) -> dict:
    if not product_name:
        return _empty_akakce_result()

    search_url = AKAKCE_SEARCH_URL.format(query=quote_plus(product_name))

    try:
        with sync_playwright() as p:
            from backend.app.services.browser_factory import launch_stealth_browser, new_stealth_page
            browser = launch_stealth_browser(p, headless=True)
            page = new_stealth_page(browser)
            page.set_default_timeout(5000)
            page.route(
                "**/*",
                lambda route: route.abort()
                if route.request.resource_type in {"image", "media", "font", "stylesheet"}
                else route.continue_(),
            )

            try:
                page.goto(search_url, wait_until="domcontentloaded", timeout=12000)
                page.wait_for_timeout(1200)

                product_link = _pick_best_akakce_link(
                    links=_extract_links(page),
                    product_name=product_name,
                    base_url=search_url,
                )
                if product_link:
                    try:
                        page.goto(product_link, wait_until="domcontentloaded", timeout=12000)
                        page.wait_for_timeout(1200)
                    except Exception as exc:
                        logger.warning("Akakce product load error [%s]: %s", product_link, exc)

                page_text = page.inner_text("body")
                market_prices = extract_market_prices_from_text(
                    page_text=page_text,
                    max_prices=max_prices,
                )

                return {
                    "market_prices": market_prices,
                    "price_search_url": product_link or search_url,
                }
            finally:
                browser.close()

    except Exception as exc:
        logger.warning("Akakce price scraper error [%s]: %s", product_name, exc)

    return {
        "market_prices": [],
        "price_search_url": search_url,
    }


def scrape_cimri_prices(product_name: str | None, max_prices: int = 8) -> dict:
    if not product_name:
        return _empty_cimri_result()

    search_url = CIMRI_SEARCH_URL.format(query=quote_plus(product_name))

    try:
        with sync_playwright() as p:
            from backend.app.services.browser_factory import launch_stealth_browser, new_stealth_page
            browser = launch_stealth_browser(p, headless=True)
            page = new_stealth_page(browser)
            page.set_default_timeout(5000)
            page.route(
                "**/*",
                lambda route: route.abort()
                if route.request.resource_type in {"image", "media", "font", "stylesheet"}
                else route.continue_(),
            )

            try:
                page.goto(search_url, wait_until="domcontentloaded", timeout=12000)
                page.wait_for_timeout(1200)

                product_link = _pick_best_cimri_link(
                    links=_extract_links(page),
                    product_name=product_name,
                    base_url=search_url,
                )
                if product_link:
                    try:
                        page.goto(product_link, wait_until="domcontentloaded", timeout=12000)
                        page.wait_for_timeout(1200)
                    except Exception as exc:
                        logger.warning("Cimri product load error [%s]: %s", product_link, exc)

                market_prices = extract_market_prices_from_text(
                    page_text=page.inner_text("body"),
                    max_prices=max_prices,
                    source="cimri",
                )

                return {
                    "market_prices": market_prices,
                    "price_search_url": product_link or search_url,
                }
            finally:
                browser.close()
    except Exception as exc:
        logger.warning("Cimri price scraper error [%s]: %s", product_name, exc)

    return {
        "market_prices": [],
        "price_search_url": search_url,
    }


def extract_market_prices_from_text(
    page_text: str,
    max_prices: int = 8,
    source: str = "akakce",
) -> list[dict]:
    text = str(page_text or "")
    lines = [_clean_line(line) for line in text.split("\n") if line.strip()]
    prices: list[dict] = []
    seen = set()

    for index, line in enumerate(lines):
        price_text = _extract_price_text(line)
        if not price_text:
            continue

        price = parse_price_to_float(price_text)
        if not price or price <= 0:
            continue

        seller = _seller_near_line(lines, index)
        key = (round(price, 2), seller.lower())
        if key in seen:
            continue

        seen.add(key)
        prices.append(
            {
                "source": source,
                "seller": _clean_seller_name(seller),
                "price": round(price, 2),
                "price_text": price_text,
            }
        )

        if len(prices) >= max_prices:
            break

    return sorted(prices, key=lambda item: item["price"])


def merge_market_prices(*price_lists: list[dict], max_prices: int = 16) -> list[dict]:
    merged = []
    seen = set()

    for price_list in price_lists:
        for item in price_list:
            price = item.get("price")
            if not isinstance(price, (int, float)):
                continue

            key = (item.get("source"), round(price, 2), str(item.get("seller") or "").lower())
            if key in seen:
                continue

            seen.add(key)
            merged.append(item)

    return sorted(merged, key=lambda item: item["price"])[:max_prices]


def filter_market_prices_by_current_price(
    market_prices: list[dict],
    current_price: float,
) -> list[dict]:
    min_allowed = current_price * 0.6
    max_allowed = current_price * 1.8
    return [
        item
        for item in market_prices
        if isinstance(item.get("price"), (int, float))
        and min_allowed <= item["price"] <= max_allowed
    ]


def build_history_from_market_prices(
    market_prices: list[dict],
    current_price: float | None = None,
) -> list[dict]:
    prices = [
        item.get("price")
        for item in market_prices
        if isinstance(item.get("price"), (int, float))
    ]
    if not prices:
        return build_simulated_price_history(current_price)

    today = datetime.now()
    min_price = min(prices)
    max_price = max(prices)
    avg_price = sum(prices) / len(prices)
    final_price = current_price or min_price

    return [
        {
            "date": (today - timedelta(days=2)).strftime("%Y-%m-%d"),
            "price": round(max_price, 2),
            "source": "market_price_high",
        },
        {
            "date": (today - timedelta(days=1)).strftime("%Y-%m-%d"),
            "price": round(avg_price, 2),
            "source": "market_price_average",
        },
        {
            "date": today.strftime("%Y-%m-%d"),
            "price": round(final_price, 2),
            "source": "current_product_price" if current_price else "market_price_low",
        },
    ]


def build_simulated_price_history(current_price: float | None = None) -> list:
    current_price = current_price or 300.0
    today = datetime.now()
    history = []
    base_price = current_price * random.uniform(1.08, 1.28)

    for i in range(90):
        date = today - timedelta(days=89 - i)
        progress = i / 89
        trend_price = base_price - ((base_price - current_price) * progress)
        noise = random.uniform(-12, 12)
        price = round(max(trend_price + noise, current_price * 0.75), 2)
        history.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "price": price,
                "source": "simulated",
            }
        )

    history[-1]["price"] = current_price
    return history


def _extract_links(page) -> list[dict]:
    return page.eval_on_selector_all(
        "a[href]",
        """
        anchors => anchors
            .map(anchor => ({
                text: (anchor.innerText || anchor.textContent || '').trim(),
                href: anchor.getAttribute('href') || ''
            }))
            .filter(item => item.href && item.text.length >= 5)
        """,
    )


def _pick_best_akakce_link(
    links: list[dict],
    product_name: str,
    base_url: str,
) -> str | None:
    product_tokens = _important_tokens(product_name)
    best_score = 0
    best_link = None

    for link in links:
        href = str(link.get("href") or "")
        text = str(link.get("text") or "")
        absolute_url = urljoin(base_url, href)
        if "akakce.com" not in absolute_url or not _looks_like_product_url(absolute_url):
            continue

        score = len(product_tokens & _important_tokens(f"{text} {absolute_url}"))
        if score > best_score:
            best_score = score
            best_link = absolute_url

    minimum_score = min(2, len(product_tokens))
    if best_score < minimum_score:
        return None

    return best_link


def _pick_best_cimri_link(
    links: list[dict],
    product_name: str,
    base_url: str,
) -> str | None:
    product_tokens = _important_tokens(product_name)
    best_score = 0
    best_link = None

    for link in links:
        href = str(link.get("href") or "")
        text = str(link.get("text") or "")
        absolute_url = urljoin(base_url, href)
        if "cimri.com" not in absolute_url or not _looks_like_cimri_product_url(absolute_url):
            continue

        score = len(product_tokens & _important_tokens(f"{text} {absolute_url}"))
        if score > best_score:
            best_score = score
            best_link = absolute_url

    minimum_score = min(2, len(product_tokens))
    if best_score < minimum_score:
        return None

    return best_link


def _looks_like_product_url(url: str) -> bool:
    lower = url.lower()
    blocked = ["/arama", "/kategori", "/marka", "/kampanya"]
    if any(item in lower for item in blocked):
        return False
    return lower.endswith(".html") or "-fiyati" in lower or "/p/" in lower


def _looks_like_cimri_product_url(url: str) -> bool:
    lower = url.lower()
    blocked = ["/arama", "/kategori", "/marka", "/kampanya"]
    if any(item in lower for item in blocked):
        return False
    return "/cep-telefonlari/" in lower or "-fiyatlari" in lower or lower.endswith(".html")


def _extract_price_text(text: str) -> str | None:
    match = re.search(r"\d{1,3}(?:\.\d{3})*(?:,\d{2})?\s*(?:tl|₺)", text, flags=re.IGNORECASE)
    if match:
        return _clean_line(match.group())
    return None


def _price_match_to_float(value: str) -> float | None:
    cleaned = str(value).lower()
    cleaned = cleaned.replace("tl", "").replace("₺", "").strip()
    cleaned = cleaned.replace(".", "").replace(",", ".")

    match = re.search(r"\d+(?:\.\d+)?", cleaned)
    if not match:
        return None

    return float(match.group())


def _seller_near_line(lines: list[str], index: int) -> str:
    candidates = []
    for offset in range(1, 4):
        for nearby_index in (index - offset, index + offset):
            if 0 <= nearby_index < len(lines):
                candidates.append(lines[nearby_index])

    for candidate in candidates:
        cleaned = _clean_line(candidate)
        if not cleaned or _extract_price_text(cleaned):
            continue
        if len(cleaned) <= 40 and not _looks_like_noise(cleaned):
            return cleaned

    return ""


def _looks_like_noise(text: str) -> bool:
    normalized = _normalize_text(text)
    noise = [
        "sepete",
        "kargo",
        "taksit",
        "yorum",
        "ozellik",
        "fiyat",
        "arama",
        "filtre",
        "renk",
        "secenek",
        "karsilastir",
        "favori",
        "bildirim",
        "siyah",
        "mavi",
        "sari",
        "beyaz",
        "pembe",
        "yesil",
        "magazaya",
        "git",
        "alarm",
        "kur",
    ]
    if re.fullmatch(r"\d+(?:\s*gb)?", normalized):
        return True
    if re.fullmatch(r"\d+\s*\d?", normalized):
        return True
    return any(item in normalized for item in noise)


def _clean_seller_name(value: str) -> str | None:
    cleaned = _clean_line(value)
    if not cleaned or _looks_like_noise(cleaned):
        return None
    return cleaned


def _important_tokens(value: str) -> set[str]:
    generic_tokens = {
        "icin",
        "fiyat",
        "fiyati",
        "akakce",
        "apple",
        "telefon",
        "akilli",
        "urun",
        "gb",
        "tl",
    }
    return {
        token
        for token in _normalize_text(value).split()
        if (len(token) >= 3 or token.isdigit()) and token not in generic_tokens
    }


def _normalize_text(value: str) -> str:
    translated = str(value or "").translate(
        str.maketrans(
            {
                "ı": "i",
                "ğ": "g",
                "ü": "u",
                "ş": "s",
                "ö": "o",
                "ç": "c",
                "İ": "i",
                "Ğ": "g",
                "Ü": "u",
                "Ş": "s",
                "Ö": "o",
                "Ç": "c",
            }
        )
    )
    normalized = unicodedata.normalize("NFKD", translated)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    ascii_value = re.sub(r"[^a-z0-9]+", " ", ascii_value)
    return _clean_line(ascii_value)


def _clean_line(line: str) -> str:
    return " ".join(str(line or "").split())


def _empty_akakce_result() -> dict:
    return {
        "market_prices": [],
        "price_search_url": None,
    }


def _empty_cimri_result() -> dict:
    return {
        "market_prices": [],
        "price_search_url": None,
    }
