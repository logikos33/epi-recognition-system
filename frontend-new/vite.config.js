import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/**
 * ═══════════════════════════════════════════════════════════════════════
 * VITE CONFIGURATION — EPI Monitor Frontend
 * ═══════════════════════════════════════════════════════════════════════
 *
 * ⚠️  REGRA CRÍTICA: Este arquivo controla o proxy entre o frontend (porta 3000)
 *    e o backend Flask (porta 5001). Qualquer alteração aqui pode quebrar
 *    a comunicação com o backend em desenvolvimento E produção.
 *
 * ANTES DE ALTERAR:
 *   1. Criar savepoint: git tag -a savepoint-vite-YYYY-MM-DD
 *   2. Testar TODAS as rotas do proxy após a mudança
 *   3. Rodar: npm run validate:proxy antes de commitar
 *   4. Nunca remover uma regra de proxy sem confirmar que o frontend
 *      não usa mais aquela rota
 *
 * ADICIONAR nova rota de proxy:
 *   - Adicionar no objeto proxy abaixo
 *   - Documentar para que serve
 *   - Testar com curl http://localhost:3000/nova-rota
 *   - Adicionar ao smoke test em scripts/validate-proxy.sh
 *
 * ═══════════════════════════════════════════════════════════════════════
 */

export default defineConfig({
  plugins: [react()],

  server: {
    port: 3000,
    strictPort: true,
    host: true,
    watch: {
      usePolling: true,
      interval: 500,
    },

    proxy: {
      // ─── HEALTH CHECK ───────────────────────────────────────────────────
      // Status do backend — usado pelo BackendStatusBanner
      '/health': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        secure: false,
      },

      // ─── NEW MODULAR BACKEND (v1) ─────────────────────────────────────────
      // All new routes use /api/v1/ prefix — must be BEFORE the catch-all /api
      '/api/v1': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        secure: false,
        configure: (proxy) => {
          proxy.on('error', (err, req) => {
            console.error(`[Proxy] /api/v1${req.url} → ${err.message}`)
          })
        }
      },

      // ─── AUTENTICAÇÃO ─────────────────────────────────────────────────────
      // Login, registro, token refresh
      '/api/auth': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        secure: false,
      },

      // ─── TREINAMENTO (VIDEOS, FRAMES, ANNOTAÇÕES) ─────────────────────────
      // Upload de vídeos, extração de frames, anotações, dataset export
      // Inclui: /api/training/videos, /api/training/frames, /api/training/dataset
      '/api/training': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        secure: false,
        configure: (proxy) => {
          proxy.on('error', (err, req) => {
            console.error(`[Proxy] /api/training${req.url} → ${err.message}`);
          });
        }
      },

      // ─── CÂMERAS IP ────────────────────────────────────────────────────────
      // Gerenciamento de câmeras IP, RTSP URLs, testes de conectividade
      '/api/cameras': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        secure: false,
        configure: (proxy) => {
          proxy.on('error', (err, req) => {
            console.error(`[Proxy] /api/cameras${req.url} → ${err.message}`);
          });
        }
      },

      // ─── STREAMS HLS ─────────────────────────────────────────────────────
      // Controle de streams: start, stop, status, health
      '/api/streams': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        secure: false,
        configure: (proxy) => {
          proxy.on('error', (err, req) => {
            console.error(`[Proxy] /api/streams${req.url} → ${err.message}`);
          });
        }
      },

      // ─── STREAMS HLS (FILES) ──────────────────────────────────────────────
      // Arquivos .m3u8 e .ts gerados pelo FFmpeg para streaming
      // Servidos diretamente pelo backend Flask
      '/streams': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        secure: false,
        configure: (proxy) => {
          proxy.on('error', (err, req) => {
            console.error(`[Proxy] /streams${req.url} → ${err.message}`);
          });
        }
      },

      // ─── STORAGE ESTÁTICO ─────────────────────────────────────────────────
      // Imagens, thumbnails e arquivos servidos pelo backend
      // Inclui uploads, datasets, modelos treinados
      '/storage': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        secure: false,
      },

      // ─── CLASSES YOLO ─────────────────────────────────────────────────────
      // Classes de detecção (Produto, Caminhão, Placa, EPI, etc.)
      '/api/classes': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        secure: false,
      },

      // ─── PRODUTOS ─────────────────────────────────────────────────────────
      // CRUD de produtos do sistema
      '/api/products': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        secure: false,
      },

      // ─── WILDCARD GERAL ─────────────────────────────────────────────────────
      // Captura qualquer /api/* não listado acima — evita 404 silencioso
      // MANTER SEMPRE como última regra do proxy
      //
      // DEBUG: Adicione ?debug=true à URL para ver logs de proxy no console
      // Exemplo: http://localhost:3000/api/qualquer-coisa?debug=true
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        secure: false,
        configure: (proxy) => {
          proxy.on('error', (err, req) => {
            console.error(`[Proxy] /api${req.url} → BACKEND OFFLINE? ${err.message}`);
          });

          proxy.on('proxyReq', (proxyReq, req) => {
            // Log de requests em desenvolvimento para debugging
            if (req.query?.debug === 'true' || process.env.VITE_DEBUG_PROXY === 'true') {
              console.log(`[Proxy] ${req.method} ${req.url} → :5001`);
            }
          });
        }
      },
    }
  },

  cacheDir: '/tmp/vite-cache-epi',

  build: {
    outDir: 'dist',
    sourcemap: true,
  },

  resolve: {
    alias: {
      '@': '/src',
    },
  },
})
