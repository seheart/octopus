<script>
  import OctoLogo from '../components/OctoLogo.svelte';
  import { Card, Section } from '../components/ui/index.js';
  import {
    DARK_BG,
    LIGHT_BG,
    PICKED_DARK,
    PICKED_LIGHT,
    darkOptions,
    lightOptions
  } from './labs-palette.js';
</script>

<div class="h-full overflow-y-auto px-6 py-6">
  <div class="max-w-5xl mx-auto space-y-8">
    <div>
      <h1 class="text-2xl font-bold text-heading mb-1">Labs</h1>
      <p class="text-sm text-muted">
        Logo color experiments. Swatches render against their real mode background so the contrast
        is honest — your current theme doesn't change what you see here.
      </p>
    </div>

    <Card padding="lg">
      <Section title="dark mode · against #0a0a0a">
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3">
          {#each darkOptions as opt (opt.hex)}
            <div class="rounded-lg border border-border overflow-hidden">
              <div class="flex items-center justify-center py-8" style="background: {DARK_BG};">
                <OctoLogo size={64} color={opt.hex} bg={DARK_BG} />
              </div>
              <div class="px-3 py-2 bg-surface-2">
                <div class="flex items-baseline justify-between gap-2">
                  <span class="font-mono text-sm text-heading">
                    {opt.name}{#if opt.hex === PICKED_DARK || opt.hex === PICKED_LIGHT}
                      <span class="ml-1.5 text-[10px] text-accent uppercase tracking-wider"
                        >· current</span
                      >
                    {/if}
                  </span>
                  <span class="font-mono text-xs text-muted">{opt.hex}</span>
                </div>
                <p class="text-xs text-muted mt-0.5">{opt.note}</p>
              </div>
            </div>
          {/each}
        </div>
      </Section>
    </Card>

    <Card padding="lg">
      <Section title="light mode · against #f6f4ef">
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3">
          {#each lightOptions as opt (opt.hex)}
            <div class="rounded-lg border border-border overflow-hidden">
              <div class="flex items-center justify-center py-8" style="background: {LIGHT_BG};">
                <OctoLogo size={64} color={opt.hex} bg={LIGHT_BG} />
              </div>
              <div class="px-3 py-2 bg-surface-2">
                <div class="flex items-baseline justify-between gap-2">
                  <span class="font-mono text-sm text-heading">
                    {opt.name}{#if opt.hex === PICKED_DARK || opt.hex === PICKED_LIGHT}
                      <span class="ml-1.5 text-[10px] text-accent uppercase tracking-wider"
                        >· current</span
                      >
                    {/if}
                  </span>
                  <span class="font-mono text-xs text-muted">{opt.hex}</span>
                </div>
                <p class="text-xs text-muted mt-0.5">{opt.note}</p>
              </div>
            </div>
          {/each}
        </div>
      </Section>
    </Card>

    <Card padding="lg">
      <Section title="status">
        <div class="text-sm text-muted space-y-1 mt-2 font-mono">
          <div>
            dark · <span class="text-heading">magenta #D546E2</span>
          </div>
          <div>
            light · <span class="text-heading">magenta #86298E</span>
          </div>
          <div class="text-xs text-muted mt-1">in-family with the design palette</div>
        </div>
      </Section>
    </Card>
  </div>
</div>
