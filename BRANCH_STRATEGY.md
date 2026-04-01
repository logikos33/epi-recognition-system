# 🌿 Branch Strategy - EPI Recognition System

**Data**: 31 de Março de 2026  
**Propósito**: Definir fluxo de trabalho padrão para desenvolvimento e deploy

---

## 📋 Estrutura de Branches

| Branch | Ambiente | Propósito |
|--------|----------|-----------|
| **V2** | Desenvolvimento | Onde o código é escrito e testado localmente |
| **V2-clean** | Staging/Teste | Código validado antes de produção |
| **Main** | Produção | Código testado e aprovado para Railway deploy |

---

## 🔄 Fluxo de Trabalho (Padrão)

```
V2 (dev) → V2-clean (staging) → Main (produção)
```

**Regra de ouro**:  
⚠️ **NUNCA** comitar direto na Main ou V2-clean.  
Sempre partir da V2 para novas features.

---

## 📝 Processo Passo a Passo

### 1. Desenvolvimento (Branch V2)
- Criar features na V2
- Testar localmente
- Commitar com mensagens claras
- **Push**: `git push origin V2`

### 2. Validação (Branch V2-clean)
- Merge V2 → V2-clean
- Testar em ambiente de staging
- Validar todas as features
- **Push**: `git push origin V2-clean`

### 3. Produção (Branch Main)
- Merge V2-clean → Main
- Deploy automático no Railway
- Monitorar logs e métricas
- **Push**: `git push origin main`

---

## 🚀 Comandos Padrão

### Iniciar Nova Feature
```bash
git checkout V2
# ... escrever código ...
git add .
git commit -m "feat: descrição da feature"
git push origin V2
```

### Mover para Staging
```bash
git checkout V2-clean
git merge V2 --no-ff -m "merge: V2 → V2-clean - descrição"
git push origin V2-clean
```

### Mover para Produção
```bash
git checkout main
git merge V2-clean --no-ff -m "merge: V2-clean → Main - versão X.Y.Z"
git push origin main
```

---

## 🎯 Política de Merges

**Sempre usar `--no-ff`** (no fast-forward) para preservar histórico:
- Mantém histórico claro de quando cada merge aconteceu
- Facilita rollback se necessário
- Permite ver exatamente quando features entraram em cada ambiente

### Mensagens de Merge Padrão

**V2 → V2-clean:**
```
merge: V2 → V2-clean (staging) - [descrição das features]
```

**V2-clean → Main:**
```
merge: V2-clean → Main (production) - v[X.Y.Z] [descrição]
```

---

## ⚠️ Situações Especiais

### Branches Não Relacionadas

Se encontrar erro: `fatal: refusing to merge unrelated histories`

**Solução:**
```bash
git merge V2-clean --allow-unrelated-histories -s recursive -X theirs --no-ff
```

**Explicação:**  
Use `-X theirs` para favorecer conteúdo da branch sendo mergeada (V2-clean tem código mais recente).

### Conflitos de Merge

Se houver conflitos durante merge:

1. **Abortar** (se quiser recomeçar):
   ```bash
   git merge --abort
   ```

2. **Resolver manualmente**:
   ```bash
   # Editar arquivos com conflitos
   # Remover marcadores: <<<<<<< ======= >>>>>>>
   git add <arquivos_resolvidos>
   git commit -m "merge: resolução de conflitos"
   ```

---

## 📊 Histórico de Branches

### V2 (Dev)
- **Último commit**: 7e86e90 (fix: escape JSX comparison operators)
- **Total de commits únicos**: Integração completa
- **Propósito**: Código ativo em desenvolvimento

### V2-clean (Staging)
- **Último commit**: 7e86e90
- **Sync com V2**: 100% (fast-forward)
- **Propósito**: Validação antes de produção

### Main (Produção)
- **Último commit**: 2eda630 (merge: V2-clean → Main)
- **Deploy automático**: Railway (nixpacks.toml)
- **Propósito**: Ambiente de produção no Railway

---

## 🔄 Sync Estratégia

### Verificar Status dos Branches
```bash
# Ver commits em V2-clean que não estão em V2
git log --oneline V2..V2-clean

# Ver commits em Main que não estão em V2-clean
git log --oneline V2-clean..main

# Ver commits únicos em cada branch
git rev-list --count main --not V2-clean
git rev-list --count V2-clean --not V2
```

### Reposicionar Branch (CUIDADO - só se necessário)
```bash
# ⚠️ ATENÇÃO: Isso REESCREVE histórico
git checkout V2-clean
git reset --hard V2
git push origin V2-clean --force
# ❌ NÃO fazer em Main sem aprovação explícita
```

---

## 🚨 Regras de Ouro

1. ✅ **SEMPRE** desenvolver na V2 primeiro
2. ✅ **NUNCA** commitar direto na Main
3. ✅ **SEMPRE** usar `--no-ff` em merges
4. ✅ **SEMPRE** testar em V2-clean antes de ir para Main
5. ✅ **SEMPRE** fazer push após cada merge bem-sucedido
6. ❌ **NUNCA** fazer force push na Main (apenas em emergências extremas)
7. ❌ **NUNCA** rebase branches públicas (V2, V2-clean, Main)

---

## 📌 Tags de Versão (Futuro)

Quando implementar versionamento semântico:

```bash
# Na branch Main, após merge
git tag -a v0.1.0 -m "Versão 0.1.0 - MVP Completo"
git push origin v0.1.0
```

**Padrão sugerido:**
- `v0.X.Y` para desenvolvimento
- `v1.0.0` para primeira versão estável de produção
- `vX.Y.Z` para releases (semver)

---

## 🔗 Links Úteis

- **Railway Dashboard**: https://railway.app/project/...
- **GitHub Repository**: https://github.com/logikos33/epi-recognition-system
- **CI/CD**: Deploy automático via Railway Nixpacks

---

## 📝 Notas de Implementação

**Data de criação**: 31 de Março de 2026  
**Autor**: Vitor Emanuel (Logikos)  
**Versão**: 1.0

**Histórico de alterações:**
- 2026-03-31: Criação da estratégia de branches
- MVP Completo integrado: HLS Streaming + YOLO Training

---

**Próxima revisão**: Após primeiro ciclo completo de produção (V2 → V2-clean → Main)
