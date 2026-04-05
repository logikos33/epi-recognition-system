# Débito Técnico: HTTP 401 na Aba Treinamento

**Data**: 2 de Abril de 2026
**Status**: 🔴 ABERTO - Não Crítico (sistema funciona pelo curl)
**Impacto**: Usuários não conseguem acessar a aba "Treinar" via browser

## Sintoma

```javascript
GET https://v2-clean-pre-producao.up.railway.app/api/training/videos
HTTP 401 (Unauthorized)
```

Console mostra:
- `hasToken: true` - Token existe no localStorage
- `tokenPreview: 'eyJhbGciOiJIUzI1NiIs...'` - Token válido
- Backend retorna `Invalid token`
- Auto-cleanup remove o token após 401

## Diagnóstico Realizado

### ✅ O que funciona:
1. **curl com token**: HTTP 200 ✅
2. **Logs do Railway**: Mostram `✅ Token válido!` para Chrome 120
3. **JWT_SECRET_KEY**: Confirmado atualizado no Railway
4. **Token payload**: Válido, não expirado (6+ dias restantes)

### ❌ O que não funciona:
1. **Browser Chrome/146**: HTTP 401 inconsistente
2. **Aba Treinar**: Requisições falham aleatoriamente

### 🕵️ Hipóteses (não confirmadas):
1. **Múltiplos tokens** no localStorage (conflito entre access_token e token)
2. **Race condition** em requisições paralelas (cleanup concorrente)
3. **Cache do browser** com versão antiga do frontend
4. **Encoding** do token (caracteres especiais corrompidos)
5. **CORS/Proxy** Railway modificando headers

## Workaround Conhecido

Usuários podem usar **curl** ou **Postman** para acessar os endpoints:
- Token JWT válido funciona via API
- Apenas interface web está afetada

## Próximos Passos (Quando Resolver)

1. **Adicionar logging detalhado** no frontend:
   - Mostrar token completo antes do envio
   - Capturar headers exatos da requisição

2. **Testar em browser limpo** (incognito mode):
   - Descartar cache/localstorage corrompido

3. **Verificar encoding**:
   - Comparar byte-a-byte o token no browser vs curl
   - Base64 decode/encode consistency

4. **Remover auto-cleanup agressivo**:
   - Comentar linhas 54-60 do api.js
   - Testar sem cleanup automático

## Arquivos Relacionados

- `frontend-new/src/services/api.js` (linhas 23-82: request handler)
- `frontend-new/src/App.tsx` (linhas 874-898: loadVideos)
- `api_server.py` (linhas 3045-3075: /api/training/videos endpoint)

## Notas

- Backend está funcionando corretamente (comprovado via curl)
- JWT_SECRET_KEY está correto e atualizado
- Token é válido e não expirado
- Problema é específico do browser (possível race condition ou cache)

---

**Criado por**: Claude Sonnet 4.5
**Tempo gasto**: ~4 horas em debugging
**Decisão**: Deixar como débito técnico e priorizar outras features
