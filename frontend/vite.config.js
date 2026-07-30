import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // The API base URL comes from VITE_API_URL (see .env.example); no proxy is
    // needed because the Django backend allows this origin via CORS.
  },
});
