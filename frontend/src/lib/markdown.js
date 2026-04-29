import DOMPurify from 'dompurify';
import { marked } from 'marked';

marked.setOptions({
  gfm: true,
  breaks: true
});

/** Render an assistant message as sanitized HTML. */
export function renderMarkdown(src) {
  if (!src) return '';
  const raw = marked.parse(src, { async: false });
  return DOMPurify.sanitize(raw, {
    ADD_ATTR: ['target', 'rel']
  });
}
