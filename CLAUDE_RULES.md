# EPI Monitor — Regras do Projeto para Claude Code

## LEIA ESTE ARQUIVO ANTES DE QUALQUER AÇÃO EM QUALQUER SESSÃO

Este documento é obrigatório. Não é sugestão. É lei do projeto.
Violar qualquer regra = retrabalho = problema para a Ambev.
Ao iniciar qualquer sessão no projeto EPI Monitor, ler este arquivo
ANTES de executar qualquer comando ou alterar qualquer arquivo.

---

## 1. MISSÃO DO PROJETO

Sistema de reconhecimento de imagem para baias de carregamento da AMBEV.
Detecta produtos sendo carregados em caminhões via câmeras CCTV.
Contabiliza quantos produtos foram carregados e quanto tempo levou.
Futuro: identificar produto específico, detectar perda, compliance EPI.

Fases:
- MVP (atual): pipeline end-to-end com 1 câmera
- Fase 2: múltiplas baias, regras avançadas, integração SAP/ERP
- Fase 3: produto específico, IA de perda, compliance EPI automatizado

---

## 2. STACK TÉCNICA

- Backend: Flask (porta 5001), Python, psycopg2, YOLOv8, FFmpeg
- Frontend: React/Vite (porta 3000), HLS.js, Recharts
- Banco: PostgreSQL
- Branches: V2 (dev) → V2-clean (staging) → main (produção)
- Deploy: Railway (main = produção automática via push)

---

## 3. REGRAS DE PROTEÇÃO — O QUE NUNCA ALTERAR

### Frontend — PROIBIDO TOCAR:
- MonitoringPage e qualquer componente CCTV (grid, overlay, scanlines)
- AnnotationInterface.jsx (draw mode, select mode, keyboard shortcuts)
- VideoTimelineSelector.jsx
- Design system existente (cores, fontes, componentes base)
- Rotas do React Router já configuradas
- Qualquer componente que renderiza sem erro atualmente

### Backend — PROIBIDO TOCAR:
- Endpoints que respondem HTTP 200 (testar ANTES de qualquer mudança)
- Nomes de tabelas existentes no PostgreSQL
- Nomes de colunas existentes (apenas ADD COLUMN IF NOT EXISTS)
- Sistema de autenticação JWT existente
- YOLOTrainer e YOLOExporter existentes
- Extração de frames FFmpeg (1fps, 960px, q:v8, 4 workers)

### Banco de Dados — PROIBIDO ABSOLUTAMENTE:
- DROP TABLE
- RENAME TABLE ou RENAME COLUMN
- ALTER COLUMN que mude tipo de dados existente
- DELETE FROM em tabelas com dados sem autorização explícita

### Git — PROIBIDO:
- Push direto na branch main (usar Pull Request)
- Force push em branch pública
- Merge sem passar pelo smoke test (./scripts/validate-proxy.sh)
- Commit de arquivos .env ou secrets

---

## 4. O QUE É PERMITIDO

- ADD COLUMN IF NOT EXISTS
- CREATE TABLE IF NOT EXISTS
- CREATE INDEX IF NOT EXISTS
- Adicionar novos endpoints via Blueprint (nunca modificar existentes)
- Criar novos arquivos e componentes
- Registrar novos blueprints no api_server.py
- Adicionar novas regras de proxy no vite.config.ts (nunca remover)
- Commit e merge V2 → V2-clean após validação completa

---

## 5. BACKEND NUNCA PODE CAIR — REGRA CRÍTICA

O sistema roda em produção para a Ambev com câmeras monitorando baias.
Se o backend cair, a operação inteira fica cega. INACEITÁVEL.

### Causas já identificadas de queda:
1. next(get_db()) sem fechar → pool exhaustion → HTTP 502
2. Exceção não tratada em endpoint → processo morre
3. Exceção em thread de background → processo morre
4. Polling frontend sem backoff → flood de requests → sufoca backend
5. Treinamento YOLO na mesma thread → CPU 100% → timeouts

### Regras obrigatórias:

NUNCA usar next(get_db()):
  # ERRADO:
  db = next(get_db())
  # CORRETO:
  with get_db_connection() as conn:
      cur = conn.cursor()

SEMPRE handler global de exceções:
  @app.errorhandler(Exception)
  def handle_exception(e):
      logger.error(f"Unhandled: {e}\n{traceback.format_exc()}")
      return jsonify({'error': 'Erro interno'}), 500

NUNCA treinar na thread principal — subprocess isolado com nice -n 15.

Frontend SEMPRE com backoff exponencial:
  # ERRADO: setInterval(fetchData, 5000)
  # CORRETO: setTimeout com backoff até 60s

Stress test obrigatório após qualquer mudança no backend:
  for i in $(seq 1 50); do curl -s http://localhost:5001/health & done; wait
  curl -s http://localhost:5001/health

Usar ./start_backend.sh — NUNCA python api_server.py direto.

---

## 6. METODOLOGIA DE DESENVOLVIMENTO

### Antes de começar qualquer feature:
  git checkout V2
  git add -A && git commit -m "savepoint: antes de <feature>"
  git tag -a savepoint-<feature>-$(date +%Y%m%d-%H%M) -m "savepoint"
  git push origin V2 --tags
  ./scripts/validate-proxy.sh  # deve passar 100%

### Durante o desenvolvimento:
- 1 arquivo por vez → testar → confirmar → próximo
- Backend antes do frontend
- Commit após cada camada completa
- Se algo quebrar: git checkout HEAD -- <arquivo>

### Antes de merge V2 → V2-clean:
- [ ] ./scripts/validate-proxy.sh passa 100%
- [ ] curl http://localhost:5001/health retorna 200
- [ ] Stress test de 50 requests passa
- [ ] Zero erros novos no console do browser
- [ ] Nenhum dado mockado introduzido
- [ ] Todos os botões têm funcionalidade real

### NUNCA:
- Reportar como "pronto" sem ter testado
- Criar componente sem endpoint existente e testado com curl
- Alterar mais de 1 arquivo por tool call
- Usar "pausa estratégica" como desculpa para parar
- Commitar .env ou secrets

---

## 7. PADRÕES DE CÓDIGO OBRIGATÓRIOS

### Backend — todo endpoint:
  @blueprint.route('/api/exemplo', methods=['GET'])
  def meu_endpoint():
      try:
          with get_db_connection() as conn:
              cur = conn.cursor()
              cur.execute("SELECT ...", (param,))
              result = cur.fetchall()
          return jsonify({'data': result})
      except ValueError as e:
          logger.warning(f"Validation: {e}")
          return jsonify({'error': str(e)}), 400
      except Exception as e:
          logger.error(f"Error: {e}\n{traceback.format_exc()}")
          return jsonify({'error': 'Erro interno'}), 500

### Frontend — todo hook de dados:
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  // Os 3 estados SEMPRE tratados na UI

### Frontend — polling com backoff:
  let failCount = 0
  const poll = async () => {
    try {
      await fetchData()
      failCount = 0
      setTimeout(poll, 5000)
    } catch {
      failCount++
      setTimeout(poll, Math.min(5000 * Math.pow(2, failCount - 1), 60000))
    }
  }
  poll()

---

## 8. ESTRUTURA DO PROJETO

  /
  ├── api_server.py          ← rotas + registrar blueprints
  ├── cameras/               ← blueprint câmeras
  ├── rules/                 ← blueprint rules engine (a criar)
  ├── dashboard/             ← blueprint dashboard (a criar)
  ├── training/              ← otimização treinamento
  ├── migrations/            ← SQL numerados
  ├── scripts/validate-proxy.sh
  ├── start_backend.sh       ← SEMPRE usar para subir o backend
  ├── CLAUDE_RULES.md        ← ESTE ARQUIVO — ler em toda sessão
  └── frontend-new/
      ├── src/hooks/         ← lógica de dados
      ├── src/components/    ← UI
      └── vite.config.ts     ← proxy (NUNCA remover regras)

---

## 9. COMANDOS ESSENCIAIS

  # Subir ambiente:
  ./start_backend.sh &
  cd frontend-new && npm run dev

  # Smoke test (antes de todo merge):
  ./scripts/validate-proxy.sh

  # Stress test:
  for i in $(seq 1 50); do curl -s http://localhost:5001/health & done; wait

  # Verificar pool leaks (deve ser 0):
  grep -c "next(get_db)" api_server.py

  # Savepoint:
  git add -A && git commit -m "savepoint: descrição"
  git tag -a savepoint-$(date +%Y%m%d-%H%M) -m "descrição"
  git push origin V2 --tags

  # Merge para staging:
  ./scripts/validate-proxy.sh && \
    git checkout V2-clean && \
    git merge V2 --no-ff && \
    git push origin V2-clean && \
    git checkout V2

---

## 10. ROLLBACK DE EMERGÊNCIA

  # Ver savepoints:
  git tag -l "savepoint-*" | sort | tail -10

  # Reverter arquivo específico:
  git checkout HEAD -- caminho/arquivo.py

  # Reverter branch para savepoint:
  git reset --hard savepoint-NOME
  git push --force origin V2-clean  # apenas emergência

---

## 11. DIAGNÓSTICO QUANDO BACKEND CAI

  tail -50 logs/api_server.log | grep -i "error\|exception\|traceback"
  grep -c "next(get_db)" api_server.py  # deve ser 0
  ./start_backend.sh &

---

*Mantido por Vitor Emanuel (Logikos).*
*Atualizado conforme o projeto evolui.*
