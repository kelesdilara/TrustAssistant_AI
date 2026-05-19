import logging
import re
import unicodedata
from typing import Dict, List
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from playwright.sync_api import sync_playwright


logger = logging.getLogger(__name__)


SIKAYETVAR_BASE_URL = "https://www.sikayetvar.com"
SIKAYETVAR_SEARCH_URL = f"{SIKAYETVAR_BASE_URL}/arama?q={{query}}"


def get_complaint_signals(
    seller_name: str | None = None,
    product_name: str | None = None,
    site_name: str | None = None,
    max_complaints: int = 5,
    timeout_seconds: int = 8,
) -> dict:
    queries = _build_queries(
        seller_name=seller_name,
        site_name=site_name,
        product_name=product_name,
    )
    if not queries:
        return _empty_result()

    complaints: List[Dict] = []
    complaint_scope = None
    complaint_query = None
    for query, scope in queries:
        complaints = _scrape_with_playwright(
            query=query,
            max_complaints=max_complaints,
            timeout_ms=timeout_seconds * 1000,
        )

        if not complaints:
            complaints = _scrape_with_http(
                query=query,
                max_complaints=max_complaints,
                timeout_seconds=min(timeout_seconds, 4),
            )

        if complaints:
            complaint_scope = scope
            complaint_query = query
            break

    return {
        "complaints": complaints,
        "complaint_count": len(complaints),
        "complaint_sources": ["sikayetvar"] if complaints else [],
        "complaint_scope": complaint_scope,
        "complaint_query": complaint_query,
    }


def extract_complaints_from_text(page_text: str, max_complaints: int = 5) -> List[Dict]:
    lines = [
        _clean_line(line)
        for line in str(page_text or "").split("\n")
        if 30 <= len(line.strip()) <= 280
    ]

    complaints: List[Dict] = []
    seen = set()

    for line in lines:
        _add_complaint(complaints, seen, line, url=None, max_complaints=max_complaints)
        if len(complaints) >= max_complaints:
            break

    return complaints


def extract_complaints_from_cards(cards: list[dict], max_complaints: int = 5) -> List[Dict]:
    complaints: List[Dict] = []
    seen = set()

    for card in cards:
        title = _clean_line(str(card.get("title") or ""))
        href = str(card.get("href") or "").strip() or None
        url = _absolute_sikayetvar_url(href) if href else None

        _add_complaint(
            complaints=complaints,
            seen=seen,
            title=title,
            url=url,
            max_complaints=max_complaints,
            require_hint=True,
        )
        if len(complaints) >= max_complaints:
            break

    return complaints


def _scrape_with_playwright(query: str, max_complaints: int, timeout_ms: int) -> List[Dict]:
    urls = _candidate_urls(query)

    try:
        with sync_playwright() as p:
            from backend.app.services.browser_factory import launch_stealth_browser, new_stealth_page
            browser = launch_stealth_browser(p, headless=True)
            page = new_stealth_page(browser)
            page.set_default_timeout(min(timeout_ms, 5000))
            page.route(
                "**/*",
                lambda route: route.abort()
                if route.request.resource_type in {"image", "media", "font", "stylesheet"}
                else route.continue_(),
            )

            try:
                for url in urls:
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                        page.wait_for_timeout(1000)
                    except Exception as exc:
                        logger.warning("Complaint page load error [%s]: %s", url, exc)
                        continue

                    complaints = extract_complaints_from_cards(
                        _extract_complaint_cards(page),
                        max_complaints=max_complaints,
                    )
                    complaints = _filter_relevant_complaints(complaints, query)
                    if complaints:
                        return complaints

                    complaints = extract_complaints_from_text(
                        page.inner_text("body"),
                        max_complaints=max_complaints,
                    )
                    complaints = _filter_relevant_complaints(complaints, query)
                    if complaints:
                        return complaints
            finally:
                browser.close()
    except Exception as exc:
        logger.warning("Complaint Playwright error [%s]: %s", query, exc)

    return []


def _extract_complaint_cards(page) -> list[dict]:
    return page.eval_on_selector_all(
        "a[href]",
        """
        anchors => anchors
            .map(anchor => ({
                title: (anchor.innerText || anchor.textContent || '').trim(),
                href: anchor.getAttribute('href') || ''
            }))
            .filter(item =>
                item.title.length >= 20 &&
                item.title.length <= 220 &&
                item.href &&
                !item.href.includes('/arama') &&
                !item.href.includes('/giris') &&
                !item.href.includes('/uye-ol')
            )
        """,
    )


def _scrape_with_http(query: str, max_complaints: int, timeout_seconds: int) -> List[Dict]:
    for url in _candidate_urls(query):
        try:
            request = Request(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/122.0.0.0 Safari/537.36"
                    ),
                    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
                },
            )
            with urlopen(request, timeout=timeout_seconds) as response:
                page_text = response.read().decode("utf-8", errors="ignore")
            complaints = extract_complaints_from_text(page_text, max_complaints=max_complaints)
            complaints = _filter_relevant_complaints(complaints, query)
            if complaints:
                return complaints
        except Exception as exc:
            logger.warning("Complaint HTTP error [%s]: %s", url, exc)

    return []


def _candidate_urls(query: str) -> list[str]:
    slug = _slugify(query)
    urls = []
    if slug:
        urls.append(f"{SIKAYETVAR_BASE_URL}/{slug}")
    urls.append(SIKAYETVAR_SEARCH_URL.format(query=quote_plus(query)))
    return urls


def _add_complaint(
    complaints: List[Dict],
    seen: set,
    title: str,
    url: str | None,
    max_complaints: int,
    require_hint: bool = True,
) -> None:
    title = _clean_line(title)
    normalized = _normalize_text(title)

    if not title or normalized in seen or len(complaints) >= max_complaints:
        return

    if require_hint and not _looks_like_complaint(title):
        return

    if _looks_like_navigation(title):
        return

    seen.add(normalized)
    complaints.append(
        {
            "source": "sikayetvar",
            "title": title,
            "url": url,
        }
    )


def _filter_relevant_complaints(complaints: List[Dict], query: str) -> List[Dict]:
    query_tokens = _important_tokens(query)
    if not query_tokens:
        return complaints

    relevant = []
    for complaint in complaints:
        haystack = _normalize_text(
            f"{complaint.get('title', '')} {complaint.get('url', '')}"
        )
        haystack_tokens = set(haystack.split())
        if query_tokens & haystack_tokens:
            relevant.append(complaint)

    return relevant


def _important_tokens(value: str) -> set[str]:
    generic_tokens = {
        "yetkili",
        "satici",
        "satis",
        "magaza",
        "resmi",
        "urun",
        "gb",
        "tl",
    }
    return {
        token
        for token in _normalize_text(value).split()
        if (len(token) >= 4 or token.isdigit()) and token not in generic_tokens
    }


def _build_queries(
    seller_name: str | None,
    product_name: str | None,
    site_name: str | None = None,
) -> list[tuple[str, str]]:
    queries = []
    if seller_name and "bulunamad" not in _normalize_text(seller_name):
        queries.append((seller_name.strip(), "seller"))

    if site_name:
        site_query = site_name.strip()
        if site_query and all(site_query != query for query, _ in queries):
            queries.append((site_query, "site"))

    if product_name:
        product_query = product_name.strip()
        if product_query and all(product_query != query for query, _ in queries):
            queries.append((product_query, "product"))

    return queries


def _looks_like_complaint(text: str) -> bool:
    normalized = _normalize_text(text)
    complaint_hints = [
        "sikayet",
        "magdur",
        "iade",
        "teslim",
        "kargo",
        "bozuk",
        "arizali",
        "yanlis",
        "eksik",
        "iptal",
        "para",
        "garanti",
        "servis",
        "ulasamiyorum",
        "cozulmedi",
        "problem",
        "sorun",
    ]
    return any(item in normalized for item in complaint_hints)


def _looks_like_navigation(text: str) -> bool:
    normalized = _normalize_text(text)
    blocked = [
        "sikayetvar",
        "cozum merkezi",
        "marka karsilastir",
        "uye girisi",
        "giris yap",
        "kayit ol",
        "populer markalar",
        "en yeni sikayetler",
        "hakkimizda",
        "iletisim",
    ]
    return any(item in normalized for item in blocked)


def _absolute_sikayetvar_url(href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return f"{SIKAYETVAR_BASE_URL}{href}"
    return f"{SIKAYETVAR_BASE_URL}/{href}"


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_value = ascii_value.lower()
    ascii_value = re.sub(r"[^a-z0-9]+", "-", ascii_value)
    return ascii_value.strip("-")


def _clean_line(line: str) -> str:
    return " ".join(str(line or "").split())


def _normalize_text(value: str) -> str:
    replacements = str.maketrans(
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
    normalized = str(value or "").lower().translate(replacements)
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return _clean_line(normalized)


def _empty_result() -> dict:
    return {
        "complaints": [],
        "complaint_count": 0,
        "complaint_sources": [],
        "complaint_scope": None,
        "complaint_query": None,
    }
