# OpenCitiVibes Documentation Website

A static website showcasing OpenCitiVibes - the open source citizen engagement platform.

## Structure

```
docs/html/
├── index.html          # Landing page
├── installation.html   # Installation guide
├── css/
│   └── styles.css      # All styles
├── js/
│   └── main.js         # Interactive features
├── images/             # Screenshots and assets
│   ├── screenshots/    # App screenshots
│   ├── hero/           # Hero images
│   └── logo.svg        # Logo
└── README.md           # This file
```

## Development

This is a static site with no build step required. Just open `index.html` in a browser.

### Local Development

```bash
# Using Python
cd docs/html
python -m http.server 8080
# Visit http://localhost:8080

# Using Node.js
npx serve docs/html
```

## Adding Screenshots

1. Take screenshots of your OpenCitiVibes instance
2. Save them in `images/screenshots/`:
   - `home.png` - Homepage view
   - `idea.png` - Single idea view
   - `submit.png` - Idea submission form
   - `admin.png` - Admin moderation panel
3. Update the JavaScript in `main.js` to reference actual images

## Customization

### Colors

Edit CSS variables in `css/styles.css`:

```css
:root {
    --color-primary: #2563eb;
    --color-secondary: #7c3aed;
    /* ... */
}
```

### Content

- Update text directly in HTML files
- Add/remove features in the features grid
- Update live instances section with real deployments

## Hosting

This site can be hosted on:
- GitHub Pages
- Netlify
- Vercel
- Any static file host

### GitHub Pages

```bash
# In your repo settings, enable GitHub Pages
# Set source to: docs/html directory
```

### Netlify

Drag and drop the `docs/html` folder to Netlify, or connect your repo and set:
- Build command: (none)
- Publish directory: `docs/html`

## Technologies

- Pure HTML5
- CSS3 with custom properties
- Vanilla JavaScript
- Inter font (Google Fonts)
- Fira Code for code blocks

No frameworks or build tools required!
