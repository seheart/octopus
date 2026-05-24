/**
 * Svelte action: add a "Copy" button to every `<pre><code>` block inside the
 * action's host element. Re-scans on `update` so re-renders (streaming chat,
 * progressively appended tokens) get buttons added as new blocks appear.
 *
 * Usage:
 *   <div class="markdown-body" use:codeCopy>
 *     {@html renderMarkdown(content)}
 *   </div>
 */

function addButton(pre) {
  if (pre.dataset.copyWired === '1') return;
  pre.dataset.copyWired = '1';

  // Anchor the absolute-positioned button inside the <pre>.
  pre.style.position = 'relative';

  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className =
    'absolute top-1.5 right-1.5 opacity-0 group-hover/code:opacity-100 transition-opacity ' +
    'text-[10px] uppercase tracking-wider font-mono px-1.5 py-0.5 rounded ' +
    'bg-surface border border-border text-muted hover:text-accent hover:border-accent cursor-pointer';
  btn.textContent = 'copy';
  btn.setAttribute('aria-label', 'Copy code block');

  // Wrap in a group/code container so the hover-reveal works without forcing
  // it to always be visible (which would crowd short snippets).
  pre.classList.add('group/code');

  btn.addEventListener('click', async (e) => {
    e.stopPropagation();
    const code = pre.querySelector('code');
    const text = code ? code.innerText : pre.innerText;
    try {
      await navigator.clipboard.writeText(text);
      const orig = btn.textContent;
      btn.textContent = '✓ copied';
      setTimeout(() => {
        if (btn.isConnected) btn.textContent = orig;
      }, 1500);
    } catch (_) {
      /* clipboard blocked — silently degrade */
    }
  });

  pre.appendChild(btn);
}

function scan(node) {
  node.querySelectorAll('pre').forEach(addButton);
}

export function codeCopy(node) {
  scan(node);
  return {
    update() {
      // Streaming chat re-renders on every token; cheap to re-scan since the
      // data-attr guard makes addButton idempotent.
      scan(node);
    }
  };
}
