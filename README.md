# TrustAssistant AI

AI destekli alisveris guven analiz sistemi.

Backend; urun linki veya urun adi alir, yorum guvenilirligi, satici/sikayet sinyali ve fiyat karsilastirma sinyalini birlikte analiz eder.

## Calistirma

Tam Docker kurulumu:

```powershell
docker compose up --build
```

Web:

```text
http://127.0.0.1:8080
```

Backend:

```text
http://127.0.0.1:8000
```

Sadece backend'i lokal calistirmak istersen:

```powershell
backend\venv311\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Health:

```text
GET http://127.0.0.1:8000/health
```

Docs:

```text
http://127.0.0.1:8000/docs
```

## Analiz API

```http
POST /api/v1/analysis/
Content-Type: application/json
```

Urun linki:

```json
{
  "product_url": "https://www.trendyol.com/apple/iphone-15-128-gb-mavi-p-762254881"
}
```

Urun adi:

```json
{
  "product_name": "iphone 15 128 gb",
  "search_mode": "fast"
}
```

`search_mode`:

- `fast`: Trendyol, Hepsiburada, N11, Amazon
- `wide`: tum tanimli marketplace listesi

## Mevcut Durum

Hazir olanlar:

- Yorum scraping ve kaynak birlestirme
- Sahte/tekrar yorum sinyali
- Satici guven skoru
- Sikayetvar sikayet sinyali
- Akakce + Cimri guncel piyasa fiyat karsilastirmasi
- Fast/Wide marketplace arama modu
- Mobil `ApiService` gercek backend endpoint'ine bagli

Backend response ana alanlari:

- `overall_trust_score`
- `review_count`, `review_sources`, `source_review_counts`
- `complaints`, `complaint_count`, `complaint_scope`, `complaint_sources`
- `price_sources`, `current_market_prices`, `price_history_source`, `price_search_urls`
- `risk_factors`
- `final_recommendation`

## Kalan Isler

Kapanisa kalan ana basliklar:

- Mobil UI'da backend cevabini sadece metin yerine kartli/bolumlu gostermek
- Scraper loglarini `print` yerine merkezi logger'a almak
- Canli site hatalarinda cache/timeout politikasini netlestirmek
- DB'ye analiz gecmisi kaydetmek
- Auth ekranlarini gercek backend auth akisi ile baglamak
- Production config: env, CORS, rate limit, deploy ayarlari

## Test

```powershell
backend\venv311\Scripts\python.exe -m pytest -q
```
