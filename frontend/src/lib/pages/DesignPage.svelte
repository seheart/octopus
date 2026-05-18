<script>
  import { Button, Card, Code, Section, Tag, StatRow } from '../components/ui/index.js';
  import { theme, setTheme } from '../stores/theme.svelte.js';
  import {
    DARK_BG,
    LIGHT_BG,
    DARK_PROFILE,
    LIGHT_PROFILE,
    darkFamily,
    lightFamily
  } from './design-palette.js';

  const modes = [
    { label: 'dark', bg: DARK_BG, profile: DARK_PROFILE, family: darkFamily },
    { label: 'light', bg: LIGHT_BG, profile: LIGHT_PROFILE, family: lightFamily }
  ];

  const surfaceTokens = [
    { name: 'canvas', desc: 'page background', class: 'bg-canvas' },
    { name: 'surface', desc: 'cards, panels', class: 'bg-surface' },
    { name: 'surface-2', desc: 'nested surfaces, inputs', class: 'bg-surface-2' },
    { name: 'border', desc: 'dividers, outlines', class: 'bg-border' },
    { name: 'body', desc: 'default text', class: 'bg-body' },
    { name: 'heading', desc: 'titles, emphasis', class: 'bg-heading' },
    { name: 'muted', desc: 'secondary text, labels', class: 'bg-muted' }
  ];

  const typeScale = [
    { name: 'text-xs', label: '12px — captions, footers' },
    { name: 'text-sm', label: '13px — secondary copy' },
    { name: 'text-base', label: '14px — body default' },
    { name: 'text-lg', label: '15px — emphasized body' },
    { name: 'text-xl', label: '16px — small headings' },
    { name: 'text-2xl', label: '18px — page headings' }
  ];
</script>

<div class="h-full overflow-y-auto px-6 py-6">
  <div class="max-w-5xl mx-auto space-y-8">
    <!-- Page header -->
    <div class="flex items-baseline justify-between">
      <div>
        <h1 class="text-2xl font-bold text-heading mb-1">Design System</h1>
        <p class="text-sm text-muted">
          The sanctioned tokens and primitives. New work uses these — no exceptions.
        </p>
      </div>
      <div class="flex gap-2">
        <Button
          variant={theme.value === 'light' ? 'primary' : 'secondary'}
          size="sm"
          onclick={() => setTheme('light')}>light</Button
        >
        <Button
          variant={theme.value === 'dark' ? 'primary' : 'secondary'}
          size="sm"
          onclick={() => setTheme('dark')}>dark</Button
        >
      </div>
    </div>

    <!-- The palette — both modes shown side-by-side regardless of current theme -->
    <Card padding="lg">
      <Section title="palette · ten hues, one tonal voice">
        <p class="text-sm text-muted mb-5 max-w-2xl">
          The full family at each mode's anchor: <span class="text-heading"
            >same saturation, same lightness within a mode; only hue varies.</span
          > Four hues are wired as semantic tokens — <span class="text-accent">· accent · success ·
            error · warning</span
          > — the other six are spare voices for charts, the oscilloscope, and future roles. Any
          new color picked must match the (S, L) profile.
        </p>

        <div class="space-y-6">
          {#each modes as mode (mode.label)}
            <div>
              <div class="flex items-baseline gap-3 mb-2 flex-wrap">
                <span class="font-mono text-sm text-heading">{mode.label}</span>
                <span class="font-mono text-xs text-muted">{mode.profile}</span>
                <span class="font-mono text-xs text-muted">against {mode.bg}</span>
              </div>
              <div class="rounded-lg border border-border overflow-hidden">
                <div
                  class="grid grid-cols-5 lg:grid-cols-10 gap-2 p-3"
                  style="background: {mode.bg};"
                >
                  {#each mode.family as c (c.name)}
                    <div
                      class="aspect-square rounded-md"
                      style="background: {c.hex};"
                      title="{c.name} · {c.hue} · {c.hex}"
                    ></div>
                  {/each}
                </div>
                <div class="grid grid-cols-5 lg:grid-cols-10 bg-surface-2 border-t border-border">
                  {#each mode.family as c (c.name)}
                    <div class="px-2 py-2 border-r border-border last:border-r-0 min-w-0">
                      <div class="font-mono text-xs text-heading truncate">{c.name}</div>
                      <div class="font-mono text-[10px] text-muted">{c.hue}</div>
                      <div class="font-mono text-[10px] text-muted truncate">{c.hex}</div>
                      {#if c.role}
                        <div class="font-mono text-[10px] text-accent mt-0.5 truncate">
                          · {c.role}
                        </div>
                      {/if}
                    </div>
                  {/each}
                </div>
              </div>
            </div>
          {/each}
        </div>
      </Section>
    </Card>

    <!-- Surface / text tokens -->
    <Card padding="lg">
      <Section title="surface &amp; text tokens">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
          {#each surfaceTokens as t (t.name)}
            <div class="flex items-center gap-3 p-2 rounded border border-border">
              <div class="w-10 h-10 rounded border border-border shrink-0 {t.class}"></div>
              <div class="min-w-0">
                <div class="font-mono text-sm text-heading">{t.name}</div>
                <div class="text-xs text-muted truncate">{t.desc}</div>
              </div>
            </div>
          {/each}
        </div>
      </Section>
    </Card>

    <!-- Typography -->
    <Card padding="lg">
      <Section title="typography">
        <div class="space-y-2">
          {#each typeScale as t (t.name)}
            <div class="flex items-baseline gap-3">
              <code class="font-mono text-xs text-muted w-24 shrink-0">{t.name}</code>
              <span class="{t.name} text-body">The quick brown octopus jumps over the lazy fox</span
              >
            </div>
          {/each}
          <div class="flex items-baseline gap-3 pt-2 border-t border-border">
            <code class="font-mono text-xs text-muted w-24 shrink-0">font-sans</code>
            <span class="font-sans text-body">Inter — for body and UI</span>
          </div>
          <div class="flex items-baseline gap-3">
            <code class="font-mono text-xs text-muted w-24 shrink-0">font-mono</code>
            <span class="font-mono text-body">JetBrains Mono — for stats and code</span>
          </div>
        </div>
      </Section>
    </Card>

    <!-- Buttons -->
    <Card padding="lg">
      <Section title="buttons">
        <div class="space-y-3">
          <div class="flex items-center gap-2 flex-wrap">
            <Button variant="primary">primary</Button>
            <Button variant="secondary">secondary</Button>
            <Button variant="ghost">ghost</Button>
            <Button disabled>disabled</Button>
          </div>
          <div class="flex items-center gap-2 flex-wrap">
            <Button size="sm" variant="primary">sm primary</Button>
            <Button size="sm" variant="secondary">sm secondary</Button>
            <Button size="sm" variant="ghost">sm ghost</Button>
          </div>
        </div>
      </Section>
    </Card>

    <!-- Code -->
    <Card padding="lg">
      <Section title="inline code">
        <p class="text-sm text-body">
          For inline references like <Code>npm run validate</Code> or
          <Code>src/app.css</Code> use the
          <Code>Code</Code> primitive — never paste-shape the styling.
        </p>
      </Section>
    </Card>

    <!-- Tags -->
    <Card padding="lg">
      <Section title="tags">
        <div class="flex items-center gap-2 flex-wrap">
          <Tag tone="neutral">neutral</Tag>
          <Tag tone="success">success</Tag>
          <Tag tone="error">error</Tag>
          <Tag tone="warning">warning</Tag>
        </div>
      </Section>
    </Card>

    <!-- Stat rows -->
    <Card padding="lg">
      <Section title="stat rows">
        <div class="space-y-1 max-w-sm">
          <StatRow label="tokens/sec" value="42.3" accent />
          <StatRow label="TTFT" value="183ms" />
          <StatRow label="tokens" value="247" />
          <StatRow label="total" value="5.8s" />
        </div>
      </Section>
    </Card>

    <!-- Governance -->
    <Card padding="lg">
      <Section title="rules of the road">
        <ul class="text-sm text-body space-y-1.5 list-disc pl-5">
          <li>
            Semantic accents (<Code>accent</Code>, <Code>success</Code>, <Code>error</Code>,
            <Code>warning</Code>) share one saturation/lightness — only hue varies. New accents
            must join the family.
          </li>
          <li>
            Color hex values are <strong>only</strong> declared in
            <Code>src/app.css</Code> (the token file).
          </li>
          <li>
            Components use semantic Tailwind utilities (<Code>bg-surface</Code>,
            <Code>text-heading</Code>) or <Code>var(--accent)</Code> — never arbitrary Tailwind color
            values (the <Code>bg-</Code> + bracketed-hex form).
          </li>
          <li>
            New buttons / cards / inputs use the primitives in
            <Code>lib/components/ui/</Code>. If a primitive is missing, add it here first.
          </li>
          <li>
            Pre-commit + CI enforce these via stylelint, eslint, and
            <Code>scripts/validate-patterns.sh</Code>.
          </li>
        </ul>
      </Section>
    </Card>
  </div>
</div>
