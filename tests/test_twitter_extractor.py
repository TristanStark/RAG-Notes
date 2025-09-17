from rag_notes.twitter_extractor import TwitterScraper


def test_upgrade_twitter_image_url_sets_high_res():
    s = TwitterScraper(images_folder="./tmp")
    url = "https://pbs.twimg.com/media/EXAMPLE.jpg?name=small"
    upgraded = s.upgrade_twitter_image_url(url)
    assert "name=4096x4096" in upgraded


def test_add_url_puts_in_queue(tmp_path):
    s = TwitterScraper(images_folder=str(tmp_path))
    s.start()
    try:
        s.add_url("https://x.com/whatever/status/123")
        # On ne consomme pas la queue, on vérifie juste qu’on peut y mettre
        assert not s.queue.empty()
    finally:
        s.stop()
