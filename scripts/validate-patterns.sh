#!/usr/bin/env bash
# validate-patterns.sh — design-system enforcement.
# Bans direct color usage in Svelte components. The only sanctioned
# place to declare colors is frontend/src/app.css (the token file).
# Use semantic Tailwind utilities (bg-surface, text-heading, etc.)
# or CSS variables (var(--accent)) in components.

set -e

SRC=${1:-"frontend/src"}
FAIL=0

echo "→ checking $SRC for forbidden color patterns..."

# 1. Tailwind arbitrary color values: bg-[#xxxxxx], text-[rgb(...)]
if grep -rn --include="*.svelte" --include="*.html" \
    -E '(bg|text|border|ring|fill|stroke|from|to|via)-\[(#|rgb|hsl)' \
    "$SRC" 2>/dev/null; then
  echo ""
  echo "✗ Tailwind arbitrary colors found. Use semantic tokens (bg-surface, text-heading, ...)"
  FAIL=1
fi

# 2. Hex colors in inline style attributes (allow var() usage)
if grep -rn --include="*.svelte" --include="*.html" \
    -E 'style="[^"]*#[0-9a-fA-F]{3,8}' \
    "$SRC" 2>/dev/null; then
  echo ""
  echo "✗ Inline hex colors found. Use CSS variables (style=\"color: var(--accent)\")."
  FAIL=1
fi

# 3. Hex colors anywhere in .svelte files outside <style> blocks
# (style blocks are linted by stylelint; this catches script/markup leaks)
if grep -rn --include="*.svelte" \
    -E "['\"]#[0-9a-fA-F]{3,8}['\"]" \
    "$SRC" 2>/dev/null | grep -vE "^[^:]+:[^:]+:\s*//"; then
  echo ""
  echo "✗ Hex color literals in component code. Use CSS variables or token utilities."
  FAIL=1
fi

# 4. rgb()/rgba()/hsl()/hsla() literals in .svelte files. The hex check above
# misses these and they bypass the token system just the same.
if grep -rn --include="*.svelte" \
    -E "(rgba?\(|hsla?\()[^)]" \
    "$SRC" 2>/dev/null | grep -vE "^[^:]+:[^:]+:\s*//"; then
  echo ""
  echo "✗ rgb()/hsl() color literals in component code. Use CSS variables or token utilities."
  FAIL=1
fi

if [ $FAIL -eq 0 ]; then
  echo "✓ no forbidden patterns"
fi
exit $FAIL
