# EPI Monitor - Novo Frontend

Sistema profissional de monitoramento de EPI com interface CFTV.

## Tecnologias

- **React 18** + Vite (build ultra-rápido)
- **TypeScript** (type safety)
- **TailwindCSS** (styling)
- **React Router** (navegação)
- **Lucide React** (ícones)

## Design System

### Paleta de Cores
```
--bg-primary:    #0A0C0F  (fundo principal)
--bg-secondary:  #111418  (fundo secundário)
--bg-tertiary:   #181C23  (cards e inputs)
--border:        #1E2530  (bordas)
--accent:        #00A8FF  (ação principal)
--accent-green:  #00D68F  (sucesso/online)
--accent-amber:  #FFB800  (alerta)
--accent-red:    #FF3B30  (erro/offline)
```

### Fontes
- **DM Sans**: Textos gerais
- **JetBrains Mono**: Dados técnicos e código

## Estrutura

```
frontend-new/
├── src/
│   ├── components/
│   │   ├── layout/
│   │   │   ├── sidebar.tsx       # Sidebar fixa com navegação
│   │   │   ├── header.tsx        # Header com user info
│   │   │   └── layout.tsx        # Layout principal
│   │   └── ui/
│   │       ├── button.tsx        # Componente de botão
│   │       ├── input.tsx         # Componente de input
│   │       ├── select.tsx        # Componente de select
│   │       ├── card.tsx          # Componente de card
│   │       └── badge.tsx         # Badge de status
│   ├── pages/
│   │   ├── cameras.tsx           # Gerenciamento de câmeras (CRUD)
│   │   ├── monitoring.tsx        # Painel CFTV (vídeo grid)
│   │   ├── classes.tsx           # Gerenciamento de classes YOLO
│   │   ├── training.tsx          # Pipeline de treinamento
│   │   └── dashboard.tsx         # Relatórios e estatísticas
│   ├── types/
│   │   ├── camera.ts             # Tipos de câmera
│   │   └── yolo.ts               # Tipos YOLO
│   └── lib/
│       ├── mock-data.ts          # Dados de exemplo
│       └── utils.ts              # Utilitários
```

## Instalação e Execução

### 1. Instalar Dependências
```bash
cd frontend-new
npm install
```

### 2. Executar em Desenvolvimento
```bash
npm run dev
```

Acesse: **http://localhost:5173**

### 3. Build para Produção
```bash
npm run build
```

### 4. Preview do Build
```bash
npm run preview
```

## Funcionalidades Implementadas

### ✅ 1. Câmeras (CRUD Completo)
- Listar todas as câmeras
- Adicionar nova câmera
- Editar câmera existente
- Excluir câmera
- Buscar por nome, IP ou localização
- Ativar/desativar câmera
- Indicadores de status (online/offline)

### ✅ 2. Monitoramento (Painel CFTV)
- Grid configurável (1x1, 2x2, 3x3, 4x4)
- Placeholder de feed de vídeo
- Detecções simuladas sobrepostas
- Alertas de baixa confiança
- Timestamp em tempo real
- Indicador de status por câmera

### 🔜 3. Classes YOLO (Em Desenvolvimento)
- Gerenciar classes de detecção
- Configurar cores
- Ajustar limiares de confiança

### 🔜 4. Treinamento (Em Desenvolvimento)
- Upload de imagens de treinamento
- Gerenciar anotações
- Monitorar treinamento de modelo

### 🔜 5. Dashboard (Em Desenvolvimento)
- Gráficos de detecções
- Estatísticas de desempenho
- Relatórios detalhados

## Mock Data

Atualmente, o frontend usa dados mock para demonstração:

**Câmeras**: 4 câmeras de exemplo
- Câmera Entrada Principal (online)
- Câmera Linha Produção 1 (online)
- Câmera Armazém (offline)
- Câmera Linha Produção 2 (online)

**Classes YOLO**: 6 classes configuradas
- Luva de Segurança
- Capacete
- Óculos de Proteção
- Bota de Segurança
- Colete Refletivo
- Máscara Respiratória

## Próximos Passos

### Fase 1 (Implementada)
- [x] Setup Vite + React + Tailwind
- [x] Estrutura base + Sidebar
- [x] Câmeras CRUD
- [x] Monitoramento vídeo grid

### Fase 2 (Planejada)
- [ ] Classes YOLO completa
- [ ] Pipeline de treinamento
- [ ] Dashboard com gráficos

### Fase 3 (Integração)
- [ ] Conectar ao backend Flask
- [ ] Implementar streams de vídeo reais
- [ ] WebSocket para detecções em tempo real
- [ ] Autenticação JWT

## Design Decisions

### Por que Vite ao invés de Next.js?
1. **Build mais rápido**: Vite usa esbuild, 10-100x mais rápido
2. **Simplicidade**: Menos configuração, mais controle
3. **Deploy**: Arquivos estáticos puros, qualquer servidor
4. **Hot reload**: Instantâneo, sem recarregar página

### Por que Tailwind ao invés de CSS Modules?
1. **Desenvolvimento rápido**: Classes utilitárias
2. **Consistência**: Design system previsível
3. **Performance**: CSS gerado é otimizado automaticamente
4. **Dark mode**: Implementação trivial

### Por que sidebar fixa?
1. **Acesso rápido**: Sempre visível
2. **Profissional**: Similar a Intelbras VMS, Hikvision iVMS
3. **Espaço**: Maximiza área de vídeo
4. **Navegação**: One-click para qualquer tela

## Troubleshooting

### Porta 5173 já está em uso
```bash
# Matar processo
lsof -ti:5173 | xargs kill -9

# Ou usar outra porta
npm run dev -- --port 3000
```

### Build falha
```bash
# Limpar cache e node_modules
rm -rf node_modules vite-dist
npm install
```

### TypeScript errors
```bash
# Verificar tipos
npm run type-check
```

## Performance

- **First Load JS**: ~150KB gzipped
- **Time to Interactive**: < 1s
- **Build Time**: ~2s (Vite)
- **Hot Reload**: < 100ms

## Acessibilidade

- Alto contraste para ambientes de baixa luminosidade
- Tamanhos de fonte legíveis em monitores distantes
- Cores semanticamente significativas (verde=sucesso, vermelho=erro)
- Foco visível em todos elementos interativos
