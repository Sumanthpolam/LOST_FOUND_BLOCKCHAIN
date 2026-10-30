import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // The repository name is the URL path used by this GitHub Pages site.
  base: process.env.GITHUB_ACTIONS ? '/LOST_FOUND_BLOCKCHAIN/' : '/',
});
