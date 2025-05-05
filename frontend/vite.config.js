import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';
import tailwindcss from '@tailwindcss/vite'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [
        react(),
        tailwindcss()
    ],
    root: '.',
    publicDir: 'public',
    server: {
        port: 3000,
        host: '0.0.0.0', // Explicitly set host for development server
        strictPort: true,
        historyApiFallback: true,
        allowedHosts: ['ai1.home']
    },
    resolve: {
        alias: {
            '@': '/src',
        },
    },
    build: {
        outDir: 'dist',
        emptyOutDir: true,
        rollupOptions: {
            input: {
                main: resolve(__dirname, 'index.html')
            }
        }
    },
    preview: {
        port: 3000,
        host: true,
        historyApiFallback: true,
        allowedHosts: ['ai.pashkovsky.me', 'ai1.home', 'frontend']
    },
});
