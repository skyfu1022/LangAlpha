---
name: web-scraping
description: "Web scraping with Scrapling: fast HTTP requests, dynamic browser rendering, anti-bot bypass, CSS/XPath selectors, and multi-page crawling with spiders"
license: MIT
---

# Web Scraping with Scrapling

## Overview

Scrapling is a high-performance web scraping library with three fetcher tiers,
intelligent element selection, and a spider framework for multi-page crawls.
Use it when you need to extract structured data from websites, handle
JavaScript-rendered content, or bypass anti-bot protections.

## When to Use Each Fetcher

| Scenario | Fetcher | Why |
|----------|---------|-----|
| Static HTML pages, APIs, RSS feeds | `get` / `AsyncFetcher` | Fastest. HTTP-only, no browser overhead. |
| JS-rendered SPAs (React, Vue, Angular) | `fetch` / `DynamicFetcher` | Runs Chromium, waits for JS execution. |
| Cloudflare-protected sites | `stealthy_fetch` / `StealthyFetcher` | Solves Turnstile challenges, fingerprint spoofing. |
| Multiple URLs in parallel | `bulk_get` / `bulk_fetch` MCP tools | Concurrent fetching with session reuse. |
| Multi-page crawl with pagination | `Spider` framework | Pause/resume, concurrent requests, export. |

## Quick Start: MCP Tools (Recommended)

The Scrapling MCP tools are available in your sandbox. Use them via execute_code:

```python
# Fast HTTP fetch -> markdown
result = get(url="https://example.com", extraction_type="markdown")
print(result)

# JS-rendered page
result = fetch(url="https://spa-website.com", extraction_type="markdown", network_idle=True)
print(result)

# Cloudflare-protected site
result = stealthy_fetch(
    url="https://protected-site.com",
    extraction_type="markdown",
    solve_cloudflare=True
)
print(result)

# Bulk fetch multiple URLs
results = bulk_get(
    urls=["https://example.com/page1", "https://example.com/page2"],
    extraction_type="markdown"
)
for r in results:
    print(r)
```

### MCP Tool Parameters

All tools accept:
- `extraction_type`: `"markdown"` (default), `"html"`, or `"text"`
- `css_selector`: Target specific elements (e.g., `"article.content"`)
- `main_content_only`: Extract only `<body>` content (default: True)

Browser-based tools (`fetch`, `stealthy_fetch`) also accept:
- `headless`: Run browser hidden (default: True)
- `disable_resources`: Skip fonts/images for speed (default: False)
- `network_idle`: Wait for all network requests to finish (default: False)
- `timeout`: Timeout in milliseconds (default: 30000)
- `wait_selector`: Wait for a CSS selector before extracting
- `proxy`: Proxy server URL

`stealthy_fetch` additionally accepts:
- `solve_cloudflare`: Bypass Cloudflare protection (default: False)
- `real_chrome`: Use locally installed Chrome (default: False)
- `hide_canvas`: Add noise to canvas for fingerprint evasion

## Direct Python API

For advanced use cases, import Scrapling directly:

### Fetcher (Fast HTTP)

```python
from scrapling.fetchers import Fetcher, AsyncFetcher

# Sync
page = Fetcher.get("https://example.com", stealthy_headers=True)
print(page.status)  # 200

# Async
page = await AsyncFetcher.get("https://example.com", stealthy_headers=True)

# With browser impersonation
page = Fetcher.get("https://example.com", impersonate="chrome")

# Response properties
print(page.status)       # HTTP status code
print(page.body)         # Raw bytes
print(page.encoding)     # Response encoding
print(page.cookies)      # Response cookies
print(page.headers)      # Response headers

# CSS selectors (Scrapy-style pseudo-elements)
titles = page.css("h1::text").getall()
links = page.css("a::attr(href)").getall()
first_p = page.css("p::text").get()

# XPath
items = page.xpath("//div[@class='item']/text()").getall()

# BeautifulSoup-style
divs = page.find_all("div", class_="content")
```

### DynamicFetcher (Browser)

```python
from scrapling.fetchers import DynamicFetcher

page = await DynamicFetcher.async_fetch(
    "https://spa-website.com",
    headless=True,
    network_idle=True,           # Wait for all XHR/fetch to complete
    disable_resources=True,      # Skip images/fonts for speed
    timeout=30000,               # 30s timeout
    wait_selector=".data-table", # Wait for this element
)

# Extract data
rows = page.css("table.data-table tr")
for row in rows:
    cells = row.css("td::text").getall()
    print(cells)
```

### StealthyFetcher (Anti-Bot Bypass)

```python
from scrapling.fetchers import StealthyFetcher

page = await StealthyFetcher.async_fetch(
    "https://protected-site.com",
    headless=True,
    solve_cloudflare=True,   # Auto-solve Cloudflare challenges
    network_idle=True,
    google_search=True,      # Set referer as if from Google
    hide_canvas=True,        # Canvas fingerprint evasion
)
print(page.status)  # 200 after bypass
```

### Sessions (Persistent Connections)

```python
from scrapling.fetchers import FetcherSession

# Session with cookie persistence
with FetcherSession(impersonate="chrome") as session:
    # Login
    login_page = session.post("https://site.com/login", data={...})

    # Subsequent requests share cookies
    dashboard = session.get("https://site.com/dashboard")
    data = dashboard.css(".user-data::text").getall()
```

### Spider (Multi-Page Crawl)

```python
from scrapling.spiders import Spider, Request, Response

class PriceScraper(Spider):
    name = "prices"
    start_urls = ["https://example.com/products"]
    concurrent_requests = 5

    async def parse(self, response: Response):
        # Extract data from current page
        for product in response.css(".product"):
            yield {
                "name": product.css(".name::text").get(),
                "price": product.css(".price::text").get(),
            }

        # Follow pagination
        next_page = response.css("a.next::attr(href)").get()
        if next_page:
            yield Request(next_page)

# Run spider
spider = PriceScraper()
result = spider.start()
result.items.to_json("results/prices.json")
```

## Converting HTML to Markdown

When you need markdown from raw HTML:

```python
import html2text

converter = html2text.HTML2Text()
converter.body_width = 0  # No line wrapping
markdown = converter.handle(html_string)
```

## CLI (Terminal)

```bash
# Quick page-to-markdown
scrapling extract get "https://example.com" output.md

# With CSS selector
scrapling extract get "https://example.com" output.md --css "article.content"

# Dynamic fetch (browser)
scrapling extract fetch "https://spa-site.com" output.md

# Stealth fetch (anti-bot)
scrapling extract stealthy-fetch "https://protected.com" output.md --solve-cloudflare
```

## Best Practices

1. **Start with `get` (Tier 1)** -- fastest, lowest resource usage. Only escalate if content is empty or blocked.
2. **Use `extraction_type="markdown"`** for LLM-ready content.
3. **Use `css_selector`** to extract only the content you need -- reduces noise and tokens.
4. **Use `disable_resources=True`** with browser fetchers to skip images/fonts and speed up loading.
5. **Use `network_idle=True`** for SPAs that load data via XHR/fetch after initial page load.
6. **Use sessions** when making multiple requests to the same site (cookie/auth persistence).
7. **Use spiders** for structured multi-page crawls with pagination.
8. **Save results** to `results/` directory for the user to download.
