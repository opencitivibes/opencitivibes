# Shadcn/UI Customization Guide

**Project:** Idées pour Montréal
**Created:** 2025-11-20
**Purpose:** Guide for customizing Shadcn/UI components to match brand guidelines

---

## Table of Contents

1. [Overview](#overview)
2. [Setup Complete](#setup-complete)
3. [Customization Strategy](#customization-strategy)
4. [Component Usage](#component-usage)
5. [Brand Alignment](#brand-alignment)
6. [Adding New Components](#adding-new-components)

---

## Overview

Shadcn/UI has been integrated into the project to provide accessible, well-tested components for complex UI patterns like modals, dropdowns, and tabs. The integration is configured to work seamlessly with our existing purple-forward brand guidelines.

### Why Shadcn/UI?

- **Accessibility-first:** Built on Radix UI primitives with proper ARIA attributes
- **Customizable:** Copy-paste components that you own and can modify
- **Not a dependency:** Components are copied into your codebase, not installed as a package
- **Brand-compatible:** Works with our existing Tailwind configuration

---

## Setup Complete

The following setup has been completed for Phase 1:

### ✅ Installed Dependencies
- `clsx` - For conditional className merging
- `tailwind-merge` - For Tailwind class conflict resolution
- `tailwindcss-animate` - For component animations

### ✅ Configuration Files
- **`components.json`** - Shadcn/UI configuration file
  - Style: New York (Recommended)
  - TypeScript: Enabled
  - RSC (React Server Components): Enabled
  - CSS Variables: Enabled
  - Component path: `src/components/ui`

- **`tailwind.config.ts`** - Updated with:
  - Container configuration (centered, 2rem padding)
  - Border radius CSS variables
  - Accordion animations (accordion-down, accordion-up)
  - tailwindcss-animate plugin

- **`globals.css`** - Added:
  - `--radius: 0.5rem` (8px) for consistent border radius

### ✅ Utility Files
- **`src/lib/utils.ts`** - Created with `cn()` helper function
  ```typescript
  import { type ClassValue, clsx } from "clsx"
  import { twMerge } from "tailwind-merge"

  export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs))
  }
  ```

### ✅ Directory Structure
```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/              # Shadcn components go here
│   │   ├── Button.tsx       # Custom components (keep)
│   │   ├── Card.tsx         # Custom components (keep)
│   │   └── ...
│   └── lib/
│       └── utils.ts         # cn() helper function
└── components.json          # Shadcn config
```

---

## Customization Strategy

### Custom Components to KEEP

These components are already well-aligned with our brand guidelines and should **not** be replaced:

✅ **Button** - Already has primary, secondary, ghost variants with purple theme
✅ **Card** - Custom gradient and interactive variants specific to our brand
✅ **Badge** - Status-specific styling already defined
✅ **Alert** - Custom variants working well
✅ **Input** - Brand-aligned focus states
✅ **Textarea** - Consistent with Input component
✅ **Select** - Custom styling matches brand
✅ **PageContainer** - Project-specific layout component
✅ **PageHeader** - Project-specific header component

### Shadcn Components to ADD

Use Shadcn/UI for these complex, accessibility-critical components:

🔲 **Dialog (Modal)** - Better accessibility than manual implementation
🔲 **Dropdown Menu** - Proper keyboard navigation and ARIA
🔲 **Tabs** - Accessible tab switching
🔲 **Toast** - Modern notification system
🔲 **Popover** - Contextual help and information
🔲 **Command** - Power user navigation (Cmd+K)
🔲 **Tooltip** - Better UX for icon buttons
🔲 **Accordion** - Expandable sections

---

## Component Usage

### Installing Components

To add a Shadcn component, use the CLI:

```bash
cd frontend
npx shadcn@latest add dialog
npx shadcn@latest add dropdown-menu
npx shadcn@latest add tabs
# etc.
```

This will:
1. Download the component to `src/components/ui/`
2. Install any required Radix UI dependencies
3. Make the component ready to customize

### Customizing for Brand

After adding a component, customize it to match our purple theme:

#### Example: Customizing Dialog

**Before (Default):**
```typescript
// Dialog with default colors
<DialogTrigger className="bg-black text-white">
```

**After (Brand Aligned):**
```typescript
// Dialog with purple primary color
<DialogTrigger className="bg-primary-500 hover:bg-primary-600 text-white">
```

#### Example: Customizing Dropdown Menu

Look for color classes and replace with our brand colors:

```typescript
// Replace:
bg-slate-100 → bg-primary-50
text-slate-900 → text-gray-900
border-slate-200 → border-gray-200
focus:bg-slate-100 → focus:bg-primary-50
```

---

## Brand Alignment

### Color Mapping

When customizing Shadcn components, use these color replacements:

| Shadcn Default | Our Brand Color | Usage |
|----------------|-----------------|-------|
| `bg-black` | `bg-primary-500` | Primary buttons |
| `bg-slate-100` | `bg-primary-50` | Hover backgrounds |
| `border-slate-200` | `border-gray-200` | Borders |
| `text-slate-900` | `text-gray-900` | Primary text |
| `text-slate-500` | `text-gray-500` | Secondary text |
| `ring-slate-950` | `ring-primary-500` | Focus rings |

### Typography

Shadcn components use system fonts by default, which matches our configuration:
```typescript
fontFamily: {
  sans: ['-apple-system', 'BlinkMacSystemFont', ...]
}
```

No changes needed for typography!

### Spacing

Shadcn follows the same 8-point grid system we use (via Tailwind defaults).
No changes needed for spacing!

### Border Radius

We've configured `--radius: 0.5rem` (8px) to match our brand guidelines.
Shadcn components will automatically use this value.

---

## Adding New Components

### Step-by-Step Process

1. **Add the component:**
   ```bash
   npx shadcn@latest add [component-name]
   ```

2. **Locate the file:**
   ```
   frontend/src/components/ui/[component-name].tsx
   ```

3. **Customize colors:**
   - Find all color-related classes
   - Replace with brand colors (primary, gray, semantic)
   - Test with keyboard navigation

4. **Test accessibility:**
   - Verify focus states are visible (should use primary-500 ring)
   - Test with keyboard (Tab, Enter, Escape, Arrows)
   - Verify ARIA attributes are present

5. **Document usage:**
   - Add examples to this guide
   - Update component inventory in TODO.md

### Example: Adding Dialog Component

```bash
# Step 1: Add component
cd frontend
npx shadcn@latest add dialog

# Step 2: Customize in src/components/ui/dialog.tsx
# Replace slate colors with primary/gray colors

# Step 3: Use in your pages
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog"
```

---

## Best Practices

### Do's ✓

- **Always test keyboard navigation** after customizing
- **Keep the same accessibility attributes** (aria-*, role)
- **Use our color palette** (primary, gray, semantic colors)
- **Maintain focus ring visibility** (primary-500 with ring-offset-2)
- **Test with screen readers** when possible

### Don'ts ✗

- **Don't remove ARIA attributes** - They're critical for accessibility
- **Don't use arbitrary colors** - Stick to brand palette
- **Don't modify Radix UI behavior** - Only customize styling
- **Don't skip focus states** - Always ensure visible focus indicators
- **Don't use default black/slate** - Replace with purple primary

---

## Component Inventory

### Phase 2: Planned Shadcn Components

Track which components have been added and customized:

- [ ] **Dialog** - Modal dialogs with backdrop
- [ ] **Dropdown Menu** - Accessible dropdown menus
- [ ] **Tabs** - Tab navigation
- [ ] **Toast** - Notification system
- [ ] **Popover** - Contextual popovers
- [ ] **Select** - Enhanced select (evaluate vs custom)
- [ ] **Command** - Command palette (Cmd+K)
- [ ] **Tooltip** - Accessible tooltips
- [ ] **Accordion** - Expandable sections

### Customization Checklist

For each component added, verify:

- [ ] Colors match brand guidelines (purple primary)
- [ ] Focus states use primary-500 ring
- [ ] Keyboard navigation works
- [ ] ARIA attributes preserved
- [ ] Responsive on mobile/tablet/desktop
- [ ] Works in English and French

---

## Resources

### Shadcn/UI Documentation
- Main site: https://ui.shadcn.com/
- Components: https://ui.shadcn.com/docs/components
- Themes: https://ui.shadcn.com/themes

### Radix UI Documentation
- Primitives: https://www.radix-ui.com/primitives
- Accessibility: https://www.radix-ui.com/primitives/docs/overview/accessibility

### Our Brand Guidelines
- See: `BRAND_GUIDELINES.md` for complete color palette and design tokens

---

## Troubleshooting

### Issue: Component doesn't match brand colors

**Solution:** Find and replace default colors:
```typescript
// Find:
className="bg-black text-white"
// Replace:
className="bg-primary-500 hover:bg-primary-600 text-white"
```

### Issue: TypeScript errors with imports

**Solution:** Check that path aliases are configured in `tsconfig.json`:
```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

### Issue: Styles not applying

**Solution:** Ensure Tailwind content includes ui directory:
```typescript
// tailwind.config.ts
content: [
  './src/components/**/*.{js,ts,jsx,tsx,mdx}', // Includes ui/
]
```

---

## Version History

### Version 1.0.0 (2025-11-20)
- Initial Shadcn/UI setup and configuration
- Created customization guide
- Configured purple primary color scheme
- Set up component directory structure

---

**Maintainer Note:** Update this guide as new components are added and customization patterns emerge.
