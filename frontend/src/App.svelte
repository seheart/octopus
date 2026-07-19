<script>
  import { onMount } from 'svelte';
  import Header from './lib/components/Header.svelte';
  import Footer from './lib/components/Footer.svelte';
  import Banner from './lib/components/Banner.svelte';
  import ChatPage from './lib/pages/ChatPage.svelte';
  import ModelsPage from './lib/pages/ModelsPage.svelte';
  import PullPage from './lib/pages/PullPage.svelte';
  import StoragePage from './lib/pages/StoragePage.svelte';
  import DiagnosticPage from './lib/pages/DiagnosticPage.svelte';
  import RoadmapPage from './lib/pages/RoadmapPage.svelte';
  import SystemPage from './lib/pages/SystemPage.svelte';
  import DesignPage from './lib/pages/DesignPage.svelte';
  import AboutPage from './lib/pages/AboutPage.svelte';
  import SettingsPage from './lib/pages/SettingsPage.svelte';
  import { route, go } from './lib/stores/route.svelte.js';
  import { initTheme } from './lib/stores/theme.svelte.js';
  import CommandPalette from './lib/components/CommandPalette.svelte';

  onMount(() => {
    initTheme();
    // The Ollama activity poller is acquired by the Oscilloscope itself
    // (see stores/activity.svelte.js) — it only runs while a scope is
    // actually on screen, instead of ticking 4×/second app-wide forever.
    window.addEventListener('keydown', onGlobalKey);
    return () => window.removeEventListener('keydown', onGlobalKey);
  });

  // Cmd+/ shows shortcuts (jumps to Settings). Cmd+N jumps to chat and
  // dispatches an event the ChatPage listens for to clear the thread.
  function onGlobalKey(e) {
    const meta = e.metaKey || e.ctrlKey;
    if (!meta) return;
    if (e.key.toLowerCase() === 'n') {
      e.preventDefault();
      go('chat');
      window.dispatchEvent(new CustomEvent('octopus:new-chat'));
    }
  }
</script>

<div class="h-screen flex flex-col bg-canvas text-body font-sans">
  <CommandPalette />
  <Banner />
  <Header />
  <div class="flex-1 overflow-hidden">
    {#if route.page === 'chat'}
      <ChatPage />
    {:else if route.page === 'models'}
      <ModelsPage />
    {:else if route.page === 'pull'}
      <PullPage />
    {:else if route.page === 'storage'}
      <StoragePage />
    {:else if route.page === 'diagnostic'}
      <DiagnosticPage />
    {:else if route.page === 'roadmap'}
      <RoadmapPage />
    {:else if route.page === 'system'}
      <SystemPage />
    {:else if route.page === 'design'}
      <DesignPage />
    {:else if route.page === 'about'}
      <AboutPage />
    {:else if route.page === 'settings'}
      <SettingsPage />
    {/if}
  </div>
  <Footer />
</div>
