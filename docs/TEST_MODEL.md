# 🧪 Guia: Testar o Modelo de Detecção de EPI

Este guia detalha como testar o sistema de reconhecimento de EPI com diferentes métodos.

## 📋 Pré-requisitos

Antes de começar, certifique-se de:

- [x] Python 3.8+ instalado
- [x] Dependências instaladas: `pip install -r requirements.txt`
- [x] YOLOv8 baixado (automático na primeira execução)
- [x] Uma câmera configurada (webcam, IP ou celular)
- [x] Ambiente virtual ativo (opcional mas recomendado)

---

## 🚀 Teste Rápido (5 minutos)

### 1. Teste com Webcam

O teste mais simples - use a webcam do computador:

```bash
python main.py camera --camera-id 0 --duration 30
```

**O que acontece:**
- Abre a webcam (ID 0)
- Processa frames por 30 segundos
- Mostra estatísticas ao final

**Resultado esperado:**
```
✅ Pipeline completed successfully
Frames processed: 450
Detections: 15
Compliance rate: 73.33%
```

### 2. Teste com Imagem

Tenha uma imagem pronta:

```bash
python main.py test --image caminho/para/imagem.jpg
```

**Resultado esperado:**
```
✅ Detection successful
   Compliant: True/False
   Persons: 2
   EPIs detected: {'helmet': True, 'gloves': False, ...}
   Confidence: 0.85
```

### 3. Teste com Vídeo

```bash
python main.py test --video caminho/para/video.mp4
```

---

## 📱 Testar com Câmera do Celular

### Passo 1: Configurar Celular

**Android:**
1. Instale "IP Webcam" da Play Store
2. Abra o app e inicie o servidor
3. Anote o IP (ex: `http://192.168.1.100:8080`)

**iOS:**
1. Instale "CamTester" da App Store
2. Inicie o servidor
3. Anote a URL

### Passo 2: Testar Conexão

Abra no navegador:
```
http://SEU_IP:8080/video
```

Você deve ver o vídeo ao vivo.

### Passo 3: Adicionar ao Sistema

**Opção A: Interface Web**
```bash
python main.py dashboard
# Vá em "Gerenciar Câmeras" e adicione
```

**Opção B: Linha de Comando**
```bash
python main.py camera --camera-id 1 --duration 60
# Configure a URL no código ou .env
```

### Passo 4: Executar Detecção

```bash
# Atualize o .env com sua URL
echo "CAMERA_RTSP_URLS=http://192.168.1.100:8080/video" >> .env

# Inicie o sistema
python main.py start
```

---

## 🖼️ Testar com Imagens de Exemplo

### Criar Imagens de Teste

Se não tiver imagens, você pode:

1. **Buscar na internet:**
   - Google Images: "construction worker safety equipment"
   - Baixar 5-10 imagens

2. **Usar seu celular:**
   - Tire fotos de pessoas com EPIs
   - Salve na pasta `storage/test_images/`

3. **Usar dataset público:**
   - Construction Workers Safety Dataset
   - Safety Helmet Detection Dataset

### Testar com Múltiplas Imagens

Crie um script de teste:

```python
# test_batch.py
import os
from pathlib import Path
from agents.recognition_agent import get_recognition_agent

agent = get_recognition_agent()

test_images = Path("storage/test_images").glob("*.jpg")

for img_path in test_images:
    print(f"\n📸 Testando: {img_path.name}")
    result = agent.detect_epis(str(img_path))

    if result:
        print(f"  ✅ Compliant: {result.is_compliant}")
        print(f"  👥 Persons: {result.person_count}")
        print(f"  🛡️ EPIs: {result.epis_detected}")
        print(f"  📊 Confidence: {result.confidence:.2f}")
```

Execute:
```bash
python test_batch.py
```

---

## 🎥 Testar com Vídeo

### Vídeos de Teste

**Opções:**
1. Gravar com seu celular
2. Baixar do YouTube (formatos curtos)
3. Usar vídeos de datasets públicos

### Executar Teste

```bash
# Teste completo com anotações
python main.py test --video video.mp4

# O sistema vai:
# 1. Processar cada frame
# 2. Detectar EPIs
# 3. Salvar vídeo anotado
# 4. Gerar estatísticas
```

### Ver Resultados

Os resultados são salvos em:
```
storage/annotated/
├── frame_0001.jpg
├── frame_0002.jpg
└── ...
```

---

## 🎯 Cenários de Teste

### Cenário 1: Detecção Completa (Conforme)

**Setup:**
- Pessoa com todos os EPIs obrigatórios
- Boa iluminação
- Distância: 1-2 metros

**Esperado:**
```
✅ Compliant: True
🛡️ EPIs detectados: helmet (✓), gloves (✓), glasses (✓), vest (✓)
📊 Confidence: >0.70
```

### Cenário 2: Detecção Parcial (Não Conforme)

**Setup:**
- Pessoa faltando 1-2 EPIs
- Mesmas condições de iluminação

**Esperado:**
```
❌ Compliant: False
🛡️ EPIs faltando: gloves, glasses
📊 Confidence: >0.70
```

### Cenário 3: Múltiplas Pessoas

**Setup:**
- 2-3 pessoas no frame
- Algumas conformes, outras não

**Esperado:**
```
👥 Persons: 3
✅ Compliant: 2/3
📊 Confidence: >0.65
```

### Cenário 4: Baixa Iluminação

**Setup:**
- Ambiente com pouca luz
- Pessoa com EPIs

**Esperado:**
```
⚠️ Possível redução na confiança
📊 Confidence: 0.50-0.70
```

---

## 📊 Métricas de Avaliação

### Taxa de Detecção

Calcule a porcentagem de EPIs corretamente detectados:

```
Taxa = (EPIs Detectados / EPIs Presentes) × 100
```

**Bom:** >80%
**Aceitável:** 60-80%
**Precisa melhorar:** <60%

### Precisão (Precision)

```
Precision = (Verdadeiros Positivos) / (Todos os Positivos)
```

### Revocação (Recall)

```
Recall = (Verdadeiros Positivos) / (Todos os Reais)
```

### F1-Score

```
F1 = 2 × (Precision × Recall) / (Precision + Recall)
```

---

## 🐛 Troubleshooting

### Problema: "Model not found"

**Solução:**
```bash
# O modelo será baixado automaticamente
# Se falhar, baixe manualmente:
mkdir -p models
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt -O models/yolov8n.pt
```

### Problema: "No detections"

**Possíveis causas:**
- Frame muito escuro
- Objetos muito pequenos
- Pessoa muito distante
- Modelo não treinado para EPIs específicos

**Soluções:**
- Melhore a iluminação
- Aproxime a câmera
- Use câmera com melhor resolução
- Considere treinar modelo customizado

### Problema: "Low confidence"

**Soluções:**
- Ajuste `DETECTION_CONFIDENCE_THRESHOLD` no `.env`
- Melhore a qualidade da imagem
- Use modelo maior (yolov8s, yolov8m)

### Problema: "Camera connection failed"

**Soluções:**
- Verifique se a URL está correta
- Teste no navegador primeiro
- Verifique o firewall
- Use a mesma rede Wi-Fi (para celular)

---

## 🎓 Teste Avançado: Treinamento Customizado

Se precisar de melhor precisão:

### 1. Coletar Datasets

- Construction Workers Dataset
- Safety Helmet Wearing Dataset
- Próprias imagens anotadas

### 2. Preparar Dataset

```bash
# Estrutura de pastas
dataset/
├── images/
│   ├── train/
│   └── val/
└── labels/
    ├── train/
    └── val/
```

### 3. Treinar Modelo

```python
from ultralytics import YOLO

# Carregar modelo base
model = YOLO('yolov8n.pt')

# Treinar
model.train(
    data='dataset.yaml',
    epochs=100,
    imgsz=640
)
```

---

## 📈 Relatório de Testes

Após os testes, documente:

```markdown
## Relatório de Testes - EPI Recognition

### Data: 2024-XX-XX

### Ambiente
- Sistema Operacional: Windows 10 / macOS / Linux
- Python: 3.X.X
- Câmera: Webcam / IP / Celular
- Iluminação: Boa / Regular / Ruim

### Testes Realizados

#### Teste 1: Webcam
- ✅ Sucesso
- Taxa de detecção: 85%
- Precisão: 0.82

#### Teste 2: Câmera Celular
- ✅ Sucesso
- Latência: ~200ms
- Taxa de detecção: 78%

#### Teste 3: Vídeo
- ✅ Sucesso
- 15 detecções em 30 segundos
- Compliance rate: 73%

### Conclusões
- [ ] Sistema funcional
- [ ] Precisa de ajustes
- [ ] Pronto para produção

### Próximos Passos
1. Treinar modelo customizado
2. Ajustar threshold de detecção
3. Adicionar mais tipos de EPI
```

---

## 🚀 Próximos Passos

Após os testes:

1. ✅ **Sistema funcionando?**
   - Configure as câmeras definitivas
   - Ajuste os thresholds
   - Inicie o monitoramento 24/7

2. ⚠️ **Precisa melhorar?**
   - Treine modelo customizado
   - Ajuste configurações
   - Melhore a iluminação

3. 📊 **Quer analytics?**
   - Acesse o dashboard
   - Configure alertas
   - Exporte relatórios

---

**Próximo passo:** [Documentação Principal](README.md) →
