# EPI Recognition System

Sistema de monitoramento inteligente para detectar se colaboradores estão utilizando EPIs (Equipamentos de Proteção Individual) através de câmeras.

## 🎯 Visão Geral

O sistema utiliza arquitetura multi-agente com visão computacional para automatizar a fiscalização de compliance de EPIs em ambientes de trabalho, gerando alertas e relatórios visuais em tempo real.

## 🏗️ Arquitetura

```
epi_recognition_system/
├── agents/                      # Agentes do sistema
│   ├── recognition_agent.py     # Detecção de EPIs com YOLO
│   ├── annotation_agent.py      # Anotação e metadados
│   ├── orchestrator_agent.py    # Coordenação de todos os agentes
│   └── reporting_agent/         # Dashboard com Streamlit
│       ├── dashboard_main.py    # Dashboard principal
│       ├── alerts.py            # Página de alertas
│       ├── analytics.py         # Página de análises
│       └── history.py           # Página de histórico
├── models/                      # Modelos de dados
│   ├── database.py              # SQLAlchemy models
│   └── schemas.py               # Pydantic schemas
├── services/                    # Serviços
│   ├── yolo_service.py          # Wrapper YOLO
│   ├── database_service.py      # Operações de banco de dados
│   └── camera_service.py        # Captura de vídeo
├── utils/                       # Utilitários
│   ├── config.py                # Configurações
│   └── logger.py                # Logging
├── storage/                     # Armazenamento
├── tests/                       # Testes
├── main.py                      # Ponto de entrada
├── requirements.txt             # Dependências
└── .env.example                 # Variáveis de ambiente
```

## 🚀 Funcionalidades

- ✅ Detecção em tempo real de múltiplos EPIs (capacete, luvas, óculos, colete, botas)
- ✅ Monitoramento de múltiplas câmeras simultaneamente
- ✅ Dashboard interativo com Streamlit
- ✅ Sistema de alertas para não conformidades
- ✅ Relatórios de compliance e análises
- ✅ Armazenamento de histórico de detecções
- ✅ Visualização de bounding boxes e estatísticas

## 📋 Requisitos

- Python 3.8+
- PostgreSQL (ou SQLite para desenvolvimento)
- Webcam ou câmeras RTSP
- YOLOv8 model (baixado automaticamente)

## 🔧 Instalação

1. Clone o repositório:
```bash
git clone <repository-url>
cd "Repositorio Reconhecimento de EPI"
```

2. Crie um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente:
```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

## 🎮 Uso

### Iniciar o Sistema Completo

```bash
python main.py start
```

### Testar com uma Imagem

```bash
python main.py test --image caminho/para/imagem.jpg
```

### Testar com Vídeo

```bash
python main.py test --video caminho/para/video.mp4
```

### Monitorar Câmera Específica

```bash
python main.py camera --camera-id 0 --duration 60
```

### Abrir Dashboard

```bash
python main.py dashboard
```

### Ver Status do Sistema

```bash
python main.py status
```

## 🎨 Dashboard

O sistema possui 4 páginas principais:

1. **Dashboard Principal**: Visão geral com KPIs e métricas em tempo real
2. **Alertas**: Lista de violações com filtros e ações de resolução
3. **Análises**: Gráficos e tendências de compliance
4. **Histórico**: Busca e visualização de detecções passadas

### Abrir o Dashboard

```bash
streamlit run agents/reporting_agent/dashboard_main.py
```

Ou utilize o comando:

```bash
python main.py dashboard
```

## 🔧 Configuração

### Variáveis de Ambiente Principais

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/epi_monitoring

# YOLO Model
YOLO_MODEL_PATH=models/yolov8n.pt
DETECTION_CONFIDENCE_THRESHOLD=0.5

# Cameras
CAMERA_RTSP_URLS=rtsp://camera1,rtsp://camera2

# Streamlit
STREAMLIT_PORT=8501
```

### Tipos de EPI Configuráveis

- `helmet`: Capacete (obrigatório)
- `gloves`: Luvas (obrigatório)
- `glasses`: Óculos (obrigatório)
- `vest`: Colete (obrigatório)
- `boots`: Botas (opcional)

## 🧪 Testes

Executar todos os testes:

```bash
pytest tests/ -v
```

Executar testes específicos:

```bash
pytest tests/test_recognition.py -v
pytest tests/test_orchestrator.py -v
pytest tests/test_database.py -v
```

## 📊 Pipeline de Processamento

```
┌─────────────────┐
│  Camera Feed    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│         ORCHESTRATOR AGENT              │
│  ┌──────────────────────────────────┐   │
│  │  1. Capture Frame                │   │
│  └────────────┬─────────────────────┘   │
│               ▼                         │
│  ┌──────────────────────────────────┐   │
│  │  2. RECOGNITION AGENT            │   │
│  │     (YOLO Detection)             │   │
│  └────────────┬─────────────────────┘   │
│               ▼                         │
│  ┌──────────────────────────────────┐   │
│  │  3. ANNOTATION AGENT             │   │
│  │     (Metadata + Save)            │   │
│  └────────────┬─────────────────────┘   │
│               ▼                         │
│  ┌──────────────────────────────────┐   │
│  │  4. Save to PostgreSQL           │   │
│  └────────────┬─────────────────────┘   │
│               ▼                         │
│  ┌──────────────────────────────────┐   │
│  │  5. REPORTING AGENT              │   │
│  │     (Update Dashboard)           │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

## 🛠️ Desenvolvimento

### Adicionar Nova Câmera

```python
from agents.orchestrator_agent import get_orchestrator_agent

orchestrator = get_orchestrator_agent()
camera_id = orchestrator.add_camera(
    name="Camera 1",
    location="Fábrica - Linha A",
    rtsp_url="rtsp://192.168.1.100:554/stream"
)
```

### Customizar Tipos de EPI

Edite `utils/config.py`:

```python
EPI_TYPES = {
    "helmet": {"required": True, "label": "Capacete"},
    "gloves": {"required": True, "label": "Luvas"},
    # ... adicione mais EPIs
}
```

## 📈 Métricas e KPIs

O sistema monitora:
- Taxa de compliance por EPI
- Volume de detecções
- Alertas gerados
- Tendências temporais
- Performance por câmera

## 🔐 Segurança

- As câmeras RTSP devem estar em rede segura
- Use senhas fortes no PostgreSQL
- Configure firewall para portas do Streamlit
- Implemente HTTPS em produção

## 🐛 Troubleshooting

### YOLO Model Não Encontrado

```bash
# O modelo será baixado automaticamente na primeira execução
# Se falhar, baixe manualmente:
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
```

### Erro de Conexão com Câmera

```bash
# Teste a conexão RTSP:
ffplay rtsp://camera_url
```

### Database Connection Error

```bash
# Verifique se o PostgreSQL está rodando:
sudo systemctl status postgresql

# Ou use SQLite para desenvolvimento:
DATABASE_URL=sqlite:///./epi_monitoring.db
```

## 📝 Licença

Este projeto foi desenvolvido para fins de demonstração e uso interno.

## 👥 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 📞 Suporte

Para dúvidas ou problemas, abra uma issue no repositório.

---

Desenvolvido com ❤️ para melhorar a segurança no trabalho
