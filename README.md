# TrustAssistant AI

AI destekli alışveriş güven analiz sistemi.

Backend; ürün linki veya ürün adı alır, yorum güvenilirliği, satıcı/şikayet sinyali ve fiyat karşılaştırma sinyalini birlikte analiz eder.

## Çalıştırma

Tam Docker kurulumu:

```bash
docker compose up --build
```

Web:

```text
http://localhost:8080
```

Backend:

```text
http://localhost:8001
```

Swagger API Dokümantasyonu:

```text
http://localhost:8001/docs
```

Health:

```text
GET http://localhost:8001/health
```

## Analiz API

```http
POST /api/v1/analysis/
Content-Type: application/json
```

Ürün linki:

```json
{
  "product_url": "https://www.trendyol.com/apple/iphone-15-128-gb-mavi-p-762254881"
}
```

Ürün adı:

```json
{
  "product_name": "iphone 15 128 gb",
  "search_mode": "fast"
}
```

`search_mode`:

- `fast`: Trendyol, Hepsiburada, N11, Amazon
- `wide`: Tüm tanımlı marketplace listesi

## Mevcut Durum

Hazır olanlar:

- Yorum scraping ve kaynak birleştirme (Trendyol, Hepsiburada, N11, Amazon, Teknosa, MediaMarkt, Gratis, Watsons, eBebek, LC Waikiki, Vatan)
- Sahte/tekrar yorum sinyali ve ortalama yıldız puanı analizi
- Satıcı güven skoru (bilinen markalar ve resmi satıcı tespiti)
- Şikayetvar şikayet sinyali
- Akakce + Cimri güncel piyasa fiyat karşılaştırması
- Fast/Wide marketplace arama modu
- Redis önbellekleme (aynı ürün için anında yanıt)
- Playwright stealth (bot tespitini azaltır)
- Mobil `ApiService` gerçek backend endpoint'ine bağlı

Backend response ana alanları:

- `overall_trust_score`
- `review_count`, `review_sources`, `source_review_counts`
- `complaints`, `complaint_count`, `complaint_scope`, `complaint_sources`
- `price_sources`, `current_market_prices`, `price_history_source`, `price_search_urls`
- `risk_factors`
- `final_recommendation`

## Test

```bash
pytest tests/ -v
```
