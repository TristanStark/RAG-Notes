import os
import requests
import threading
from queue import Queue, Empty
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import base64
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

class TwitterScraper:
    def __init__(self, images_folder="H:\\github\\Les Reliques des Aînées Assistant\\Generic Assistant\\images2", poll_interval=5, max_retries=3):
        self.images_folder = images_folder
        self.queue = Queue()
        self.result_queue = Queue()
        self.poll_interval = poll_interval
        self.max_retries = max_retries
        self.retry_counts = {}
        self.running = False

    def add_url(self, tweet_url):
        """
        Add a tweet URL to the queue.
        """
        print(f"[ADDED] URL added to queue: {tweet_url}")
        self.queue.put(tweet_url)

    def upgrade_twitter_image_url(self, url, target_size="4096x4096"):
        """
        Replace 'name' parameter in Twitter image URL to request highest resolution.
        """
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        qs['name'] = [target_size]
        new_query = urlencode(qs, doseq=True)
        return urlunparse(parsed._replace(query=new_query))

    def playwright_scrape(self, tweet_url):
        """
        Use Playwright to load the tweet page and extract text and images.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            print(f"[SCRAPER] Navigating to: {tweet_url}")
            page.goto(tweet_url, timeout=60000)
            page.wait_for_timeout(5000)
            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, "html.parser")
        tweet_text = None
        images = []

        # Extract tweet text
        tweet_spans = soup.find_all(attrs={"data-testid": "tweetText"})
        if tweet_spans:
            tweet_text = " ".join([span.get_text(separator=" ", strip=True) for span in tweet_spans])

        # Extract images
        for img in soup.find_all("img"):
            src = img.get("src")
            if src and "pbs.twimg.com" in src and "profile_images" not in src:
                images.append(self.upgrade_twitter_image_url(src))

        return {
            "text": tweet_text,
            "images": list(set(images))
        }

    def download_image(self, url, filename=None):
        """
        Download image from URL to local images folder.
        """
        os.makedirs(self.images_folder, exist_ok=True)
        if not filename:
            filename = url.split("/")[-1].split("?")[0] + ".jpg"

        try:
            response = requests.get(url)
            if response.status_code == 200:
                path = os.path.join(self.images_folder, filename)
                with open(path, "wb") as f:
                    f.write(response.content)
                
                return path, base64.b64encode(response.content).decode('utf-8'), filename
            else:
                print(f"[ERROR] Failed to download image: {url} (status {response.status_code})")
        except Exception as e:
            print(f"[ERROR] Error downloading image: {e}")

        return None

    def process_tweet_url(self, tweet_url):
        """
        Main processing pipeline for a single tweet URL.
        Returns True if successful, False otherwise.
        """
        print(f"[INFO] Processing tweet URL: {tweet_url}")

        try:
            data = self.playwright_scrape(tweet_url)
        except Exception as e:
            print(f"[ERROR] Playwright failed: {e}")
            return False, []

        print("[RESULT] Text:", data["text"])
        local_image_paths = []
        base64_images = []
        filenames = []

        for image_url in data["images"]:
            local_path, base64_image, filename = self.download_image(image_url)
            if local_path:
                local_image_paths.append(local_path)
                base64_images.append(base64_image)
                filenames.append(filename)
                print(f"[RESULT] Image downloaded to: {local_path}")

        # Example: insert into DB / FAISS
        # agent.add_data_and_update_index(base_name="tweets", payload={"text": data["text"], "image_path": local_path})

        print(f"[RESULT] Processing complete for tweet: {tweet_url}")
        return True, local_image_paths, base64_images, filenames

    def worker_loop(self):
        """
        Worker thread: continuously consumes the queue.
        """
        print("[LOOP] Worker loop started.")
        while self.running:
            try:
                tweet_url = self.queue.get(timeout=self.poll_interval)
                print(f"[WORKING] Got tweet URL from queue: {tweet_url}")

                success, local_image_paths, base64_images, filenames = self.process_tweet_url(tweet_url)
                retries = self.retry_counts.get(tweet_url, 0)

                if not success:
                    retries += 1
                    self.retry_counts[tweet_url] = retries

                    if retries < self.max_retries:
                        print(f"[WARNING] Requeuing tweet URL (attempt {retries}): {tweet_url}")
                        self.queue.put(tweet_url)
                    else:
                        print(f"[ERROR] Max retries reached for tweet URL. Dropping: {tweet_url}")
                else:
                    if tweet_url in self.retry_counts:
                        del self.retry_counts[tweet_url]

                # Notify result
                result = {
                    "tweet_url": tweet_url,
                    "status": "success" if success else "failure",
                    "retries": retries,
                    "images": local_image_paths,
                    "base64_images": base64_images,
                    "filenames": filenames,
                    "message": "Processed successfully" if success else f"Processing failed after {retries} attempt(s)"
                }
                self.result_queue.put(result)

                self.queue.task_done()

            except Empty:
                pass  # No new items, poll again

    def start(self):
        """
        Start the background worker.
        """
        print("[INFO] Starting TwitterScraper service...")
        self.running = True
        self.worker_thread = threading.Thread(target=self.worker_loop, daemon=True)
        self.worker_thread.start()

    def stop(self):
        """
        Stop the background worker.
        """
        print("[STOPPED] Stopping TwitterScraper service...")
        self.running = False
        self.worker_thread.join()
        print("[STOPPED] Stopped.")


if __name__ == "__main__":
    scraper = TwitterScraper(images_folder="./images", max_retries=3)
    scraper.start()

    # EXAMPLE: add some URLs
    scraper.add_url("https://x.com/artfanszone/status/1943726625633227198")

    try:
        while True:
            try:
                # Wait for any results
                result = scraper.result_queue.get(timeout=5)
                print(f"[RESULT] Result: {result}")
                print(f"Images downloaded: {', '.join(result['images']) if result['images'] else 'None'}")
            except Empty:
                pass  # No result yet
    except KeyboardInterrupt:
        scraper.stop()
