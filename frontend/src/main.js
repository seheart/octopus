import { mount } from 'svelte';
// Self-hosted fonts via @fontsource so the SPA doesn't fetch from
// fonts.googleapis.com. Lets us ship a tight CSP without 'unsafe-*' for
// stylesheet sources and removes a third-party tracking surface.
import '@fontsource/inter/400.css';
import '@fontsource/inter/500.css';
import '@fontsource/inter/600.css';
import '@fontsource/inter/700.css';
import '@fontsource/jetbrains-mono/400.css';
import '@fontsource/jetbrains-mono/500.css';
import '@fontsource/jetbrains-mono/600.css';
import './app.css';
import App from './App.svelte';

const app = mount(App, { target: document.getElementById('app') });
export default app;
