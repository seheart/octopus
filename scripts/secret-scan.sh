#!/usr/bin/env bash
# secret-scan.sh — block commits containing secret-shaped literals.
# Mirrors the patterns in backend/main.py _AUDIT_PATTERNS so the
# diagnostic-page audit and the pre-commit hook stay in lockstep.

set -e

# Only scan staged files; nothing to do otherwise.
files=$(git diff --cached --name-only --diff-filter=ACMR)
[ -z "$files" ] && exit 0

# Skip files we know contain pattern-shaped strings intentionally:
# - test fixtures (stub credentials for regression coverage)
# - this script and backend/main.py (the audit patterns themselves are
#   "password"/"secret"-shaped by necessity)
skip() {
  case "$1" in
    *.test.*|*.spec.*|backend/test_main.py) return 0 ;;
    backend/main.py|scripts/secret-scan.sh) return 0 ;;
    *) return 1 ;;
  esac
}

FAIL=0
report() {
  echo "✗ $1: $2"
  FAIL=1
}

for f in $files; do
  [ -f "$f" ] || continue
  skip "$f" && continue
  # Credential literals (api_key=…, secret:…, bearer <token>)
  if grep -nE '(api[_-]?key|secret|password|bearer[[:space:]]+[A-Za-z0-9_-]{16,})[[:space:]]*[:=]' "$f" >/dev/null 2>&1; then
    report "$f" "possible credential literal"
  fi
  # AWS access key id
  if grep -nE 'AKIA[0-9A-Z]{16}' "$f" >/dev/null 2>&1; then
    report "$f" "AWS access key id"
  fi
  # GitHub personal-access token
  if grep -nE 'ghp_[A-Za-z0-9]{36}' "$f" >/dev/null 2>&1; then
    report "$f" "GitHub personal access token"
  fi
done

if [ $FAIL -ne 0 ]; then
  echo ""
  echo "Pre-commit blocked: secret-shaped literal in staged change. Remove or stage the fix."
  echo "If a true positive needs to land (e.g., a test fixture), name the file *.test.* / *.spec.*"
  exit 1
fi
