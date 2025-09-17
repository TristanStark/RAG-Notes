# Optionnel: forcer l’install chromium si non présent
try:
    from playwright.sync_api import sync_playwright  # noqa: F401
    print("[init] Playwright import OK")
except Exception as e:
    print(f"[init] Playwright missing? {e}")
