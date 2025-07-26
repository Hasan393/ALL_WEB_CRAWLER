# crawl_llama4.py
import asyncio
import aiofiles
import os
import logging
from typing import List

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from pydantic import BaseModel, Field

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("crawl_llama4")

# ------------------------------------------------------------------
# 1. Ask user for number of pages and the URLs
# ------------------------------------------------------------------
def get_user_urls() -> List[str]:
    while True:
        try:
            n = int(input("How many pages do you want to crawl? (1-99): ").strip())
            if 1 <= n <= 99:
                break
            else:
                print("Please enter a number between 1 and 99.")
        except ValueError:
            print("Not a valid integer. Try again.")

    urls = []
    for i in range(1, n + 1):
        url = input(f"Enter URL #{i}: ").strip()
        if not url.startswith("http"):
            url = "https://" + url
        urls.append(url)
    return urls


# ------------------------------------------------------------------
# 2. Pydantic schema for LLM answer
# ------------------------------------------------------------------
class SimpleContent(BaseModel):
    content: str = Field(..., description="The direct textual answer / main content")


# ------------------------------------------------------------------
# 3. Async crawl with robust retry + Groq llama-4-scout
# ------------------------------------------------------------------
async def crawl_url(crawler: AsyncWebCrawler, url: str) -> str:
    logger.info(f"Starting crawl: {url}")
    try:
        result = await crawler.arun(
            url=url,
            timeout=45000,  # 45 seconds
            config=CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                extraction_strategy=LLMExtractionStrategy(
                    llm_config=LLMConfig(
                        provider="groq/meta-llama/llama-4-scout-17b-16e-instruct",
                        api_token=os.getenv("GROQ_API_KEY"),
                    ),
                    schema=SimpleContent.model_json_schema(),
                    extraction_type="schema",
                    instruction=(
                        "Extract the main textual content / direct answer only, "
                        "no boilerplate, no navigation, no footer."
                    ),
                    extra_args={"temperature": 0.1, "max_tokens": 2000},
                ),
            ),
        )

        if not result.success:
            logger.warning(f"Failed crawl for {url}: {result.error_message}")
            return f"[ERROR] {url} -> {result.error_message}"

        # Parse LLM JSON
        try:
            obj = SimpleContent.model_validate_json(result.extracted_content)
            return obj.content.strip()
        except Exception:
            # Fallback to raw markdown
            logger.warning(f"LLM JSON failed for {url}, returning raw markdown")
            return result.markdown.strip()

    except Exception as e:
        logger.exception(f"Unhandled exception for {url}")
        return f"[ERROR] {url} -> {e}"


# ------------------------------------------------------------------
# 4. Crawl all URLs
# ------------------------------------------------------------------
async def crawl_all(urls: List[str]) -> List[str]:
    async with AsyncWebCrawler() as crawler:
        tasks = [crawl_url(crawler, u) for u in urls]
        return await asyncio.gather(*tasks)


# ------------------------------------------------------------------
# 5. Save results to main.txt
# ------------------------------------------------------------------
async def save_to_file(results: List[str], filename: str = "main.txt"):
    async with aiofiles.open(filename, "w", encoding="utf-8") as f:
        for idx, line in enumerate(results, 1):
            await f.write(f"=== Result #{idx} ===\n")
            await f.write(line + "\n\n")
    logger.info(f"All results saved to {filename}")


# ------------------------------------------------------------------
# 6. Entrypoint
# ------------------------------------------------------------------
async def main():
    urls = get_user_urls()
    logger.info(f"Collected {len(urls)} URLs. Starting crawl...")
    results = await crawl_all(urls)
    await save_to_file(results)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Aborted by user.")