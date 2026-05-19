# TrustAssistant AI — Çalıştırma Kılavuzu

## Gereksinimler

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (v24+)
- Docker Compose v2 (`docker compose` komutu — eski `docker-compose` değil)
- Git

---

## 1. Kurulum

### 1.1 Projeyi klonla

```bash
git clone <repo-url>
cd TrustAssistant_AI
```

### 1.2 `.env` dosyasını oluştur

```bash
cp .env.example .env
```

`.env` dosyasını aç ve en azından şu değeri değiştir:

```
JWT_SECRET_KEY=buraya-cok-uzun-ve-gizli-bir-anahtar-yaz
```

Diğer değerler geliştirme ortamı için hazır.

---

## 2. Docker ile Çalıştırma

### 2.1 Tüm servisleri başlat

```bash
docker compose up --build -d
```

İlk başlatmada Docker image'ları build edilir ve Playwright/Chromium kurulur — **5-10 dakika sürebilir.**

### 2.2 Ollama modeli indir (ilk kurulumda zorunlu)

Servisler ayağa kalktıktan sonra LLM modelini yükle:

```bash
docker compose exec ollama ollama pull llama3.2
```

> Model boyutu ~2 GB'tır. İndirme ağ hızına göre değişir.
> Model indirilmeden analiz isteği yapılırsa backend hata döner.

### 2.3 Servislerin durumunu kontrol et

```bash
docker compose ps
```

Tüm servislerin `healthy` veya `running` olması beklenir.

### 2.4 Logları takip et

```bash
# Tüm servisler
docker compose logs -f

# Sadece backend
docker compose logs -f backend

# Sadece ollama
docker compose logs -f ollama
```

---

## 3. Erişim Adresleri

| Servis | URL |
|---|---|
| Flutter Web Arayüzü | http://localhost:8080 |
| FastAPI Backend | http://localhost:8000 |
| Swagger API Dokümantasyonu | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |
| Ollama | http://localhost:11434 |

---

## 4. Sık Kullanılan Docker Komutları

```bash
# Servisleri durdur (veriyi koru)
docker compose stop

# Servisleri durdur ve container'ları sil
docker compose down

# Servisleri durdur, container + volume'ları tamamen sil (veritabanı sıfırlanır!)
docker compose down -v

# Sadece backend'i yeniden build et ve başlat
docker compose up --build -d backend

# Backend container'ına bağlan
docker compose exec backend bash

# PostgreSQL'e bağlan
docker compose exec db psql -U trustuser -d trustassistant

# Redis CLI
docker compose exec redis redis-cli

# Ollama'da yüklü modelleri listele
docker compose exec ollama ollama list

# Alternatif model indir (daha hızlı / farklı boyut)
docker compose exec ollama ollama pull llama3.2:1b    # ~1.3 GB, çok daha hızlı
docker compose exec ollama ollama pull mistral        # ~4 GB, daha güçlü
```

---

## 5. Geliştirme Ortamı (Docker olmadan backend çalıştırma)

### 5.1 Python ortamı

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -e .
playwright install chromium
```

### 5.2 Altyapı servislerini Docker ile, backend'i lokalde çalıştır

```bash
# Sadece altyapıyı başlat
docker compose up -d db redis ollama

# Ollama modelini indir
docker compose exec ollama ollama pull llama3.2

# Backend'i lokalde başlat (hot-reload ile)
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

> `.env` dosyasında `DATABASE_URL` ve `REDIS_URL` değerlerinin `localhost` içerdiğinden emin ol (Docker URL değil).

### 5.3 Testleri çalıştır

```bash
pytest tests/ -v
```

---

## 6. Performans Notları

> Analiz isteği **neden bu kadar yavaş?** Aşağıdaki kısımlar gecikmeye yol açar:

| Katman | Süre (tahmini) | Neden |
|---|---|---|
| Scraping (Playwright) | 10–60 sn | Her kaynak site için ayrı Chromium oturumu açılır |
| LLM (Ollama) | 15–120 sn | Yerel model, soğuk başlangıçta ve büyük modelde çok yavaş |
| Senkron HTTP çağrısı | Tüm süreyi bloklar | `ollama_service.py` senkron `requests` kullanıyor |
| Graph her istekte derleniyor | +100–200 ms | `build_analysis_graph()` her `/analysis` isteğinde çağrılıyor |

### Hızlandırmak için ne yapılabilir?

**Kısa vadeli (hemen yapılabilir):**

1. **Daha küçük Ollama modeli kullan** — en hızlı yol:
   ```bash
   docker compose exec ollama ollama pull llama3.2:1b
   ```
   `.env` dosyasında değiştir:
   ```
   OLLAMA_MODEL=llama3.2:1b
   ```
   Sonra backend'i yeniden başlat:
   ```bash
   docker compose restart backend
   ```

2. **Uvicorn worker sayısını artır** — birden fazla eş zamanlı istek için:
   `backend/Dockerfile` sonundaki CMD satırını değiştir:
   ```dockerfile
   CMD ["python", "-m", "uvicorn", "backend.app.main:app", \
        "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
   ```

**Orta vade (kod değişikliği gerektirir):**

3. **`ollama_service.py`'de `httpx` ile async çağrı kullan** — `requests.post()` tüm event loop'u blokluyor:
   ```python
   # Şu an (blokluyor):
   import requests
   response = requests.post(...)

   # Olması gereken:
   import httpx
   async with httpx.AsyncClient() as client:
       response = await client.post(...)
   ```

4. **`analysis.py`'de graph'ı startup'ta derle, her istekte değil:**
   ```python
   # main.py lifespan içinde:
   app.state.analysis_graph = build_analysis_graph()

   # analysis.py içinde:
   graph = request.app.state.analysis_graph
   ```

5. **Redis ile sonuçları önbelleğe al** — Redis kurulu ama hiç kullanılmıyor. Aynı ürün URL'si için tekrar analiz yapılmasını engeller.

6. **`analysis.py` endpoint'ini async yap ve `run_in_executor` kullan** — `graph.invoke()` senkron olduğu için async endpoint bile olsa bir thread'i blokluyor.

---

## 7. Sorun Giderme

### Backend başlamıyor / healthcheck başarısız

```bash
docker compose logs backend
```

Genellikle PostgreSQL veya Ollama hazır olmadan bağlanmaya çalışıyor olur. Dene:

```bash
docker compose restart backend
```

### "Model not found" hatası

Ollama modeli henüz indirilmemiş demektir:

```bash
docker compose exec ollama ollama pull llama3.2
```

### Analiz çok uzun sürüyor / timeout alıyor

- `OLLAMA_MODEL=llama3.2:1b` ile daha küçük model dene (bkz. Performans Notları)
- `docker compose logs ollama` ile LLM inference süresini kontrol et
- Backend timeout `backend/app/services/ollama_service.py` içinde `timeout=120` ile ayarlı — gerekirse düşür

### PostgreSQL bağlantı hatası

```bash
docker compose exec db pg_isready -U trustuser -d trustassistant
```

### Playwright / Chromium hatası

Backend container içinde Playwright browser kurulumunu doğrula:

```bash
docker compose exec backend python -m playwright install --with-deps chromium
```

### Port çakışması

Başka bir uygulama aynı portu kullanıyorsa `.env` dosyasından port numaralarını değiştir:

```
BACKEND_PORT=8001
POSTGRES_PORT=5433
REDIS_PORT=6380
OLLAMA_PORT=11435
```

Ardından `docker compose up -d` tekrar çalıştır.

---

## 8. Bilinen Eksikler / Yapılacaklar

| Konu | Durum | Not |
|---|---|---|
| Redis önbellekleme | Eksik | Redis kurulu ama analiz akışında kullanılmıyor |
| Async Ollama çağrısı | Eksik | `requests` → `httpx` geçişi gerekiyor |
| Ollama model auto-pull | Eksik | İlk kurulumda manuel `ollama pull` gerekiyor |
| Redis veri kalıcılığı | Eksik | Container restart'ta Redis verisi kayboluyor |
| `allow_origins=["*"]` | Üretimde kısıtlanmalı | Şu an tüm origin'lere açık |
| Frontend API URL | Build-time sabit | Flutter web app `API_BASE_URL`'i build sırasında alıyor |

---

## 9. Üretim (Production) için Notlar

Üretime almadan önce şunları yap:

1. `.env` dosyasında `JWT_SECRET_KEY` değerini güvenli ve uzun bir string ile değiştir
2. `backend/app/main.py` içindeki `allow_origins=["*"]` satırını gerçek domain ile kısıtla
3. PostgreSQL için güçlü şifre kullan
4. Ollama için daha büyük model düşün (`llama3.1:8b`, `mistral` vb.)
5. Backend önünde Nginx veya Traefik ile HTTPS terminasyonu ekle
6. Redis için password authentication ekle
7. `docker-compose.yml` içinde Redis'e volume ekle (veri kalıcılığı için)
