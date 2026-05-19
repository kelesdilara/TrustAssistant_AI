import html
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Optional
from urllib.parse import quote_plus, unquote, urljoin, urlparse

from playwright.sync_api import sync_playwright


logger = logging.getLogger(__name__)


ACTIVE_MARKETPLACES = [
    "hepsiburada",
    "trendyol",
    "n11",
    "amazon",
    "teknosa",
    "ebebek",
    "lcwaikiki",
    "gratis",
    "watsons",
    "mediamarkt",
    "vatan",
]


SEARCH_URLS = {
    "hepsiburada": "https://www.hepsiburada.com/ara?q={query}",
    "trendyol": "https://www.trendyol.com/sr?q={query}",
    "n11": "https://www.n11.com/arama?q={query}",
    "amazon": "https://www.amazon.com.tr/s?k={query}",
    "teknosa": "https://www.teknosa.com/arama/?s={query}",
    "ebebek": "https://www.e-bebek.com/search?q={query}",
    "lcwaikiki": "https://www.lcwaikiki.com/tr-TR/TR/arama?q={query}",
    "gratis": "https://www.gratis.com/arama?q={query}",
    "watsons": "https://www.watsons.com.tr/search?text={query}",
    "mediamarkt": "https://www.mediamarkt.com.tr/tr/search.html?query={query}",
    "vatan": "https://www.vatanbilgisayar.com/arama/{query}",
}


HEADLESS_BLOCKED_MARKETPLACES = {
    "amazon",
    "hepsiburada",
}


MARKETPLACE_DOMAINS = {
    "hepsiburada": "hepsiburada.com",
    "trendyol": "trendyol.com",
    "n11": "n11.com",
    "amazon": "amazon.com.tr",
    "teknosa": "teknosa.com",
    "ebebek": "e-bebek.com",
    "lcwaikiki": "lcwaikiki.com",
    "gratis": "gratis.com",
    "watsons": "watsons.com.tr",
    "mediamarkt": "mediamarkt.com.tr",
    "vatan": "vatanbilgisayar.com",
}


def search_product_links(
    product_name: str,
    enabled_marketplaces: list[str] | None = None,
    headless: bool = True,
    per_marketplace_timeout_ms: int = 10000,
    max_workers: int = 4,
) -> Dict[str, str]:
    found_links: Dict[str, str] = {}

    if not product_name:
        return found_links

    query = quote_plus(product_name)

    marketplaces = enabled_marketplaces or ACTIVE_MARKETPLACES

    def search_marketplace(marketplace: str) -> tuple[str, Optional[str]]:
        search_url = SEARCH_URLS[marketplace].format(query=query)
        logger.info("Marketplace search [%s]: %s", marketplace, search_url)

        product_url = _search_single_marketplace(
            marketplace=marketplace,
            product_name=product_name,
            search_url=search_url,
            headless=headless,
            timeout_ms=per_marketplace_timeout_ms,
        )

        return marketplace, product_url

    with ThreadPoolExecutor(max_workers=min(max_workers, len(marketplaces))) as executor:
        future_to_marketplace = {
            executor.submit(search_marketplace, marketplace): marketplace
            for marketplace in marketplaces
        }
        results = {}

        for future in as_completed(future_to_marketplace):
            marketplace = future_to_marketplace[future]
            try:
                result_marketplace, product_url = future.result()
                results[result_marketplace] = product_url
            except Exception as exc:
                logger.warning("Marketplace search error [%s]: %s", marketplace, exc)
                results[marketplace] = None

    for marketplace in ["trendyol"]:
        if marketplace not in marketplaces or results.get(marketplace):
            continue

        logger.info("Marketplace search retry [%s]", marketplace)
        _, product_url = search_marketplace(marketplace)
        results[marketplace] = product_url

    for marketplace in marketplaces:
        product_url = results.get(marketplace)
        if product_url:
            logger.info("Marketplace product found [%s]: %s", marketplace, product_url)
            found_links[marketplace] = product_url
        else:
            logger.info("Marketplace product not found [%s]", marketplace)

    return found_links


def _search_single_marketplace(
    marketplace: str,
    product_name: str,
    search_url: str,
    headless: bool,
    timeout_ms: int,
) -> Optional[str]:
    with sync_playwright() as p:
        from backend.app.services.browser_factory import launch_stealth_browser, new_stealth_page
        browser = launch_stealth_browser(p, headless=headless)
        page = new_stealth_page(browser)

        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_timeout(2000)

            for _ in range(2):
                page.mouse.wheel(0, 1200)
                page.wait_for_timeout(500)

            hrefs = _get_page_hrefs(page)
            html = page.content()

            if marketplace in MARKETPLACE_DOMAINS:
                return _extract_marketplace_product_link(
                    marketplace=marketplace,
                    html=html,
                    base_url=search_url,
                    hrefs=hrefs,
                    product_name=product_name,
                )

            return None

        except Exception as e:
            logger.warning("Marketplace search error [%s]: %s", marketplace, e)
            return None

        finally:
            browser.close()


def _get_page_hrefs(page) -> list[str]:
    for _ in range(3):
        try:
            page.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
            pass

        try:
            return page.eval_on_selector_all(
                "a[href]",
                "items => items.map(item => item.getAttribute('href')).filter(Boolean)",
            )
        except Exception as exc:
            if "Execution context was destroyed" not in str(exc):
                raise
            page.wait_for_timeout(1500)

    return []


def _extract_hepsiburada_product_link(
    html: str,
    base_url: str,
    hrefs: list[str] | None = None,
    product_name: str = "",
) -> Optional[str]:
    candidates = _extract_candidate_links(
        html=html,
        hrefs=hrefs,
        domain="hepsiburada.com",
        base_url="https://www.hepsiburada.com",
    )
    return _pick_best_product_link(
        candidates=candidates,
        product_name=product_name,
        is_valid_link=_is_valid_hepsiburada_product_link,
    )


def _extract_trendyol_product_link(
    html: str,
    base_url: str,
    hrefs: list[str] | None = None,
    product_name: str = "",
) -> Optional[str]:
    candidates = _extract_candidate_links(
        html=html,
        hrefs=hrefs,
        domain="trendyol.com",
        base_url="https://www.trendyol.com",
    )
    return _pick_best_product_link(
        candidates=candidates,
        product_name=product_name,
        is_valid_link=_is_valid_trendyol_product_link,
    )


def _extract_marketplace_product_link(
    marketplace: str,
    html: str,
    base_url: str,
    hrefs: list[str] | None = None,
    product_name: str = "",
) -> Optional[str]:
    domain = MARKETPLACE_DOMAINS[marketplace]
    parsed_search_url = urlparse(base_url)
    scheme = parsed_search_url.scheme or "https"
    base_site_url = f"{scheme}://www.{domain}"
    candidates = _extract_candidate_links(
        html=html,
        hrefs=hrefs,
        domain=domain,
        base_url=base_site_url,
    )
    return _pick_best_product_link(
        candidates=candidates,
        product_name=product_name,
        is_valid_link=lambda link: _is_valid_marketplace_product_link(marketplace, link),
    )


def _extract_candidate_links(
    html: str,
    hrefs: list[str] | None,
    domain: str,
    base_url: str,
) -> list[str]:
    candidates: list[str] = []

    for href in hrefs or []:
        candidates.append(href)

    patterns = [
        r"""href\s*=\s*["']([^"']+)["']""",
        r'''"(?:url|link|href|productUrl|webUrl)"\s*:\s*"([^"]+)''',
        rf"""(?:https?:)?//(?:www\.)?{re.escape(domain)}/[^"'\s<>\\]+""",
        r"""(/[^"'\s<>\\]+-p-[^"'\s<>\\]+)""",
        r"""(/[^"'\s<>\\]+/p/[^"'\s<>\\]+)""",
        r"""(/[^"'\s<>\\]+/dp/[^"'\s<>\\]+)""",
        r"""(/[^"'\s<>\\]+\.html)""",
        r"""(/urun/[^"'\s<>\\]+)""",
    ]

    for pattern in patterns:
        candidates.extend(re.findall(pattern, html, flags=re.IGNORECASE))

    normalized_links: list[str] = []
    seen = set()

    for candidate in candidates:
        link = _clean_link(candidate)
        if not link:
            continue

        if domain not in urlparse(link).netloc.lower():
            link = urljoin(base_url, link)

        if domain not in urlparse(link).netloc.lower():
            continue

        if link in seen:
            continue

        seen.add(link)
        normalized_links.append(link)

    return normalized_links


def _pick_best_product_link(
    candidates: list[str],
    product_name: str,
    is_valid_link,
) -> Optional[str]:
    valid_links = [link for link in candidates if is_valid_link(link)]
    if not valid_links:
        return None

    product_tokens = _tokenize(product_name)
    if not product_tokens:
        return valid_links[0]

    scored_links = [
        (_link_match_score(link, product_tokens), index, link)
        for index, link in enumerate(valid_links)
    ]
    scored_links.sort(key=lambda item: (-item[0], item[1]))

    best_score = scored_links[0][0]
    minimum_score = min(2, len(product_tokens))
    if best_score < minimum_score:
        return None

    return scored_links[0][2]


def _clean_link(link: str) -> str:
    if not link:
        return ""

    link = html.unescape(link)
    link = link.replace("\\u002F", "/")
    link = link.replace("\\u002f", "/")
    link = link.replace("\\u003A", ":")
    link = link.replace("\\u003a", ":")
    link = link.replace("\\u0026", "&")
    link = link.replace("\\/", "/")
    link = unquote(link)
    link = link.split("?")[0]
    link = link.split("#")[0]
    link = link.strip()

    # Protokol ekle
    if link.startswith("//"):
        link = "https:" + link

    return link


def _tokenize(value: str) -> set[str]:
    normalized = _normalize_text(value)
    return {
        token
        for token in normalized.split()
        if len(token) > 2 or (token.isdigit() and len(token) >= 2)
    }


def _normalize_text(value: str) -> str:
    value = value.lower()
    replacements = str.maketrans(
        {
            "ı": "i",
            "ğ": "g",
            "ü": "u",
            "ş": "s",
            "ö": "o",
            "ç": "c",
        }
    )
    value = value.translate(replacements)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def _link_match_score(link: str, product_tokens: set[str]) -> int:
    path = urlparse(link).path
    slug = re.sub(r"/(?:dp|product-reviews)/[A-Z0-9]{10}.*", "", path, flags=re.IGNORECASE)
    slug = slug.split("-p-", 1)[0].replace("/", " ")
    link_tokens = _tokenize(slug)
    return len(product_tokens & link_tokens)


def _is_valid_hepsiburada_product_link(link: str) -> bool:
    lower = link.lower()

    if "hepsiburada.com" not in lower:
        return False

    if "-p-" not in lower:
        return False

    blocked = [
        "/ara",
        "/kampanya",
        "/magaza",
        "/merchant",
        "/yorumlari",
    ]

    if any(item in lower for item in blocked):
        return False

    return True


def _is_valid_trendyol_product_link(link: str) -> bool:
    lower = link.lower()

    if "trendyol.com" not in lower:
        return False

    if "-p-" not in lower:
        return False

    blocked = [
        "/sr",
        "/butik",
        "/magaza",
        "/yorumlar",
    ]

    if any(item in lower for item in blocked):
        return False

    return True


def _is_valid_marketplace_product_link(marketplace: str, link: str) -> bool:
    if marketplace == "hepsiburada":
        return _is_valid_hepsiburada_product_link(link)

    if marketplace == "trendyol":
        return _is_valid_trendyol_product_link(link)

    validators = {
        "n11": _is_valid_n11_product_link,
        "amazon": _is_valid_amazon_product_link,
        "teknosa": _is_valid_teknosa_product_link,
        "ebebek": _is_valid_ebebek_product_link,
        "lcwaikiki": _is_valid_lcwaikiki_product_link,
        "gratis": _is_valid_gratis_product_link,
        "watsons": _is_valid_watsons_product_link,
        "mediamarkt": _is_valid_mediamarkt_product_link,
        "vatan": _is_valid_vatan_product_link,
    }
    validator = validators.get(marketplace)
    return bool(validator and validator(link))


def _has_domain(link: str, domain: str) -> bool:
    return domain in urlparse(link).netloc.lower()


def _has_blocked_path(link: str, blocked: list[str]) -> bool:
    lower = link.lower()
    return any(item in lower for item in blocked)


def _is_valid_n11_product_link(link: str) -> bool:
    lower = link.lower()
    if not _has_domain(link, "n11.com"):
        return False
    if _has_blocked_path(lower, ["/arama", "/magaza", "/kampanya", "/kategori"]):
        return False
    return "/urun/" in lower or re.search(r"/[^/]+-\d{6,}", lower) is not None


def _is_valid_amazon_product_link(link: str) -> bool:
    lower = link.lower()
    if not _has_domain(link, "amazon.com.tr"):
        return False
    if _has_blocked_path(lower, ["/s?", "/stores/", "/gp/", "/hz/", "/customer-reviews"]):
        return False
    return "/dp/" in lower or "/product-reviews/" in lower


def _is_valid_teknosa_product_link(link: str) -> bool:
    lower = link.lower()
    if not _has_domain(link, "teknosa.com"):
        return False
    if _has_blocked_path(lower, ["/arama", "/kategori", "/marka"]):
        return False
    return "-p-" in lower or re.search(r"-p-\d+", lower) is not None


def _is_valid_ebebek_product_link(link: str) -> bool:
    lower = link.lower()
    if not _has_domain(link, "e-bebek.com"):
        return False
    if _has_blocked_path(lower, ["/search", "/kategori", "/c/"]):
        return False
    return "-p-" in lower or "/p/" in lower


def _is_valid_lcwaikiki_product_link(link: str) -> bool:
    lower = link.lower()
    if not _has_domain(link, "lcwaikiki.com"):
        return False
    if _has_blocked_path(lower, ["/arama", "/kategori", "/favoriler"]):
        return False
    return "/p/" in lower or "product" in lower


def _is_valid_gratis_product_link(link: str) -> bool:
    lower = link.lower()
    if not _has_domain(link, "gratis.com"):
        return False
    if _has_blocked_path(lower, ["/arama", "/search", "/kategori"]):
        return False
    return "/p/" in lower or "-p-" in lower


def _is_valid_watsons_product_link(link: str) -> bool:
    lower = link.lower()
    if not _has_domain(link, "watsons.com.tr"):
        return False
    if _has_blocked_path(lower, ["/search", "/c/", "/kategori"]):
        return False
    return "/p/" in lower or "-p-" in lower


def _is_valid_mediamarkt_product_link(link: str) -> bool:
    lower = link.lower()
    if not _has_domain(link, "mediamarkt.com.tr"):
        return False
    if _has_blocked_path(lower, ["/search", "/category", "/kampanya"]):
        return False
    return lower.endswith(".html") or "/product/" in lower


def _is_valid_vatan_product_link(link: str) -> bool:
    lower = link.lower()
    if not _has_domain(link, "vatanbilgisayar.com"):
        return False
    if _has_blocked_path(lower, ["/arama", "/kategori", "/kampanya"]):
        return False
    return lower.endswith(".html")
