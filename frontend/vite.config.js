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
        host: true,
        strictPort: true,
        historyApiFallback: true
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
        historyApiFallback: true
    },
});
