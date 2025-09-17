from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup


def upgrade_twitter_image_url(url, target_size="4096x4096"):
    """
    Remplace le paramètre name dans l'URL Twitter pour demander la plus haute résolution disponible.
    """
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    if 'name' in qs:
        qs['name'] = [target_size]
    else:
        # Add it if it doesn't exist at all
        qs.update({'name': [target_size]})

    new_query = urlencode(qs, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def extract_tweet_data(tweet_url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print(f"✅ Navigating to: {tweet_url}")
        page.goto(tweet_url, timeout=60000)
        page.wait_for_timeout(5000)

        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")

    # Essayons d'extraire le texte
    tweet_text = None
    images = []

    # Twitter rend généralement le texte du tweet en <span> avec data-testid="tweetText"
    tweet_spans = soup.find_all(attrs={"data-testid": "tweetText"})
    if tweet_spans:
        tweet_text = " ".join([span.get_text(separator=" ", strip=True) for span in tweet_spans])

    # Images (les balises img avec src vers pbs.twimg.com)
    for img in soup.find_all("img"):
        src = img.get("src")
        if src and "pbs.twimg.com" in src and not "profile_images" in src:
            images.append(upgrade_twitter_image_url(src))

    return {
        "text": tweet_text,
        "images": list(set(images))
    }

if __name__ == "__main__":
    url = "https://x.com/artfanszone/status/1943726625633227198"
    data = extract_tweet_data(url)
    print("✅ TWEET TEXT:", data["text"])
    print("✅ IMAGES:", data["images"])
