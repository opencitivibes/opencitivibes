# OpenCitiVibes Configuration Reference

Complete reference for all configuration options.

## Platform Configuration

**File:** `instances/<instance-id>/platform.config.json`

Each instance has its own configuration file. The active instance is selected via the `PLATFORM_CONFIG_PATH` environment variable.

### Core Structure

```json
{
  "platform": { },      // Platform metadata
  "instance": { },      // Instance identity
  "database": { },      // Database settings
  "contact": { },       // Contact information
  "social": { },        // Social media links
  "legal": { },         // Legal/compliance settings
  "branding": { },      // Visual customization
  "features": { },      // Feature flags
  "localization": { }   // Language settings
}
```

### Detailed Field Reference

#### platform

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `name` | string | Platform name | "OpenCitiVibes" |
| `version` | string | Platform version | "1.0.0" |

#### instance

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `id` | string | Unique instance identifier (e.g., `montreal`, `calgary`) | Yes |
| `name` | LocalizedString | Instance display name | Yes |
| `entity.type` | string | `city`\|`region`\|`organization`\|`community` | Yes |
| `entity.name` | LocalizedString | Entity name | Yes |
| `entity.region` | LocalizedString | Region name | No |
| `entity.country` | LocalizedString | Country name | No |
| `location.display` | LocalizedString | Location display text | No |
| `location.coordinates.lat` | number | Latitude for maps | No |
| `location.coordinates.lng` | number | Longitude for maps | No |
| `location.timezone` | string | IANA timezone | No |

#### database

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `file` | string | SQLite database filename | Yes |

Example:
```json
{
  "database": {
    "file": "opencitivibes_montreal.db"
  }
}
```

The database file is stored in `backend/data/`.

#### contact

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `email` | string | Primary contact email | Yes |
| `support_email` | string | Support email | No |
| `address` | LocalizedString | Physical address | No |

#### social

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `twitter` | string | Twitter/X handle | No |
| `facebook` | string | Facebook page URL | No |
| `instagram` | string | Instagram handle | No |
| `linkedin` | string | LinkedIn page URL | No |
| `youtube` | string | YouTube channel name | No |

#### legal

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `jurisdiction` | LocalizedString | Legal jurisdiction | No |
| `courts` | LocalizedString | Court jurisdiction | No |
| `privacy_authority.name` | LocalizedString | Data protection authority | No |
| `privacy_authority.acronym` | string | Authority acronym | No |
| `privacy_authority.url` | string | Authority website | No |
| `data_protection_laws` | array | Applicable laws | No |

#### branding

##### Core Colors

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `primary_color` | string (hex) | Primary brand color | "#9333ea" |
| `secondary_color` | string (hex) | Secondary color | "#6b21a8" |
| `primary_dark` | string (hex) | Dark variant of primary | Auto-generated |
| `accent` | string (hex) | Accent/highlight color | Primary color |
| `success` | string (hex) | Success state color | "#22c55e" |
| `warning` | string (hex) | Warning state color | "#eab308" |
| `error` | string (hex) | Error state color | "#ef4444" |

##### Dark Mode Colors

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `dark_mode.primary` | string (hex) | Primary color in dark mode | Lighter primary |
| `dark_mode.secondary` | string (hex) | Secondary color in dark mode | Lighter secondary |
| `dark_mode.background` | string (hex) | Page background in dark mode | "#0f172a" |
| `dark_mode.surface` | string (hex) | Card/surface background in dark mode | "#1e293b" |

##### Typography

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `fonts.heading` | string | Font family for headings | "Inter" |
| `fonts.body` | string | Font family for body text | "Inter" |
| `font_url` | string (URL) | Google Fonts URL to load custom fonts | None |

Example font configuration:
```json
{
  "fonts": {
    "heading": "Raleway",
    "body": "Inter"
  },
  "font_url": "https://fonts.googleapis.com/css2?family=Raleway:wght@400;600;700;900&family=Inter:wght@400;500;600&display=swap"
}
```

##### Hero Banner

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `hero_image` | string (path) | Hero background image | "/instance/hero.jpg" |
| `hero_overlay` | boolean | Show dark overlay on hero for text readability | true |
| `hero_position` | string (CSS) | Background position (CSS `background-position`) | "center center" |
| `hero_subtitle` | LocalizedString | Custom subtitle text on hero banner | Uses default i18n |

Example hero configuration:
```json
{
  "hero_image": "/instance/hero.jpg",
  "hero_overlay": true,
  "hero_position": "center 42%",
  "hero_subtitle": {
    "en": "Share your ideas to make our city greener",
    "fr": "Partagez vos idées pour une ville plus verte"
  }
}
```

##### Assets

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `logo` | string (path) | Logo image (SVG recommended) | "/instance/logo.svg" |
| `favicon` | string (path) | Favicon | "/instance/favicon.ico" |

##### UI Style

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `border_radius` | string | Border radius style: `sm`, `md`, `lg`, `xl`, `full` | "lg" |

#### features

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `voting_enabled` | boolean | Enable voting | true |
| `comments_enabled` | boolean | Enable comments | true |
| `tags_enabled` | boolean | Enable tagging | true |
| `quality_feedback_enabled` | boolean | Enable quality voting | true |
| `moderation_enabled` | boolean | Enable moderation | true |
| `analytics_public` | boolean | Public analytics | false |

#### localization

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `default_locale` | string | Default language | "en" |
| `supported_locales` | string[] | Available languages | ["en"] |
| `date_format` | LocalizedString | Date format per locale | - |

### LocalizedString Type

A LocalizedString is an object with locale codes as keys:

```json
{
  "en": "English text",
  "fr": "Texte francais",
  "es": "Texto espanol"
}
```

## Environment Variables

**File:** `.env`

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key (32+ chars) | `openssl rand -hex 32` |
| `DATABASE_URL` | Database connection string | `sqlite:///./data/opencitivibes.db` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ADMIN_EMAIL` | Initial admin email | None |
| `ADMIN_PASSWORD` | Initial admin password | None |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration | `30` |
| `PLATFORM_CONFIG_PATH` | Path to platform config | `./config/platform.config.json` |
| `CORS_ORIGINS` | Allowed CORS origins | `*` |

### Docker Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `COMPOSE_PROJECT_NAME` | Docker project name | `idees-montreal` |
| `CONTAINER_PREFIX` | Container name prefix | `idees-mtl` |
| `DOMAIN` | Production domain | `idees-montreal.ca` |

### Frontend Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `http://localhost:8000/api` |
| `NEXT_PUBLIC_SITE_URL` | Frontend URL | `http://localhost:3000` |

### Ntfy Push Notification Variables

Admin push notifications are powered by self-hosted [ntfy](https://ntfy.sh). Admins receive real-time notifications on their mobile devices when content requires moderation.

| Variable | Description | Default |
|----------|-------------|---------|
| `NTFY_URL` | Internal ntfy server URL (Docker network) | None (disabled) |
| `NTFY_TOPIC_PREFIX` | Topic prefix for notifications | `admin` |
| `NTFY_AUTH_TOKEN` | Auth token for publishing (if auth enabled) | None |
| `NTFY_ENABLED` | Enable/disable notifications globally | `true` |
| `APP_URL` | Frontend URL for notification deep links | `http://localhost:3000` |
| `NTFY_BASE_URL` | Public ntfy URL (for mobile app connection) | `https://ntfy.yourdomain.com` |
| `NTFY_CACHE_DURATION` | Notification cache duration | `24h` |

**Topic structure:**

| Topic | Purpose | Priority |
|-------|---------|----------|
| `{prefix}-ideas` | New ideas pending moderation | default |
| `{prefix}-comments` | Comments awaiting approval | low |
| `{prefix}-appeals` | User appeals for rejected ideas | high |
| `{prefix}-officials` | Official account verification requests | high |
| `{prefix}-reports` | Reported content (abuse) | urgent |
| `{prefix}-critical` | High-priority system alerts | max |

See [Ntfy Notification System](../claude-docs/plans/ntfy-notification-system.md) for detailed implementation.

## Legal Configuration

**File:** `backend/config/legal.config.json`

### Structure

```json
{
  "terms": {
    "version": "1.0.0",
    "effective_date": "2024-01-01",
    "sections": []
  },
  "privacy": {
    "version": "1.0.0",
    "effective_date": "2024-01-01",
    "sections": []
  }
}
```

### Section Structure

Each section in `terms.sections` or `privacy.sections`:

```json
{
  "id": "acceptance",
  "title": {
    "en": "Acceptance of Terms",
    "fr": "Acceptation des conditions"
  },
  "content": {
    "en": "By using this platform...",
    "fr": "En utilisant cette plateforme..."
  },
  "subsections": []
}
```

## Configuration Validation

### JSON Validation

```bash
# Validate platform config
python -m json.tool backend/config/platform.config.json

# Validate legal config
python -m json.tool backend/config/legal.config.json
```

### Schema Validation

The backend validates configuration on startup. Check logs for validation errors:

```bash
docker compose logs backend | grep -i config
```

## Example Configurations

### Minimal Configuration

```json
{
  "platform": {
    "name": "OpenCitiVibes",
    "version": "1.0.0"
  },
  "instance": {
    "id": "mycity",
    "name": {
      "en": "Ideas for My City"
    },
    "entity": {
      "type": "city",
      "name": {
        "en": "My City"
      }
    }
  },
  "database": {
    "file": "opencitivibes_mycity.db"
  },
  "contact": {
    "email": "contact@mycity.gov"
  },
  "branding": {
    "primary_color": "#0066CC",
    "hero_image": "/instance/hero.jpg",
    "logo": "/instance/logo.svg"
  },
  "localization": {
    "default_locale": "en",
    "supported_locales": ["en"]
  }
}
```

### Full Configuration (with all branding options)

```json
{
  "platform": {
    "name": "OpenCitiVibes",
    "version": "1.0.0"
  },
  "instance": {
    "id": "example",
    "name": {
      "en": "Ideas for Example City",
      "fr": "Idées pour Ville Exemple"
    },
    "entity": {
      "type": "city",
      "name": { "en": "Example City", "fr": "Ville Exemple" },
      "region": { "en": "State", "fr": "Province" },
      "country": { "en": "Country", "fr": "Pays" }
    },
    "location": {
      "display": { "en": "Example City, State", "fr": "Ville Exemple, Province" },
      "coordinates": { "lat": 45.5, "lng": -73.5 },
      "timezone": "America/New_York"
    }
  },
  "database": {
    "file": "opencitivibes_example.db"
  },
  "contact": {
    "email": "contact@example.com",
    "support_email": "support@example.com"
  },
  "social": {
    "twitter": "@ExampleCity",
    "facebook": "https://facebook.com/examplecity",
    "instagram": "@examplecity"
  },
  "branding": {
    "primary_color": "#2d923d",
    "secondary_color": "#2f5e30",
    "primary_dark": "#1e6b2a",
    "accent": "#990000",
    "success": "#2d923d",
    "warning": "#F9A825",
    "error": "#990000",
    "dark_mode": {
      "primary": "#4aba5a",
      "secondary": "#3d8f4d",
      "background": "#0f1a0f",
      "surface": "#1a2e1a"
    },
    "fonts": {
      "heading": "Raleway",
      "body": "Inter"
    },
    "font_url": "https://fonts.googleapis.com/css2?family=Raleway:wght@400;600;700&family=Inter:wght@400;500;600&display=swap",
    "border_radius": "lg",
    "hero_image": "/instance/hero.jpg",
    "hero_overlay": true,
    "hero_position": "center 40%",
    "hero_subtitle": {
      "en": "Share your ideas to improve our city",
      "fr": "Partagez vos idées pour améliorer notre ville"
    },
    "logo": "/instance/logo.svg",
    "favicon": "/instance/favicon.ico"
  },
  "features": {
    "voting_enabled": true,
    "comments_enabled": true,
    "tags_enabled": true,
    "quality_feedback_enabled": true,
    "moderation_enabled": true,
    "analytics_public": false
  },
  "localization": {
    "default_locale": "en",
    "supported_locales": ["en", "fr"],
    "date_format": {
      "en": "MM/DD/YYYY",
      "fr": "DD/MM/YYYY"
    }
  }
}
```

See `instances/*/platform.config.json` for live examples.

## Configuration Loading Order

1. Environment variables (`.env`)
2. Platform configuration (`platform.config.json`)
3. Legal configuration (`legal.config.json`)
4. Runtime overrides (if any)

Environment variables take precedence for sensitive values like `SECRET_KEY` and `DATABASE_URL`.

## Hot Reloading

Configuration changes require service restart:

```bash
# Restart backend only
docker compose restart backend

# Restart all services
docker compose restart
```

Frontend configuration is fetched from the `/api/config` endpoint and cached. Clear browser cache or hard refresh to see changes.
