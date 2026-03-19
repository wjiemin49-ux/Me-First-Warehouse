# Platform Mapping Reference

## Supported Platforms

| Platform | Domains | Primary Skill | Fallback |
|----------|---------|---------------|----------|
| X/Twitter | `x.com`, `twitter.com`, `mobile.twitter.com` | `x-tweet-fetcher` | — |
| WeChat | `mp.weixin.qq.com` | `web-content-fetcher` | `defuddle` |
| Jike | `okjike.com`, `jike.cn`, `m.okjike.com` | `defuddle` | `baoyu-url-to-markdown` |
| Reddit | `reddit.com`, `old.reddit.com` | `defuddle` | `baoyu-url-to-markdown` |
| Hacker News | `news.ycombinator.com` | `defuddle` | — |
| Zhihu | `zhihu.com`, `zhuanlan.zhihu.com` | `defuddle` | `baoyu-url-to-markdown` |
| Bilibili | `bilibili.com`, `b23.tv` | `defuddle` | `baoyu-url-to-markdown` |
| Generic | * | `defuddle` | `baoyu-url-to-markdown` |

## Platform-Specific Selectors

### WeChat (mp.weixin.qq.com)

```css
#activity-name    /* Title */
#js_name          /* Author/Account */
#js_content       /* Main content */
#publish_time     /* Publish time */
```

**Scrapling command**:
```bash
python3 ~/.openclaw/workspace/skills/web-content-fetcher/scripts/fetch.py "<url>" 50000
```

### Jike (okjike.com)

```css
meta[property="og:title"]     /* Author */
meta[property="og:description"] /* Content */
time                          /* Timestamp */
```

### Reddit (reddit.com)

- JSON API: Append `.json` to URL for structured data
- Example: `https://reddit.com/r/xyz/comments/abc.json`

### Hacker News

- Firebase API: `https://hacker-news.firebaseio.com/v0/item/{id}.json`

## Domain Aliases

The deduplication system normalizes these domain variants:

| Alias | Normalized To |
|-------|---------------|
| `twitter.com`, `www.twitter.com`, `mobile.twitter.com`, `www.x.com` | `x.com` |
| `m.okjike.com`, `web.okjike.com`, `www.okjike.com` | `okjike.com` |
| `old.reddit.com`, `www.reddit.com`, `np.reddit.com`, `i.reddit.com` | `reddit.com` |
| `www.weixin.qq.com` | `mp.weixin.qq.com` |

## Short URL Domains

These are auto-expanded for deduplication:

- `t.co` (Twitter)
- `bit.ly`
- `tinyurl.com`
- `goo.gl`
- `ow.ly`
- `is.gd`
- `buff.ly`
