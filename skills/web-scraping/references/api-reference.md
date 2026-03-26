# Scrapling API Reference

Offline reference for the Scrapling web-scraping library. Source: <https://scrapling.readthedocs.io/en/latest/>

---

## Table of Contents

1. [Installation](#installation)
2. [Fetcher (HTTP Requests)](#fetcher-http-requests)
3. [AsyncFetcher](#asyncfetcher)
4. [FetcherSession](#fetchersession)
5. [DynamicFetcher (Browser)](#dynamicfetcher-browser)
6. [DynamicSession / AsyncDynamicSession](#dynamicsession--asyncdynamicsession)
7. [StealthyFetcher (Anti-Bot)](#stealthyfetcher-anti-bot)
8. [StealthySession / AsyncStealthySession](#stealthysession--asyncstealthysession)
9. [Fetcher Comparison](#fetcher-comparison)
10. [ProxyRotator](#proxyrotator)
11. [Response Object](#response-object)
12. [Selector](#selector)
13. [Selectors Collection](#selectors-collection)
14. [Custom Types (TextHandler, TextHandlers, AttributesHandler)](#custom-types)
15. [Spider](#spider)
16. [Spider Request Object](#spider-request-object)
17. [Spider Response.follow()](#spider-responsefollow)
18. [Spider Sessions (SessionManager)](#spider-sessions-sessionmanager)
19. [Spider CrawlResult / CrawlStats / ItemList](#spider-crawlresult--crawlstats--itemlist)
20. [Spider Advanced Features](#spider-advanced-features)
21. [MCP Server](#mcp-server)
22. [CLI](#cli)

---

## Installation

```bash
pip install scrapling            # core library
pip install "scrapling[ai]"      # with MCP server support
pip install "scrapling[shell]"   # with interactive shell support
scrapling install                # install browser dependencies (Playwright browsers)
```

Docker images:

```bash
docker pull pyd4vinci/scrapling
docker pull ghcr.io/d4vinci/scrapling:latest
```

---

## Fetcher (HTTP Requests)

Lightweight HTTP fetcher using `curl_cffi` with browser TLS fingerprint impersonation.

```python
from scrapling.fetchers import Fetcher
```

### Class Methods

`Fetcher.get()`, `Fetcher.post()`, `Fetcher.put()`, `Fetcher.delete()` -- each returns a `Response`.

### Class Configuration Methods

| Method | Description |
|--------|-------------|
| `Fetcher.configure(**kwargs)` | Set parser arguments globally (see Parser Config below) |
| `Fetcher.display_config()` | Show current configuration |

### Shared Request Parameters

All HTTP methods (`get`, `post`, `put`, `delete`) accept these keyword arguments:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | required | Target URL |
| `stealthy_headers` | `bool` | `True` | Add real browser headers and Google referer |
| `follow_redirects` | `bool` | `True` | Follow HTTP redirections |
| `timeout` | `int` | `30` | Request timeout in seconds |
| `retries` | `int` | `3` | Retry attempts for failed requests |
| `retry_delay` | `int` | `1` | Seconds between retries |
| `impersonate` | `str \| list` | `"chrome"` | Browser TLS fingerprint (e.g. `"chrome110"`, `"firefox102"`, `"safari15_5"`) |
| `http3` | `bool` | `False` | Use HTTP/3 protocol |
| `cookies` | `dict \| list[dict]` | `None` | Request cookies |
| `proxy` | `str` | `None` | Proxy URL: `"http://user:pass@host:port"` |
| `proxy_auth` | `tuple` | `None` | `(username, password)` |
| `proxies` | `dict` | `None` | `{"http": url, "https": url}` |
| `proxy_rotator` | `ProxyRotator` | `None` | Automatic proxy rotation |
| `headers` | `dict` | `None` | Override generated headers |
| `max_redirects` | `int` | `30` | Max redirect chain length (`-1` = unlimited) |
| `verify` | `bool` | `True` | Verify HTTPS certificates |
| `cert` | `tuple` | `None` | `(cert_file, key_file)` for client certificates |
| `selector_config` | `dict` | `None` | Custom parsing arguments for Response/Selector |

### POST/PUT-Specific Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `data` | `dict` | Form data payload |
| `json` | `dict` | JSON payload |
| `params` | `dict` | Query string parameters (GET also supports this) |

### Parser Configuration Keywords

Passed to `Fetcher.configure()` or per-request via `selector_config`:

| Keyword | Type | Default | Description |
|---------|------|---------|-------------|
| `huge_tree` | `bool` | `True` | Enable large document parsing (libxml2) |
| `adaptive` | `bool` | `False` | Enable adaptive element relocation |
| `adaptive_domain` | `str` | `""` | Domain for adaptive strategies |
| `keep_comments` | `bool` | `False` | Preserve HTML comments |
| `keep_cdata` | `bool` | `False` | Preserve CDATA sections |
| `storage` | class | `SQLiteStorageSystem` | Storage backend for adaptive mode |
| `storage_args` | `dict` | `None` | Arguments for storage initialization |

### Example

```python
from scrapling.fetchers import Fetcher

page = Fetcher.get("https://example.com", impersonate="chrome", timeout=15)
print(page.status)
titles = page.css("h1::text").getall()
```

---

## AsyncFetcher

Async variant of `Fetcher` with identical API. Methods are coroutines.

```python
from scrapling.fetchers import AsyncFetcher

page = await AsyncFetcher.get("https://example.com")
```

---

## FetcherSession

Context manager for HTTP sessions with connection pooling, cookie persistence, and shared config. Up to 10x faster than individual `Fetcher` calls.

```python
from scrapling.fetchers import FetcherSession
```

### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `impersonate` | `str \| list` | `"chrome"` | Browser version to impersonate |
| `http3` | `bool` | `False` | Use HTTP/3 |
| `stealthy_headers` | `bool` | `True` | Add real browser headers |
| `proxies` | `dict` | `None` | `{"http": url, "https": url}` |
| `proxy` | `str` | `None` | Single proxy URL |
| `proxy_auth` | `tuple` | `None` | `(username, password)` |
| `proxy_rotator` | `ProxyRotator` | `None` | Automatic proxy rotation |
| `timeout` | `int \| float` | `30` | Request timeout in seconds |
| `headers` | `dict` | `None` | Default headers for all requests |
| `retries` | `int` | `3` | Retry attempts |
| `retry_delay` | `int` | `1` | Seconds between retries |
| `follow_redirects` | `bool` | `True` | Follow redirects |
| `max_redirects` | `int` | `30` | Max redirect chain |
| `verify` | `bool` | `True` | Verify HTTPS certificates |
| `cert` | `str \| tuple` | `None` | Client certificate |
| `selector_config` | `dict` | `None` | Selector config arguments |

### Usage

```python
# Sync
with FetcherSession(impersonate="chrome", http3=True) as session:
    page1 = session.get("https://example.com")
    page2 = session.post("https://example.com/api", json={"key": "val"})

# Async
async with FetcherSession(impersonate="safari") as session:
    tasks = [session.get(url) for url in urls]
    pages = await asyncio.gather(*tasks)
```

---

## DynamicFetcher (Browser)

Browser-based fetcher using Playwright (Chromium) for JavaScript-rendered pages.

```python
from scrapling.fetchers import DynamicFetcher
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | required | Target URL |
| `headless` | `bool` | `True` | Run browser hidden |
| `disable_resources` | `bool` | `False` | Block fonts, images, media, stylesheets (~25% speed boost) |
| `cookies` | `dict` | `None` | Browser cookies |
| `useragent` | `str` | `None` | Custom user agent (auto-generated if `None` in headless) |
| `network_idle` | `bool` | `False` | Wait 500ms with zero network connections |
| `load_dom` | `bool` | `True` | Wait for JS to fully load |
| `timeout` | `int` | `30000` | Timeout in **milliseconds** |
| `wait` | `int` | `None` | Additional wait after load (ms) |
| `page_action` | `Callable` | `None` | Function accepting Playwright `Page` for automation |
| `wait_selector` | `str` | `None` | CSS selector to wait for |
| `wait_selector_state` | `str` | `"attached"` | `attached`, `detached`, `visible`, `hidden` |
| `init_script` | `str` | `None` | Path to JS file executed on page creation |
| `google_search` | `bool` | `True` | Set Google referer header |
| `extra_headers` | `dict` | `None` | Additional HTTP headers |
| `proxy` | `str \| dict` | `None` | Proxy URL or dict `{"server", "username", "password"}` |
| `real_chrome` | `bool` | `False` | Use installed Google Chrome instead of Chromium |
| `locale` | `str` | system | Browser locale (e.g. `"en-GB"`) |
| `timezone_id` | `str` | system | Browser timezone |
| `cdp_url` | `str` | `None` | Chrome DevTools Protocol URL for remote browser |
| `user_data_dir` | `str` | temp | Browser user data directory |
| `extra_flags` | `list` | `None` | Additional browser launch flags |
| `additional_args` | `dict` | `None` | Extra Playwright context arguments |
| `selector_config` | `dict` | `None` | Custom parsing config |
| `blocked_domains` | `set` | `None` | Domain names to block (subdomains too) |
| `proxy_rotator` | `ProxyRotator` | `None` | Automatic proxy rotation |
| `retries` | `int` | `3` | Retry attempts |
| `retry_delay` | `int` | `1` | Seconds between retries |

### Methods

```python
# Synchronous
page = DynamicFetcher.fetch(url, **kwargs)

# Asynchronous
page = await DynamicFetcher.async_fetch(url, **kwargs)
```

### Wait Condition Order

1. `network_idle` -- wait for zero network activity for 500ms
2. `page_action` -- execute custom automation function
3. `wait_selector` + `wait_selector_state` -- wait for element condition
4. `load_dom` -- verify JS execution completion

### wait_selector_state Values

| Value | Meaning |
|-------|---------|
| `"attached"` | Element present in DOM (default) |
| `"detached"` | Element absent from DOM |
| `"visible"` | Non-empty bounding box, no `visibility:hidden` |
| `"hidden"` | Detached or invisible |

### Examples

```python
# Basic
page = DynamicFetcher.fetch("https://example.com")

# With resource blocking and domain blocking
page = DynamicFetcher.fetch(
    "https://example.com",
    disable_resources=True,
    blocked_domains={"ads.example.com", "tracker.net"},
)

# Wait for element
page = DynamicFetcher.fetch(
    "https://example.com",
    wait_selector="h1",
    wait_selector_state="visible",
)

# Browser automation
from playwright.sync_api import Page

def scroll_page(page: Page):
    page.mouse.wheel(10, 0)
    page.mouse.move(100, 400)

page = DynamicFetcher.fetch("https://example.com", page_action=scroll_page)

# Async automation
from playwright.async_api import Page as AsyncPage

async def scroll_async(page: AsyncPage):
    await page.mouse.wheel(10, 0)
    await page.mouse.move(100, 400)

page = await DynamicFetcher.async_fetch("https://example.com", page_action=scroll_async)
```

---

## DynamicSession / AsyncDynamicSession

Browser sessions that keep the browser open across multiple fetches.

```python
from scrapling.fetchers import DynamicSession, AsyncDynamicSession

# Sync
with DynamicSession(headless=True, disable_resources=True) as session:
    page1 = session.fetch("https://example1.com")
    page2 = session.fetch("https://example2.com")

# Async with tab pooling
async with AsyncDynamicSession(network_idle=True, max_pages=3) as session:
    pages = await asyncio.gather(
        session.fetch("https://spa1.com"),
        session.fetch("https://spa2.com"),
    )
```

### Per-Request Overrides (in `session.fetch()`)

`google_search`, `timeout`, `wait`, `page_action`, `extra_headers`, `disable_resources`, `wait_selector`, `wait_selector_state`, `network_idle`, `load_dom`, `blocked_domains`, `proxy`, `selector_config`.

---

## StealthyFetcher (Anti-Bot)

Extended `DynamicFetcher` with anti-bot protection bypass.

```python
from scrapling.fetchers import StealthyFetcher
```

### Additional Parameters (beyond DynamicFetcher)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `solve_cloudflare` | `bool` | `False` | Auto-solve Cloudflare Turnstile/Interstitial |
| `block_webrtc` | `bool` | `False` | Force WebRTC to respect proxy (prevent IP leak) |
| `hide_canvas` | `bool` | `False` | Add noise to canvas operations (anti-fingerprint) |
| `allow_webgl` | `bool` | `True` | Enable WebGL support |

Inherits all `DynamicFetcher` parameters.

### Methods

```python
page = StealthyFetcher.fetch(url, **kwargs)
page = await StealthyFetcher.async_fetch(url, **kwargs)
```

### Built-in Stealth Features

- Cloudflare JS/interactive/invisible challenge bypass
- Canvas fingerprinting prevention
- WebRTC leak blocking
- CDP runtime leak mitigation
- Headless mode detection patching
- Timezone mismatch defense

### Example

```python
page = StealthyFetcher.fetch(
    "https://protected-site.com",
    solve_cloudflare=True,
    block_webrtc=True,
    hide_canvas=True,
)
```

---

## StealthySession / AsyncStealthySession

Browser sessions with stealth features and tab pooling.

```python
from scrapling.fetchers import StealthySession, AsyncStealthySession

with StealthySession(solve_cloudflare=True) as session:
    page = session.fetch("https://protected.com")

async with AsyncStealthySession(solve_cloudflare=True, max_pages=3) as session:
    pages = await asyncio.gather(
        session.fetch("https://site1.com"),
        session.fetch("https://site2.com"),
    )
```

### Session Attributes

| Attribute | Description |
|-----------|-------------|
| `max_pages` | Maximum concurrent pages/tabs |
| `page_pool` | Internal page pool |
| `playwright` | Playwright instance |
| `context` | Browser context |
| `browser` | Browser instance |

### Session Methods

| Method | Description |
|--------|-------------|
| `start()` | Initialize session |
| `fetch(url, **kwargs)` | Fetch with stealth |
| `close()` | Clean up resources |
| `get_pool_stats()` | Page pool statistics |

---

## Fetcher Comparison

| Feature | Fetcher | DynamicFetcher | StealthyFetcher |
|---------|---------|----------------|-----------------|
| Speed | 5/5 | 3/5 | 3/5 |
| Stealth | 2/5 | 3/5 | 5/5 |
| Anti-Bot Options | 2/5 | 3/5 | 5/5 |
| JavaScript | No | Yes | Yes |
| Memory | Low | Medium | Medium |

**Use `Fetcher`** for simple HTTP requests, no JS needed.
**Use `DynamicFetcher`** for JS-heavy sites, browser automation, basic stealth.
**Use `StealthyFetcher`** for sites with Cloudflare or advanced anti-bot protections.

---

## ProxyRotator

Thread-safe proxy rotation with pluggable strategies.

```python
from scrapling.fetchers import ProxyRotator
```

### Constructor

```python
ProxyRotator(proxies, strategy=cyclic_rotation)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `proxies` | `list[str \| dict]` | required | Proxy URLs or Playwright-style dicts `{"server", "username", "password"}` |
| `strategy` | `Callable` | `cyclic_rotation` | `fn(proxies, current_index) -> (proxy, next_index)` |

### Methods / Properties

| Member | Returns | Description |
|--------|---------|-------------|
| `proxies` | `list` | Copy of all configured proxies |
| `get_proxy()` | proxy | Next proxy per rotation strategy |
| `__len__()` | `int` | Number of proxies |

### Custom Strategy Example

```python
import random

def random_strategy(proxies, current_index):
    idx = random.randint(0, len(proxies) - 1)
    return proxies[idx], idx

rotator = ProxyRotator(
    ["http://proxy1:8080", "http://proxy2:8080"],
    strategy=random_strategy,
)
```

### Usage with Fetchers

```python
rotator = ProxyRotator(["http://p1:8080", "http://p2:8080"])

# With Fetcher
page = Fetcher.get("https://example.com", proxy_rotator=rotator)

# With FetcherSession
with FetcherSession(proxy_rotator=rotator) as session:
    page = session.get("https://example.com")

# With DynamicSession (dict format for Playwright)
rotator = ProxyRotator([
    {"server": "http://p1:8080", "username": "u", "password": "p"},
])
with DynamicSession(proxy_rotator=rotator) as session:
    page = session.fetch("https://example.com")
```

> **Note**: Browser sessions cannot set proxies per-tab. `ProxyRotator` creates separate browser contexts per proxy automatically.

---

## Response Object

Returned by all fetchers. Inherits from `Selector`.

```python
from scrapling.engines.toolbelt.custom import Response
```

### Constructor

```python
Response(
    url, content, status, reason, cookies, headers, request_headers,
    encoding="utf-8", method="GET", history=None, meta=None, **selector_config
)
```

### HTTP Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `status` | `int` | HTTP status code |
| `reason` | `str` | HTTP reason phrase |
| `cookies` | `tuple[dict] \| dict` | Response cookies |
| `headers` | `dict` | Response headers |
| `request_headers` | `dict` | Original request headers |
| `history` | `list` | Redirect chain |
| `meta` | `dict[str, Any]` | Custom metadata (includes `"proxy"` when rotator used) |
| `request` | `Request \| None` | Associated spider Request |
| `url` | `str` | Response URL |
| `encoding` | `str` | Character encoding |

### Content Properties

| Property | Returns | Description |
|----------|---------|-------------|
| `body` | `bytes` | Raw response body |
| `text` | `TextHandler` | Text content of element |
| `tag` | `str` | Tag name |
| `attrib` | `dict` | Element attributes |
| `html_content` | `str` | Inner HTML |

### Data Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `json()` | `dict` | Parse body as JSON |
| `urljoin(relative_url)` | `str` | Resolve relative URL against response URL |

### String Representation

```python
str(response)  # "<200 https://example.com>"
```

All `Selector` methods (below) are also available on `Response`.

---

## Selector

Primary HTML parsing engine. `Response` inherits from this.

```python
from scrapling import Selector

sel = Selector(content="<html>...</html>", url="https://example.com")
```

### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `content` | `str \| bytes` | `None` | HTML content |
| `url` | `str` | `""` | URL stored for adaptive retrieval |
| `encoding` | `str` | `"utf-8"` | Character encoding |
| `huge_tree` | `bool` | `True` | Large document parsing (libxml2) |
| `root` | `HtmlElement` | `None` | Internal: pass etree object |
| `keep_comments` | `bool` | `False` | Preserve HTML comments |
| `keep_cdata` | `bool` | `False` | Preserve CDATA sections |
| `adaptive` | `bool` | `False` | Enable adaptive element relocation |
| `storage` | class | `SQLiteStorageSystem` | Storage backend |
| `storage_args` | `dict` | `None` | Storage init arguments |

### DOM Navigation Properties

| Property | Returns | Description |
|----------|---------|-------------|
| `parent` | `Selector \| None` | Direct parent |
| `children` | `list[Selector]` | Child elements |
| `siblings` | `list[Selector]` | Sibling elements |
| `below_elements` | `list[Selector]` | All descendants |
| `path` | `Selectors` | Path from root to element |
| `next` | `Selector \| None` | Next sibling |
| `previous` | `Selector \| None` | Previous sibling |

### Selector Generation Properties

| Property | Returns |
|----------|---------|
| `generate_css_selector` | CSS selector for this element |
| `generate_full_css_selector` | Full CSS selector from root |
| `generate_xpath_selector` | XPath for this element |
| `generate_full_xpath_selector` | Full XPath from root |

### Selection Methods

#### `css(selector, identifier="", adaptive=False, auto_save=False, percentage=0) -> Selectors`

CSS3 selector query. Supports pseudo-elements `::text` and `::attr(name)`.

```python
titles = page.css("h1::text").getall()
links = page.css("a::attr(href)").getall()
items = page.css("div.item")
```

#### `xpath(selector, identifier="", adaptive=False, auto_save=False, percentage=0, **kwargs) -> Selectors`

XPath query. Supports XPath variables via kwargs.

```python
items = page.xpath("//div[@class='item']")
```

#### `find_all(*args, **kwargs) -> Selectors`

Flexible element search by tag name, attribute dict, regex pattern, or callable filter.

```python
divs = page.find_all("div")
items = page.find_all("div", class_="item")
pattern_match = page.find_all(re.compile(r"h[1-6]"))
```

#### `find(*args, **kwargs) -> Selector | None`

Like `find_all` but returns only the first match or `None`.

### Text Extraction Methods

#### `get_all_text(separator="\n", strip=False, ignore_tags=("script", "style"), valid_values=True) -> TextHandler`

Concatenate all descendant text.

#### `re(regex, replace_entities=True, clean_match=False, case_sensitive=True) -> TextHandlers`

Apply regex to element text, return all matches.

#### `re_first(regex, default=None, replace_entities=True, clean_match=False, case_sensitive=True) -> TextHandler`

First regex match or default.

### Text Search Methods

#### `find_by_text(text, first_match=True, partial=False, case_sensitive=False, clean_match=True)`

Find elements by text content.

#### `find_by_regex(query, first_match=True, case_sensitive=False, clean_match=True)`

Find elements whose text matches a regex.

### Similarity Method

#### `find_similar(similarity_threshold=0.2, ignore_attributes=("href", "src"), match_text=False) -> Selectors`

Find structurally similar elements (same depth, tag, parent hierarchy).

### Serialization Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `get()` | `TextHandler` | Outer HTML (or text for pseudo-element results) |
| `getall()` | `TextHandlers` | Single-element list with serialized string |
| `prettify()` | `TextHandler` | Formatted inner HTML |

### Utility Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `has_class(class_name)` | `bool` | Check CSS class |
| `iterancestors()` | generator | Yield all ancestors |
| `find_ancestor(func)` | `Selector \| None` | First ancestor matching predicate |
| `__getitem__(key)` | `TextHandler` | Get attribute by key |
| `__contains__(key)` | `bool` | Check attribute existence |

### Adaptive Methods

| Method | Description |
|--------|-------------|
| `save(element, identifier)` | Persist element for adaptive relocation |
| `retrieve(identifier)` | Retrieve saved element data |
| `relocate(element, percentage=0, selector_type=False)` | Relocate element after page structure change |

---

## Selectors Collection

Extends `list` with batch operations. Returned by `css()`, `xpath()`, `find_all()`.

### Properties

| Property | Description |
|----------|-------------|
| `first` | First element |
| `last` | Last element |
| `length` | Count |

### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `extract()` | `TextHandlers` | All serialized strings |
| `extract_first()` | `TextHandler` | First serialized |
| `css(selector)` | `Selectors` | Apply CSS to all |
| `xpath(selector)` | `Selectors` | Apply XPath to all |
| `re(regex)` | `TextHandlers` | Regex across all |
| `re_first(regex)` | `TextHandler` | First regex match |
| `search(value)` | `Selectors` | Filter by value |
| `filter(func)` | `Selectors` | Filter by predicate |
| `get()` | `TextHandler` | First element serialized |
| `getall()` | `TextHandlers` | All serialized |

---

## Custom Types

### TextHandler

Extends `str` with scraping-oriented methods.

| Method | Returns | Description |
|--------|---------|-------------|
| `clean()` | `TextHandler` | Remove whitespace and consecutive spaces |
| `json()` | `dict` | Parse as JSON |
| `get(default=None)` | `TextHandler` | Return self or default |
| `get_all()` | `TextHandler` | Alias of self |
| `extract()` | `TextHandler` | Alias of `get_all()` |
| `extract_first()` | `TextHandler` | Alias of `get()` |
| `re(regex, ...)` | matches | Apply regex, return matches |
| `re_first(regex, default=None, ...)` | `TextHandler` | First regex match |

Plus all standard `str` methods (`strip`, `upper`, `lower`, `replace`, `split`, etc.) -- each returns `TextHandler`.

### TextHandlers

Extends `list[TextHandler]`.

| Method | Returns | Description |
|--------|---------|-------------|
| `get(default=None)` | `TextHandler` | First item |
| `get_all()` | `TextHandlers` | Self |
| `extract()` | `TextHandlers` | Self |
| `extract_first(default=None)` | `TextHandler` | First item |
| `re(regex, ...)` | `TextHandlers` | Regex across all, flatten |
| `re_first(regex, default=None, ...)` | `TextHandler` | First match across all |

### AttributesHandler

Read-only mapping (`Mapping[str, TextHandler]`).

| Method | Description |
|--------|-------------|
| `get(key, default=None)` | Standard dict `.get()` |
| `search_values(keyword, partial=False)` | Find attributes by value |
| `json_string` (property) | Attributes as JSON bytes |

---

## Spider

Async web spider with concurrency, sessions, pause/resume, and streaming.

```python
from scrapling.spiders import Spider, Response, Request
```

### Minimal Example

```python
class QuotesSpider(Spider):
    name = "quotes"
    start_urls = ["https://quotes.toscrape.com"]

    async def parse(self, response: Response):
        for quote in response.css("div.quote"):
            yield {
                "text": quote.css("span.text::text").get(""),
                "author": quote.css("small.author::text").get(""),
            }

result = QuotesSpider().start()
```

### Constructor

```python
Spider(crawldir=None, interval=300.0)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `crawldir` | `str \| None` | `None` | Directory for checkpoint files (enables pause/resume) |
| `interval` | `float` | `300.0` | Seconds between periodic checkpoint saves |

### Class Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | `None` | **Required.** Spider identifier |
| `start_urls` | `list[str]` | `[]` | Initial URLs to crawl |
| `allowed_domains` | `set[str]` | `set()` | Domain whitelist (subdomains auto-match) |
| `concurrent_requests` | `int` | `4` | Max simultaneous requests |
| `concurrent_requests_per_domain` | `int` | `0` | Per-domain limit (`0` = unlimited) |
| `download_delay` | `float` | `0.0` | Seconds between requests |
| `max_blocked_retries` | `int` | `3` | Retries for blocked responses |
| `fp_include_kwargs` | `bool` | `False` | Include kwargs in dedup fingerprint |
| `fp_keep_fragments` | `bool` | `False` | Keep URL `#fragment` in fingerprint |
| `fp_include_headers` | `bool` | `False` | Include headers in fingerprint |
| `logging_level` | `int` | `logging.DEBUG` | Log level |
| `logging_format` | `str` | `"[%(asctime)s]:({spider_name}) %(levelname)s: %(message)s"` | Log format |
| `logging_date_format` | `str` | `"%Y-%m-%d %H:%M:%S"` | Timestamp format |
| `log_file` | `str \| None` | `None` | Log file path |

### Core Methods

| Method | Description |
|--------|-------------|
| `start(use_uvloop=False, **backend_options)` | Run spider synchronously. Returns `CrawlResult`. |
| `async stream()` | Async generator yielding items in real time. Access `spider.stats` during iteration. |
| `pause()` | Request graceful shutdown (for use with `stream()`). |

### Lifecycle Hooks (override in subclass)

| Hook | Signature | Description |
|------|-----------|-------------|
| `parse` | `async def parse(self, response) -> AsyncGenerator` | **Required.** Default callback. Must yield dicts or Requests. |
| `start_requests` | `async def start_requests() -> AsyncGenerator` | Override to customize initial requests. |
| `on_start` | `async def on_start(self, resuming=False)` | Called before crawling. `resuming=True` on checkpoint restore. |
| `on_close` | `async def on_close(self)` | Called after crawling completes. |
| `on_error` | `async def on_error(self, request, error)` | Handle request errors. |
| `on_scraped_item` | `async def on_scraped_item(self, item) -> dict \| None` | Process/filter items. Return `None` to drop. |
| `is_blocked` | `async def is_blocked(self, response) -> bool` | Custom block detection. Default checks status codes `401, 403, 407, 429, 444, 500, 502, 503, 504`. |
| `retry_blocked_request` | `async def retry_blocked_request(self, request, response) -> Request` | Modify request before retry. |
| `configure_sessions` | `def configure_sessions(self, manager: SessionManager)` | Register sessions. Default creates `FetcherSession`. |

### Pagination Example

```python
async def parse(self, response: Response):
    for quote in response.css("div.quote"):
        yield {"text": quote.css("span.text::text").get("")}

    next_page = response.css("li.next a::attr(href)").get()
    if next_page:
        yield response.follow(next_page, callback=self.parse)
```

---

## Spider Request Object

```python
from scrapling.spiders import Request
```

### Constructor

```python
Request(url, sid="", callback=None, priority=0, dont_filter=False, meta=None, **kwargs)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | required | Target URL |
| `sid` | `str` | `""` | Session ID for routing |
| `callback` | `callable` | `None` | Async generator processing response |
| `priority` | `int` | `0` | Higher = processed sooner |
| `dont_filter` | `bool` | `False` | Skip deduplication |
| `meta` | `dict` | `{}` | Metadata passed to response |
| `**kwargs` | | | Extra args for session's fetch (e.g. `method`, `data`, `wait_selector`) |

### Methods

| Method | Description |
|--------|-------------|
| `copy()` | Independent copy |
| `update_fingerprint(include_kwargs, include_headers, keep_fragments)` | Generate SHA1 dedup fingerprint |

### Deduplication

Fingerprint computed from: URL + HTTP method + request body + session ID. Duplicates silently dropped unless `dont_filter=True`.

---

## Spider Response.follow()

Preferred way to create follow-up requests from callbacks.

```python
response.follow(url, sid="", callback=None, priority=None, dont_filter=False,
                meta=None, referer_flow=True, **kwargs)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | required | Absolute or relative URL |
| `sid` | `str` | `""` | Session ID (inherits if empty) |
| `callback` | `callable` | `None` | Callback (inherits if `None`) |
| `priority` | `int \| None` | `None` | Priority (inherits if `None`) |
| `dont_filter` | `bool` | `False` | Skip dedup |
| `meta` | `dict \| None` | `None` | Merged with existing meta (new wins) |
| `referer_flow` | `bool` | `True` | Set current URL as Referer |
| `**kwargs` | | | Merged with original request kwargs |

Automatic advantages: resolves relative URLs, sets Referer, inherits session and kwargs.

---

## Spider Sessions (SessionManager)

Override `configure_sessions(self, manager)` to register sessions.

### manager.add()

```python
manager.add(session_id, session, *, default=False, lazy=False)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `session_id` | `str` | required | Reference name |
| `session` | session instance | required | `FetcherSession`, `AsyncDynamicSession`, or `AsyncStealthySession` |
| `default` | `bool` | `False` | Make this the default session |
| `lazy` | `bool` | `False` | Defer startup until first use |

### Session Types for Spiders

| Session Type | Use Case |
|---|---|
| `FetcherSession` | Fast HTTP, no JS |
| `AsyncDynamicSession` | Browser automation, JS rendering |
| `AsyncStealthySession` | Anti-bot bypass, Cloudflare |

### Example: Multiple Sessions with Blocked Retry Escalation

```python
from scrapling.spiders import Spider, SessionManager, Request, Response
from scrapling.fetchers import FetcherSession, AsyncStealthySession, ProxyRotator

class MySpider(Spider):
    name = "my_spider"
    start_urls = ["https://example.com"]
    max_blocked_retries = 5

    def configure_sessions(self, manager: SessionManager):
        manager.add("requests", FetcherSession(
            impersonate=["chrome", "firefox", "safari"],
            proxy_rotator=ProxyRotator(["http://p1:8080", "http://p2:8080"]),
        ))
        manager.add("stealth", AsyncStealthySession(
            block_webrtc=True,
            proxy_rotator=ProxyRotator([
                {"server": "http://residential1:8080", "username": "u", "password": "p"},
            ]),
        ), lazy=True)

    async def retry_blocked_request(self, request, response):
        request.sid = "stealth"
        return request

    async def parse(self, response):
        yield {"title": response.css("title::text").get("")}
```

### SessionManager Methods

| Method | Description |
|--------|-------------|
| `add(session_id, session, *, default, lazy)` | Register session |
| `remove(session_id)` / `pop(session_id)` | Remove session |
| `get(session_id)` | Retrieve session |
| `async start()` | Start non-lazy sessions |
| `async close()` | Close all sessions |
| `async fetch(request)` | Fetch via appropriate session |
| `default_session_id` (property) | Current default |
| `session_ids` (property) | All registered IDs |

---

## Spider CrawlResult / CrawlStats / ItemList

### CrawlResult

```python
@dataclass
class CrawlResult:
    stats: CrawlStats
    items: ItemList
    paused: bool = False
    completed: bool  # property: True if not paused
```

Supports `len()` and iteration over items.

### CrawlStats

| Attribute | Type | Description |
|-----------|------|-------------|
| `requests_count` | `int` | Total requests processed |
| `failed_requests_count` | `int` | Failed requests |
| `offsite_requests_count` | `int` | Filtered out-of-domain requests |
| `blocked_requests_count` | `int` | Blocked detection hits |
| `items_scraped` | `int` | Extracted items |
| `items_dropped` | `int` | Dropped items |
| `response_bytes` | `int` | Total response data |
| `domains_response_bytes` | `dict` | Per-domain byte counts |
| `response_status_count` | `dict` | HTTP status distribution (e.g. `{"status_200": 150}`) |
| `sessions_requests_count` | `dict` | Per-session request counts |
| `proxies` | `list` | Proxies used |
| `log_levels_counter` | `dict` | Log level distribution |
| `custom_stats` | `dict` | User-defined metrics |
| `start_time` | `float` | Epoch start |
| `end_time` | `float` | Epoch end |
| `elapsed_seconds` | `float` | Duration (property) |
| `requests_per_second` | `float` | Throughput (property) |
| `concurrent_requests` | `int` | Config value |
| `concurrent_requests_per_domain` | `int` | Config value |
| `download_delay` | `float` | Config value |

Methods: `increment_status()`, `increment_response_bytes()`, `increment_requests_count()`, `to_dict()`.

### ItemList

Extends `list` with export methods:

| Method | Description |
|--------|-------------|
| `to_json(path, *, indent=False)` | Export as JSON (`indent=True` for 2-space pretty) |
| `to_jsonl(path)` | Export as JSON Lines |

Parent directories created automatically.

---

## Spider Advanced Features

### Pause / Resume

```python
spider = MySpider(crawldir="crawl_data/my_spider")
result = spider.start()
# Ctrl+C -> graceful shutdown + checkpoint save
# Ctrl+C x2 -> force stop
# Re-run same code -> resumes from checkpoint

if result.paused:
    print("Paused, run again to resume")
```

### Streaming

```python
import anyio

async def main():
    spider = MySpider()
    async for item in spider.stream():
        print(item)
        print(f"Stats: {spider.stats.items_scraped} items")

anyio.run(main)
```

### uvloop

```python
result = MySpider().start(use_uvloop=True)
```

Requires `uvloop` (Linux/macOS) or `winloop` (Windows).

---

## MCP Server

Scrapling ships an MCP server with 6 scraping tools + 1 serve method.

### Starting the Server

```bash
# stdio transport (for Claude Desktop / Claude Code)
scrapling mcp

# HTTP transport
scrapling mcp --http --host 127.0.0.1 --port 8000
```

Programmatically:

```python
from scrapling.core.ai import ScraplingMCPServer
server = ScraplingMCPServer()
server.serve(http=False, host="0.0.0.0", port=8000)
```

### Claude Desktop Config

```json
{
  "mcpServers": {
    "ScraplingServer": {
      "command": "/path/to/scrapling",
      "args": ["mcp"]
    }
  }
}
```

### Claude Code Config

```bash
claude mcp add ScraplingServer "/path/to/scrapling" mcp
```

### ResponseModel

All tools return:

```python
@dataclass
class ResponseModel:
    status: int     # HTTP status code
    content: str    # Page content (markdown/HTML/text)
    url: str        # Original URL
```

### Tool 1: `get`

Fast HTTP GET with browser fingerprint impersonation. Low-mid protection.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | required | Target URL |
| `impersonate` | `ImpersonateType` | `"chrome"` | Browser fingerprint |
| `extraction_type` | `str` | `"markdown"` | `"markdown"`, `"HTML"`, or `"text"` |
| `css_selector` | `str \| None` | `None` | CSS selector for extraction |
| `main_content_only` | `bool` | `True` | Extract `<body>` only |
| `params` | `dict \| None` | `None` | Query string parameters |
| `headers` | `Mapping \| None` | `None` | Request headers |
| `cookies` | `dict[str, str] \| None` | `None` | Cookies |
| `timeout` | `int \| float \| None` | `30` | Timeout in seconds |
| `follow_redirects` | `bool` | `True` | Follow redirects |
| `max_redirects` | `int` | `30` | Max redirects (`-1` = unlimited) |
| `retries` | `int \| None` | `3` | Retry attempts |
| `retry_delay` | `int \| None` | `1` | Seconds between retries |
| `proxy` | `str \| None` | `None` | Proxy URL |
| `proxy_auth` | `dict[str, str] \| None` | `None` | `{"username", "password"}` |
| `auth` | `dict[str, str] \| None` | `None` | HTTP basic auth |
| `verify` | `bool \| None` | `True` | Verify HTTPS |
| `http3` | `bool \| None` | `False` | Use HTTP/3 |
| `stealthy_headers` | `bool \| None` | `True` | Realistic browser headers |

### Tool 2: `bulk_get`

Same as `get` but with `urls: list[str]` instead of `url`. Returns `list[ResponseModel]`.

### Tool 3: `fetch`

Browser-based fetch via Playwright. Low-mid protection.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | required | Target URL |
| `extraction_type` | `str` | `"markdown"` | Content format |
| `css_selector` | `str \| None` | `None` | CSS selector |
| `main_content_only` | `bool` | `True` | Body only |
| `headless` | `bool` | `True` | Headless browser |
| `google_search` | `bool` | `True` | Google referer |
| `real_chrome` | `bool` | `False` | Use installed Chrome |
| `wait` | `int \| float` | `0` | Wait after load (ms) |
| `proxy` | `str \| dict \| None` | `None` | Proxy |
| `timezone_id` | `str \| None` | `None` | Timezone |
| `locale` | `str \| None` | `None` | Locale |
| `extra_headers` | `dict \| None` | `None` | Headers |
| `useragent` | `str \| None` | `None` | User agent |
| `cdp_url` | `str \| None` | `None` | CDP URL |
| `timeout` | `int \| float` | `30000` | Timeout (ms) |
| `disable_resources` | `bool` | `False` | Block resources |
| `wait_selector` | `str \| None` | `None` | Wait for selector |
| `cookies` | `Sequence \| None` | `None` | Browser cookies |
| `network_idle` | `bool` | `False` | Wait for network idle |
| `wait_selector_state` | `str` | `"attached"` | Selector state |

### Tool 4: `bulk_fetch`

Same as `fetch` but with `urls: list[str]`. Returns `list[ResponseModel]`.

### Tool 5: `stealthy_fetch`

All `fetch` parameters plus:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `hide_canvas` | `bool` | `False` | Canvas noise |
| `block_webrtc` | `bool` | `False` | Block WebRTC |
| `allow_webgl` | `bool` | `True` | Allow WebGL |
| `solve_cloudflare` | `bool` | `False` | Solve Cloudflare challenges |
| `additional_args` | `dict \| None` | `None` | Extra Playwright context args |

### Tool 6: `bulk_stealthy_fetch`

Same as `stealthy_fetch` but with `urls: list[str]`. Returns `list[ResponseModel]`.

---

## CLI

### Global Commands

```bash
scrapling install          # Install browser dependencies
scrapling shell            # Launch interactive shell
scrapling mcp              # Start MCP server (stdio)
scrapling mcp --http       # Start MCP server (HTTP)
scrapling extract ...      # Terminal scraping
scrapling --help           # Help
```

### Interactive Shell

```bash
scrapling shell
scrapling shell -c "get('https://example.com'); print(page.css('title::text').get())"
scrapling shell --loglevel info
```

Requires `pip install "scrapling[shell]"`.

#### Built-in Shortcuts

| Function | Description |
|----------|-------------|
| `get(url, **kwargs)` | HTTP GET |
| `post(url, **kwargs)` | HTTP POST |
| `put(url, **kwargs)` | HTTP PUT |
| `delete(url, **kwargs)` | HTTP DELETE |
| `fetch(url, **kwargs)` | Browser fetch |
| `stealthy_fetch(url, **kwargs)` | Stealth fetch |
| `view(page)` | Open HTML in browser |
| `uncurl(curl_cmd)` | Convert curl to Request object |
| `curl2fetcher(curl_cmd)` | Execute curl command via fetcher |

#### Auto-Variables

| Variable | Description |
|----------|-------------|
| `page` | Last fetched page |
| `response` | Alias for `page` |
| `pages` | Last 5 fetched pages (`Selectors` object) |

### Extract Commands

```
scrapling extract <command> <url> <output_file> [OPTIONS]
```

Output format determined by extension: `.html` (raw HTML), `.md` (markdown), `.txt` (plain text).

#### `scrapling extract get`

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `-H, --headers` | `TEXT` | -- | `"Key: Value"` (repeatable) |
| `--cookies` | `TEXT` | -- | `"name1=val1;name2=val2"` |
| `--timeout` | `INTEGER` | `30` | Seconds |
| `--proxy` | `TEXT` | -- | `"http://user:pass@host:port"` |
| `-s, --css-selector` | `TEXT` | -- | CSS selector |
| `-p, --params` | `TEXT` | -- | `"key=value"` (repeatable) |
| `--follow-redirects` | `BOOLEAN` | `True` | Follow redirects |
| `--verify` | `BOOLEAN` | `True` | Verify SSL |
| `--impersonate` | `TEXT` | -- | Browser fingerprint |
| `--stealthy-headers` | `BOOLEAN` | `True` | Realistic headers |

#### `scrapling extract post` / `scrapling extract put`

All `get` flags plus:

| Flag | Type | Description |
|------|------|-------------|
| `-d, --data` | `TEXT` | Form data: `"key1=val1&key2=val2"` |
| `-j, --json` | `TEXT` | JSON string |

#### `scrapling extract delete`

Same flags as `get`.

#### `scrapling extract fetch`

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--headless` | `BOOLEAN` | `True` | Headless mode |
| `--disable-resources` | `BOOLEAN` | `False` | Block resources |
| `--network-idle` | `BOOLEAN` | `False` | Wait for idle |
| `--timeout` | `INTEGER` | `30000` | Milliseconds |
| `--wait` | `INTEGER` | `0` | Extra wait (ms) |
| `-s, --css-selector` | `TEXT` | -- | CSS selector |
| `--wait-selector` | `TEXT` | -- | Wait for selector |
| `--locale` | `TEXT` | system | Locale |
| `--real-chrome` | `BOOLEAN` | `False` | Use Chrome |
| `--proxy` | `TEXT` | -- | Proxy URL |
| `-H, --extra-headers` | `TEXT` | -- | `"Key: Value"` (repeatable) |

#### `scrapling extract stealthy-fetch`

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--headless` | `BOOLEAN` | `True` | Headless mode |
| `--disable-resources` | `BOOLEAN` | `False` | Block resources |
| `--block-webrtc` | `BOOLEAN` | `False` | Block WebRTC |
| `--solve-cloudflare` | `BOOLEAN` | `False` | Solve Cloudflare |
| `--allow-webgl` | `BOOLEAN` | `True` | Allow WebGL |
| `--network-idle` | `BOOLEAN` | `False` | Wait for idle |
| `--real-chrome` | `BOOLEAN` | `False` | Use Chrome |
| `--timeout` | `INTEGER` | `30000` | Milliseconds |
| `--wait` | `INTEGER` | `0` | Extra wait (ms) |
| `-s, --css-selector` | `TEXT` | -- | CSS selector |
| `--wait-selector` | `TEXT` | -- | Wait for selector |
| `--hide-canvas` | `BOOLEAN` | `False` | Canvas noise |
| `--proxy` | `TEXT` | -- | Proxy URL |
| `-H, --extra-headers` | `TEXT` | -- | `"Key: Value"` (repeatable) |

#### Docker Usage

```bash
docker run -v $(pwd)/output:/output scrapling extract get "https://example.com" /output/article.md
```
