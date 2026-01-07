# Cloudflare Configuration Guide

This guide documents the Cloudflare configuration for OpenCitiVibes, optimized for the free tier.

## Overview

OpenCitiVibes uses Cloudflare as a CDN and security layer. The configuration prioritizes:
- **Performance**: Edge caching for fast page loads (improved LCP)
- **Security**: TLS 1.2+, browser integrity checks, hotlink protection
- **Reliability**: Always Online, stale-while-revalidate

## CLI Tool

A custom CLI tool is available for auditing Cloudflare settings:

```bash
# Location
~/.claude/tools/cloudflare-cli/cf.py

# Or via symlink
~/.local/bin/cf

# Usage
CF_API_TOKEN="your-token" cf all          # Full audit
CF_API_TOKEN="your-token" cf ssl          # SSL settings only
CF_API_TOKEN="your-token" cf cache        # Cache settings only
```

### Getting an API Token

1. Go to https://dash.cloudflare.com/profile/api-tokens
2. Click **Create Token**
3. Select **Read all resources** template
4. Save the token securely

### Available Commands

| Command | Description |
|---------|-------------|
| `cf verify` | Verify API token is valid |
| `cf zones` | List all zones |
| `cf dns` | List DNS records |
| `cf ssl` | Show SSL/TLS settings |
| `cf security` | Show security settings |
| `cf cache` | Show caching settings |
| `cf speed` | Show speed optimizations |
| `cf network` | Show network settings |
| `cf firewall` | List firewall rules |
| `cf page-rules` | List page rules |
| `cf all` | Full audit (all above) |

Add `--json` for JSON output.

## Recommended Settings

### SSL/TLS

| Setting | Value | Why |
|---------|-------|-----|
| SSL Mode | **Full (Strict)** | Validates origin certificate |
| Minimum TLS Version | **1.2** | TLS 1.0/1.1 are deprecated and vulnerable |
| TLS 1.3 | **On** | Modern, faster handshakes |
| Always Use HTTPS | **On** | Redirects HTTP to HTTPS |
| Automatic HTTPS Rewrites | **On** | Fixes mixed content |

### Security

| Setting | Value | Why |
|---------|-------|-----|
| Security Level | **Medium** | Balances protection vs false positives |
| Browser Integrity Check | **On** | Blocks malicious bots |
| Email Obfuscation | **On** | Protects email addresses from scrapers |
| Hotlink Protection | **On** | Prevents bandwidth theft |

### Caching

| Setting | Value | Why |
|---------|-------|-----|
| Cache Level | **Aggressive** | Caches more content types |
| Browser Cache TTL | **4 hours** | Reduces origin requests |
| Always Online | **On** | Serves cached pages if origin is down |

### Speed

| Setting | Value | Why |
|---------|-------|-----|
| Brotli | **On** | Better compression than gzip |
| Early Hints | **On** | Preloads resources |
| HTTP/2 | **On** | Multiplexed connections |
| HTTP/3 (QUIC) | **On** | Faster on unreliable networks |

### Network

| Setting | Value | Why |
|---------|-------|-----|
| IPv6 | **On** | Modern connectivity |
| WebSockets | **On** | Required for real-time features |
| 0-RTT | **On** | Faster repeat connections |

## Cache Rules

### Homepage Caching

The homepage HTML is cached at Cloudflare's edge to improve LCP (Largest Contentful Paint).

**Cache Rule Configuration:**

| Field | Value |
|-------|-------|
| Rule name | Cache the homepage HTML |
| Expression | `(http.request.uri.path eq "/")` |
| Cache eligibility | Eligible for cache |
| Edge TTL | Ignore origin, use **2 hours** |

**Important:** Use `http.request.uri.path` (not `uri.full`) for path matching.

### Next.js Configuration

The frontend sends proper cache headers to enable Cloudflare caching:

**`frontend/src/app/page.tsx`:**
```typescript
// Force static generation - data is fetched client-side
export const dynamic = 'force-static';

// Revalidate every hour for SEO metadata updates
export const revalidate = 3600;
```

**`frontend/next.config.js`:**
```javascript
// Cache control for public pages
const pagesCacheHeaders = [
  {
    key: 'Cache-Control',
    value: 'public, s-maxage=3600, stale-while-revalidate=86400',
  },
];

// Applied to homepage, idea pages, category pages
```

### Verifying Cache is Working

```bash
# Check cache status
curl -s -I https://yourdomain.com/ | grep -i cf-cache-status

# Expected results:
# First request:  cf-cache-status: MISS (fetched from origin)
# Second request: cf-cache-status: HIT (served from edge)
```

| Status | Meaning |
|--------|---------|
| `HIT` | Served from Cloudflare edge cache |
| `MISS` | Fetched from origin, now cached |
| `DYNAMIC` | Not cacheable (check headers) |
| `BYPASS` | Cache bypassed (check rules) |

## DNS Configuration

### Proxied vs DNS-Only

| Record | Proxied | Reason |
|--------|---------|--------|
| Main domain (A/AAAA) | Yes (orange cloud) | CDN + security |
| www subdomain | Yes | CDN + security |
| SSH subdomain | **No** (grey cloud) | SSH needs direct IP |
| ntfy subdomain | **No** | Push notifications need direct |

**Example DNS:**
```
A     example.com       → 51.x.x.x    (Proxied)
A     www               → 51.x.x.x    (Proxied)
A     ssh               → 51.x.x.x    (DNS only)
A     ntfy              → 51.x.x.x    (DNS only)
```

### SSH Access with Cloudflare

Cloudflare doesn't proxy port 22. For SSH access:

1. Create `ssh.yourdomain.com` with **DNS only** (grey cloud)
2. Use this hostname for SSH: `ssh user@ssh.yourdomain.com`
3. Set this in GitHub secrets for deployments

## Web Analytics & Law 25 Compliance

Cloudflare Web Analytics is enabled and whitelisted in our Content Security Policy.

### Privacy Features

| Feature | Status |
|---------|--------|
| Cookies | ❌ None |
| localStorage | ❌ None |
| IP fingerprinting | ❌ None |
| Browser fingerprinting | ❌ None |
| Data sold to advertisers | ❌ No |

### Law 25 / GDPR Compatibility

Cloudflare Web Analytics is **privacy-friendly** and compatible with Quebec's Law 25:

- **No cookies or tracking**: Does not use any client-side state (cookies, localStorage)
- **No fingerprinting**: Does not fingerprint users via IP, User Agent, or other data
- **No consent banner required**: Since no cookies are set, no cookie consent is needed

**Note:** Cloudflare is a US company, and IP addresses pass through their servers (even if not stored). Under strict Law 25/GDPR interpretation, this could be considered cross-border data transfer. However, Cloudflare is certified under the EU-U.S. Data Privacy Framework.

### CSP Configuration

The analytics beacon is whitelisted in `frontend/next.config.js`:

```javascript
"script-src 'self' 'unsafe-eval' 'unsafe-inline' https://static.cloudflareinsights.com"
```

## Performance Monitoring

### Cloudflare RUM (Real User Monitoring)

Access via Dashboard → Analytics → Web Analytics

Key metrics to monitor:
- **LCP (Largest Contentful Paint)** - Should be < 2.5s
- **FID (First Input Delay)** - Should be < 100ms
- **CLS (Cumulative Layout Shift)** - Should be < 0.1

### Improving LCP

If LCP is poor, common causes:

| Cause | Solution |
|-------|----------|
| Slow TTFB | Enable edge caching (cache rules) |
| Large images | Use `next/image` with WebP/AVIF |
| Render-blocking JS | Defer non-critical scripts |
| Web fonts | Use `font-display: swap` |

### Testing TTFB

```bash
# Check Time To First Byte
curl -s -o /dev/null -w "TTFB: %{time_starttransfer}s\n" https://yourdomain.com/

# Good: < 200ms (cached)
# Acceptable: < 600ms (origin)
# Poor: > 1s
```

## Troubleshooting

### Page Not Caching

1. Check origin headers:
   ```bash
   curl -I https://yourdomain.com/ | grep -i cache-control
   ```

2. If you see `no-cache, no-store`:
   - Add `export const dynamic = 'force-static'` to the page
   - Or configure cache rule to ignore origin headers

3. Verify cache rule expression uses `uri.path` not `uri.full`

### Mixed Content Warnings

Enable **Automatic HTTPS Rewrites** in SSL/TLS settings.

### Images Not Loading

If using hotlink protection, ensure your own domain is allowed.

### WebSocket Connection Failed

Ensure **WebSockets** is enabled in Network settings.

## Security Checklist

- [ ] SSL Mode: Full (Strict)
- [ ] Minimum TLS: 1.2
- [ ] Always Use HTTPS: On
- [ ] Browser Integrity Check: On
- [ ] Email Obfuscation: On
- [ ] Hotlink Protection: On
- [ ] No sensitive subdomains exposed (SSH uses DNS-only)

## Related Documentation

- [Deployment Guide](DEPLOYMENT.md) - CI/CD pipeline
- [Hardening Guide](HARDENING.md) - Server security
- [Configuration Reference](../CONFIGURATION.md) - App configuration
