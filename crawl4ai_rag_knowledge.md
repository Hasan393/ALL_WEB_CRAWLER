Below is a *ready-to-index* Markdown corpus distilled from the three crawl results.  
It keeps every technical detail that matters for RAG (URLs, parameters, code, configuration keys, etc.) while removing navigation chrome and duplication.  
Simply feed the file into your vector DB or chunk it further—the headings and fenced code blocks give the retriever strong lexical cues.

---

# Crawl4AI v0.7.x – RAG-Ready Knowledge Base

## 1. Library Entry Points
| Entry Point | Purpose |
|-------------|---------|
| AsyncWebCrawler | High-level async crawler |
| arun() | Single-URL crawl |
| arun_many() | Batch crawl |
| CrawlerRunConfig | **One-stop object** for filtering, extraction, and media settings |
| BrowserConfig | Playwright browser tuning |

---

## 2. Core Configuration (`CrawlerRunConfig`)

| Key | Type | Description | Example |
|-----|------|-------------|---------|
| `css_selector` | str | Restrict scrape to one CSS scope | `"main.content"` |
| `target_elements` | List[str] | Like `css_selector` but *multi* scope and keeps page context | `["article", ".sidebar"]` |
| `word_count_threshold` | int | Drop text blocks shorter than N words | `15` |
| `excluded_tags` | List[str] | Strip entire tags | `["nav","footer","form"]` |
| `exclude_external_links` | bool | Discard off-domain links | `True` |
| `exclude_social_media_links` | bool | Skip known social platforms | `True` |
| `exclude_domains` | List[str] | Custom blacklist | `["adsite.net"]` |
| `exclude_external_images` | bool | Remove 3rd-party images | `True` |
| `exclude_all_images` | bool | Remove *every* `<img>` | `False` |
| `process_iframes` | bool | Inline iframe HTML | `True` |
| `wait_for_images` | bool | Block until images load | `True` |
| `screenshot` | bool | Base64 full-page PNG in `result.screenshot` | `False` |
| `pdf` | bool | PDF snapshot in `result.pdf` | `False` |
| `capture_mhtml` | bool | Single-file MHTML archive | `False` |

---

## 3. Result Object (`CrawlResult`)

```json
{
  "url": "https://example.com",
  "success": true,
  "cleaned_html": "<html>...</html>",
  "markdown": "...",
  "links": {
    "internal": [{ "href": "...", "text": "...", "title": "...", "base_domain": "..." }],
    "external": [...]
  },
  "media": {
    "images": [
      {
        "src": "https://cdn...jpg",
        "alt": "...",
        "desc": "...",
        "score": 3,
        "width": 800,
        "height": 600
      }
    ],
    "tables": [
      {
        "headers": ["Name", "Age"],
        "rows": [["Alice", "30"]],
        "caption": "Staff"
      }
    ]
  },
  "screenshot": "...base64...",
  "pdf": "...base64...",
  "mhtml": "...raw MHTML...",
  "error_message": null
}
```

---

## 4. Link & Media Deep-Dive

### 4.1 Basic Link Extraction
```python
from crawl4ai import AsyncWebCrawler

async with AsyncWebCrawler() as crawler:
    result = await crawler.arun("https://example.com")
    internal = result.links["internal"]
    external = result.links["external"]
```

### 4.2 Advanced Link Head Extraction
Provides **intrinsic**, **contextual (BM25)**, and **total** scores plus `<head>` metadata.

```python
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.async_configs import LinkPreviewConfig

config = CrawlerRunConfig(
    link_preview_config=LinkPreviewConfig(
        include_internal=True,
        include_external=False,
        max_links=20,
        concurrency=5,
        timeout=10,
        query="API documentation guide",
        score_threshold=0.3,
        verbose=True
    ),
    score_links=True
)
```

Returned link object:
```json
{
  "href": "https://docs.python.org/3.15/",
  "text": "Python 3.15 (in development)",
  "title": "3.15.0a0 Documentation",
  "base_domain": "docs.python.org",
  "intrinsic_score": 4.17,
  "contextual_score": 1.000,
  "total_score": 5.917,
  "head_data": {
    "title": "3.15.0a0 Documentation",
    "meta": { "description": "The official Python documentation..." }
  }
}
```

---

## 5. Table Recognition
Tables scoring ≥ 7 (default) are auto-extracted.

```python
crawler_cfg = CrawlerRunConfig(
    table_score_threshold=5  # lower ⇒ more tables
)
```

---

## 6. LLM-Driven JSON Extraction

### 6.1 Pydantic Schema Example
```python
from pydantic import BaseModel
from crawl4ai import LLMExtractionStrategy, LLMConfig, CrawlerRunConfig

class Product(BaseModel):
    name: str
    price: str

llm_strategy = LLMExtractionStrategy(
    llm_config=LLMConfig(provider="openai/gpt-4o-mini",
                         api_token="sk-..."),
    schema=Product.model_json_schema(),
    extraction_type="schema",
    instruction="Extract products with name and price.",
    chunk_token_threshold=1200,
    overlap_rate=0.1,
    apply_chunking=True,
    input_format="markdown",
    extra_args={"temperature": 0.0, "max_tokens": 800}
)

crawl_cfg = CrawlerRunConfig(extraction_strategy=llm_strategy)
```

### 6.2 Knowledge-Graph Use Case
```python
class Entity(BaseModel):
    name: str
    description: str

class Relationship(BaseModel):
    entity1: Entity
    entity2: Entity
    relation_type: str
    description: str

class KnowledgeGraph(BaseModel):
    entities: List[Entity]
    relationships: List[Relationship]
```

---

## 7. Performance Tips

| Strategy | Speed-up |
|----------|----------|
| Switch to `LXMLWebScrapingStrategy()` | 10-20× on large HTML |
| Raise `concurrency` in `LinkPreviewConfig` | Faster link head extraction |
| Reduce `chunk_token_threshold` + enable overlap | Lower LLM cost |
| Use `exclude_external_images=True` | Cuts memory & bandwidth |

---

## 8. One-Shot Combined Config
```python
crawler_cfg = CrawlerRunConfig(
    css_selector="#main-content",
    excluded_tags=["nav", "footer"],
    exclude_external_links=True,
    exclude_domains=["badads.com"],
    exclude_external_images=True,
    wait_for_images=True,
    process_iframes=True,
    extraction_strategy=my_strategy,   # LLM or CSS-based
    cache_mode=CacheMode.BYPASS
)
```

---

## 9. Quick Copy-Paste Indexes

### 9.1 Minimal RAG Setup
```bash
pip install crawl4ai
export OPENAI_API_KEY="sk-..."
```

```python
import asyncio, json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, LLMExtractionStrategy, LLMConfig

class QA(BaseModel):
    question: str
    answer: str

async def rag_seed(url):
    cfg = CrawlerRunConfig(
        extraction_strategy=LLMExtractionStrategy(
            llm_config=LLMConfig(provider="openai/gpt-4o-mini"),
            schema=QA.model_json_schema(),
            instruction="Generate 3 Q&A pairs from the article."
        )
    )
    async with AsyncWebCrawler() as crawler:
        r = await crawler.arun(url, config=cfg)
        return json.loads(r.extracted_content)

if __name__ == "__main__":
    pairs = asyncio.run(rag_seed("https://docs.crawl4ai.com/core/quickstart/"))
    print(pairs)
```

---

