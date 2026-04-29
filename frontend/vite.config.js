import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte()],
  server: {
    port: 8801,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8800',
        changeOrigin: true
      }
    }
  }
});
