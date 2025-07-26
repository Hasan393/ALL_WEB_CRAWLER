"""
Crawl4AI-based single-page spider.
Asks the user for ONE starting URL, then:
1. Crawls every link that is on the same topic (same netloc / base path).
2. Never visits the same URL twice.
3. Saves the raw HTML of every page to baka.txt (creates the file if it does not exist).
4. Uses zero LLM; no summarization, no cleaning – just dumps raw bytes.
"""

import os
import re
from urllib.parse import urljoin, urlparse

from crawl4ai import AsyncWebCrawler
import asyncio


# ------------------------------------------------------------------
# Helper: decide if a link should be followed
# ------------------------------------------------------------------
def same_topic(base_url: str, candidate: str) -> bool:
    """
    Very naïve “stay on topic” rule:
    – must share the same scheme + netloc
    – must share the same first path segment (or be a sub-path)
    """
    base = urlparse(base_url)
    cand = urlparse(candidate)

    if cand.scheme not in {"http", "https"}:
        return False
    if cand.netloc != base.netloc:
        return False

    # Optional: keep only sub-paths
    base_path = base.path.rstrip("/")
    cand_path = cand.path.rstrip("/")
    if not cand_path.startswith(base_path):
        return False

    return True


# ------------------------------------------------------------------
# Crawler
# ------------------------------------------------------------------
async def crawl_single_site(start_url: str):
    seen = set()
    to_visit = [start_url]
    output_path = "baka.txt"

    # Create / truncate the file once
    open(output_path, "wb").close()

    async with AsyncWebCrawler(verbose=False) as crawler:
        while to_visit:
            url = to_visit.pop(0)
            if url in seen:
                continue
            seen.add(url)

            try:
                result = await crawler.arun(url=url)
                if not result.success:
                    print(f"[SKIP] {url} – {result.error_message}")
                    continue

                print(f"[OK] {url} ({len(result.html)} bytes)")

                # Save raw HTML to file
                with open(output_path, "ab") as f:
                    f.write(f"\n\n<!-- URL: {url} -->\n\n".encode("utf-8"))
                    f.write(result.html.encode("utf-8"))

                # Extract links for further crawling
                links = re.findall(r'href=["\'](.*?)["\']', result.html, flags=re.I)
                for raw_link in links:
                    absolute = urljoin(url, raw_link.split("#")[0])
                    absolute = absolute.split("?")[0]  # strip query to avoid duplicates
                    if absolute not in seen and same_topic(start_url, absolute):
                        to_visit.append(absolute)

            except Exception as e:
                print(f"[ERROR] {url} – {e}")


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------
if __name__ == "__main__":
    user_url = input("Enter the URL to crawl: ").strip()
    if not user_url:
        print("No URL supplied – exiting.")
    else:
        asyncio.run(crawl_single_site(user_url))