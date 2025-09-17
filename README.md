# RAG-NOTES

Bot Discord + Scraper Twitter/X (Playwright) pour extraire textes/images et pousser vers un backend RAG via API.

## ⚙️ Prérequis
- Python 3.11+
- (Option) Docker / Docker Compose
- Discord bot token + intents activés (Message Content Intent)

## 🚀 Démarrage rapide
```bash
cp .env.example .env
make install
make init
make run
````

## 🧪 Qualité

* **Ruff** pour lint/format: `make qa` (`ruff check .`) et `make fmt`.
* **Pytest** minimal et stable en CI.

## 🐳 Docker

```bash
make docker-build
make docker-run
```

Monte le dossier `./data` pour persister les images.

##  Variables d’env

Voir `.env.example`. Points clés :

* `API_URL`: endpoint de votre service RAG (ex: `http://localhost:5000/`).
* `CHANNEL_ID_*`: IDs entiers des canaux Discord à surveiller.
* `IMAGES_FOLDER`: dossier local de stockage des images.

## Intégration code

* `twitter_extractor.py` utilise Playwright (Chromium) pour extraire les URLs d’images et les télécharger.
* `bot.py` consomme `result_queue` et envoie les images/base64 au backend via `add_data`.

## Scripts d’init

* `init_dirs.py`: crée `./data` et `./data/images`.
* `init_playwright.py`: sanity check Playwright.
* `init_dbs.py`: no-op par défaut (DB gérée par le backend RAG).

## CI/CD(rom)

* **CI**: lint + tests + build image (GHCR `:latest`).
* **CD**: tag `vX.Y.Z` → release + push image tagguée.

##  Notes

* En production Docker, pensez à fournir `.env` et à monter `./data`.
* Si l’API RAG (https://github.com/TristanStark/Generic-Assistant) est indisponible, vous pouvez implémenter un fallback local dans `scripts/init_dbs.py`.

```
