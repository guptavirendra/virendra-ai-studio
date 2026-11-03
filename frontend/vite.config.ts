import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const { VITE_API_URL = 'http://localhost:8000' } = loadEnv(mode, '.', '');

  return {
    plugins: [react()],
    server: {
      host: '0.0.0.0',
      port: 4173,
      proxy: {
        '/content': {
          target: VITE_API_URL,
          changeOrigin: true,
        },
        '/api': {
          target: VITE_API_URL,
          changeOrigin: true,
        },
      },
    },
  };
});
