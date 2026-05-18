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
  import LabsPage from './lib/pages/LabsPage.svelte';
  import ScopeLabPage from './lib/pages/ScopeLabPage.svelte';
  import AboutPage from './lib/pages/AboutPage.svelte';
  import SettingsPage from './lib/pages/SettingsPage.svelte';
  import { route } from './lib/stores/route.svelte.js';
  import { initTheme } from './lib/stores/theme.svelte.js';
  import { startActivityPoller } from './lib/stores/activity.svelte.js';

  onMount(() => {
    initTheme();
    // Watches Ollama globally so the Oscilloscope shows activity from
    // every client (Octopus, raven, ollama CLI, …) — not just our chats.
    startActivityPoller();
  });
</script>

<div class="h-screen flex flex-col bg-canvas text-body font-sans">
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
    {:else if route.page === 'labs'}
      <LabsPage />
    {:else if route.page === 'scope-lab'}
      <ScopeLabPage />
    {:else if route.page === 'about'}
      <AboutPage />
    {:else if route.page === 'settings'}
      <SettingsPage />
    {/if}
  </div>
  <Footer />
</div>
