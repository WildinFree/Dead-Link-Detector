def clean_url(url):
    """Remove duplicates and normalize URLs."""
    return url.strip().lower()

def deduplicate_urls(urls):
    """Remove duplicate URLs."""
    return list(dict.fromkeys(urls))