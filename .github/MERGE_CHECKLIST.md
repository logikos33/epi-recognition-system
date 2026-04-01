# ═══════════════════════════════════════════════════════════════════════
# CHECKLIST OBRIGATÓRIO ANTES DE MERGE
# ═══════════════════════════════════════════════════════════════════════
#
# EPI Monitor - Processo de Merge Controlado
#
# Objetivo: Evitar regressões e bugs em produção através de validação
#          sistemática antes de cada merge.
#
# Regra de Ouro: **NUNCA fazer merge se o smoke test falhar.**
#
# ═══════════════════════════════════════════════════════════════════════

## ───────────────────────────────────────────────────────────────────────
## ANTES DE FAZER MERGE V2 → V2-clean (staging)
## ───────────────────────────────────────────────────────────────────────

### Preparação:
- [ ] `git checkout V2 && git status`
  - Verificar: sem arquivos não commitados
  - Se houver arquivos: commitar ou stashes antes de prosseguir

### Backend:
- [ ] Backend rodando: `curl http://localhost:5001/health`
  - Esperado: HTTP 200 com JSON {"status": "healthy"}
  - Se falhar: subir backend e aguardar startup completo

### Frontend:
- [ ] Frontend rodando: `curl http://localhost:3000`
  - Esperado: HTTP 200 com HTML da aplicação
  - Se falhar: iniciar Vite: `cd frontend-new && npm run dev`

### Smoke Test:
- [ ] Smoke test passou: `./scripts/validate-proxy.sh`
  - Esperado: "12 passaram | 0 falharam"
  - Se falhar: CORRIGIR antes de prosseguir
  - **BLOQUEADOR**: Não fazer merge se smoke test falhar

### Validação Manual (Navegação no Browser):
- [ ] MonitoringPage (grid CCTV)
  - Abrir: http://localhost:3000
  - Verificar: grid de câmeras carrega, overlays aparecem
  - Console: zero erros de 404 ou conexão

- [ ] CamerasPage
  - Verificar: lista de câmeras aparece
  - Console: zero erros

- [ ] TrainingPage - Tab "Vídeos & Dados"
  - Verificar: lista de vídeos aparece
  - Testar: upload de vídeo funciona
  - Console: zero erros

- [ ] TrainingPage - Tab "Anotar"
  - Verificar: frames aparecem para anotação
  - Testar: desenhar bounding box funciona
  - Console: zero erros

- [ ] TrainingPage - Tab "Treinar"
  - Verificar: estatísticas do dataset aparecem
  - Console: zero erros

- [ ] TrainingPage - Tab "Histórico"
  - Verificar: histórico de treinamentos aparece
  - Console: zero erros

- [ ] AnnotationInterface
  - Verificar: interface abre ao clicar em "Anotar" em um vídeo
  - Testar: desenhar box, salvar, carregar anotação
  - Console: zero erros

### Qualidade de Código:
- [ ] Nenhum botão novo sem funcionalidade real
  - Todos os botões devem ter handlers conectados a backend real
  - Zero botões "demo" ou "em desenvolvimento"

- [ ] Nenhum dado mockado introduzido
  - Todo dado no frontend vem de API real
  - Verificar: não há arrays MOCK ou dados hardcoded

### Merge:
- [ ] Criar tag de versão (opcional): `git tag -a v0.1.X -m "descrição"`
- [ ] Fazer merge: `git checkout V2-clean && git merge V2 --no-ff`
- [ ] Push: `git push origin V2-clean`
- [ ] Rodar smoke test na V2-clean: `./scripts/validate-proxy.sh`

## ───────────────────────────────────────────────────────────────────────
## ANTES DE FAZER MERGE V2-clean → main (produção)
## ───────────────────────────────────────────────────────────────────────

### Todos os itens da V2 → V2-clean:
- [ ] Revisar TODOS os itens acima (V2 → V2-clean)
- [ ] Confirmar que smoke test foi rodado na branch V2-clean

### Stress Test do Backend:
- [ ] Backend sobrevive ao stress test:
  ```bash
  for i in $(seq 1 50); do
    curl -s http://localhost:5001/health &
  done
  wait
  echo "Stress test completo - backend sobreviveu"
  ```
  - Esperado: Zero erros de conexão, zero crashes
  - Se falhar: investigar pool de conexões ou memory leak

### Testes Estendidos (10 minutos mínimo):
- [ ] Sistema rodando por 10 minutos sem erros no console
  - Monitorar: logs/api_server.log
  - Esperado: Zero exceptions, zero warnings críticos

### Deploy (após validação completa):
- [ ] Tag de versão criada: `git tag -a vX.Y.Z -m "Release: descrição"`
- [ ] Push da tag: `git push origin main --tags`
- [ ] Deploy no Railway iniciado automaticamente
- [ ] Monitorar deploy no dashboard do Railway
- [ ] Testar produção: https://epi-recognition-system-production.up.railway.app/health

### Pós-Deploy:
- [ ] Health check da produção: `curl https://epi-recognition-system-production.up.railway.app/health`
- [ ] Verificar logs no Railway: zero erros de startup
- [ ] Testar fluxo completo no ambiente de produção

## ───────────────────────────────────────────────────────────────────────
## ROLLBACK - SE ALGO DEU ERRADO APÓS O MERGE
## ───────────────────────────────────────────────────────────────────────

### Revert último merge:
```bash
# Reverter merge mantendo histórico
git revert -m 1 HEAD

# Se falhar, reset forçado (PERDE mudanças do merge)
git reset --hard HEAD~1

# Push do revert
git push origin V2-clean  # ou main
```

### Voltar para savepoint:
```bash
# Listar savepoints disponíveis
git tag -l "savepoint-*"

# Voltar para savepoint específico
git checkout savepoint-XXXX-XX
git branch -D V2-clean  # Se necessário
git checkout -b V2-clean savepoint-XXXX-XX
```

## ═══════════════════════════════════════════════════════════════════════
# CONTINGÊNCIA - EM CASO DE DÚVIDA
# ═══════════════════════════════════════════════════════════════════════

### Se o smoke test falhar:
1. NÃO fazer merge
2. Investigar falha:
   - Backend offline? Subir e verificar logs
   - Proxy quebrado? Verificar vite.config.js
   - Endpoint faltando? Criar ou corrigir
3. Corrigir problema
4. Rodar smoke test novamente
5. Só prosseguir quando passar

### Se encontrar bug durante testes manuais:
1. Documentar bug (issue no GitHub ou em TODO.md)
2. Se for crítico (bloqueia produção): corrigir antes do merge
3. Se for menor (não crítico): documentar e incluir próximo sprint
4. NEVER commitar código sabidamente bugado para "consertar depois"

### Se houver pressão para liberar rápido:
1. LEMBRAR: Um merge quebrado em produção = pior que um merge atrasado
2. Não pular etapas do checklist
3. Se for realmente crítico, pode fazer "hotfix" direto na main
   - Mas documentar motivo excepcional
   - Criar branch de hotfix separada
   - Merge com revisão mínima de 2 pessoas

# ═══════════════════════════════════════════════════════════════════════
# FIM DO CHECKLIST
# ═══════════════════════════════════════════════════════════════════════
