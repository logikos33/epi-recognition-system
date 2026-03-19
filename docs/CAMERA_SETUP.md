# 📱 Guia: Usar Câmera do Celular para Testes

Este guia detalha como usar seu celular como câmera para testar o sistema de reconhecimento de EPI.

## 🤖 Android - IP Webcam

### Instalação

1. Abra a Google Play Store
2. Busque por **"IP Webcam"**
3. Instale o app (gratuito)

### Configuração

1. **Abra o app IP Webcam**
2. Role para baixo até encontrar a seção de servidor
3. Toque em **"Start server"** (botão azul na parte inferior)
4. Anote o **endereço IP** mostrado (ex: `http://192.168.1.100:8080`)

![IP Webcam Interface](https://raw.githubusercontent.com/ultralytics/assets/main/yolov8/streamlit/img/ipwebcam1.jpg)

### Conectar no Sistema

**Opção 1: Pela Interface Web**

1. Abra a página de gerenciamento de câmeras
2. Preencha o formulário:
   - **Nome**: Câmera Android
   - **Localização**: Teste Local
   - **Tipo**: http
   - **URL**: `http://SEU_IP:8080/video`
3. Clique em "Testar Conexão"
4. Se funcionar, clique em "Adicionar Câmera"

**Opção 2: Pela Linha de Comando**

```bash
python main.py camera --camera-id 0 --duration 30
# Depois configure a URL no arquivo .env:
# CAMERA_RTSP_URLS=http://192.168.1.100:8080/video
```

### Solução de Problemas

**❌ Não conecta:**
- Verifique se celular e PC estão na mesma rede Wi-Fi
- Desative o VPN se estiver usando
- Verifique o firewall do Windows/Mac

**❌ Imagem preta:**
- Role para baixo no app IP Webcam
- Em "Video preferences", mude a resolução
- Tente "480p" ou "720p"

**❌ Lentidão:**
- Reduza a qualidade do vídeo
- Use resolução mais baixa (640x480)
- Aproxime o celular do roteador

---

## 🍎 iOS - CamTester

### Instalação

1. Abra a App Store
2. Busque por **"CamTester"** ou **"Webcam"**
3. Instale o app

### Configuração

1. **Abra o app**
2. Toque em "Start Server"
3. Anote a URL HTTP mostrada
4. Use a URL no sistema

### Conectar no Sistema

Siga os mesmos passos da seção Android, usando a URL fornecida pelo app iOS.

---

## 🌐 Verificar o IP do Celular

### Android

1. Vá em **Configurações** > **Rede e Internet** > **Wi-Fi**
2. Toque na rede conectada
3. Procure por **"Endereço IP"**

### iOS

1. Vá em **Configurações** > **Wi-Fi**
2. Toque no **(i)** ao lado da rede conectada
3. O IP está listado como **"Endereço IP"**

---

## 📋 Checklist Completo

Antes de testar, verifique:

- [ ] Celular e computador na mesma rede Wi-Fi
- [ ] App de câmera instalado
- [ ] Servidor iniciado no app
- [ ] IP anotado corretamente
- [ ] Firewall do computador configurado
- [ ] URL testada no navegador primeiro

---

## 🧪 Teste Rápido

### 1. Testar URL no Navegador

Antes de usar no sistema, abra a URL no navegador:

```
http://SEU_IP:8080/video
```

Você deve ver o vídeo do celular em tempo real.

### 2. Testar com Python

```python
import cv2

# Substitua pelo seu IP
url = "http://192.168.1.100:8080/video"

cap = cv2.VideoCapture(url)

if cap.isOpened():
    print("✅ Conexão bem-sucedida!")
    ret, frame = cap.read()
    if ret:
        print(f"✅ Frame capturado: {frame.shape}")
    cap.release()
else:
    print("❌ Falha na conexão")
```

### 3. Testar no Sistema

```bash
# Opção 1: Interface web
python main.py dashboard

# Opção 2: Linha de comando
python main.py camera --camera-id 0 --duration 60
```

---

## 🔧 Configuração Avançada

### Qualidade de Vídeo

No IP Webcam (Android):
- Role até "Video preferences"
- Escolha a resolução:
  - **Baixa latência**: 640x480
  - **Alta qualidade**: 1280x720
  - **Ultra**: 1920x1080

### Taxa de FPS

- Para detecção em tempo real: 15-30 FPS
- Para testes básicos: 10-15 FPS

### Autenticação

Se o app exigir senha:

```
http://USUARIO:SENHA@192.168.1.100:8080/video
```

---

## 🚀 Comandos Úteis

### Ver câmeras ativas no sistema

```bash
python main.py status
```

### Iniciar todas as câmeras

```bash
python main.py start
```

### Testar detecção com câmera do celular

```bash
python main.py test --image http://192.168.1.100:8080/video
```

---

## 📊 Exemplos de URL

```
# IP Webcam Android
http://192.168.1.100:8080/video

# Com autenticação
http://admin:password@192.168.1.100:8080/video

# Porta alternativa
http://192.168.1.100:8181/video

# CamTester iOS
http://192.168.1.101:5000/video
```

---

## 🎯 Dicas de Uso

### Para Melhor Qualidade

1. **Boa iluminação**: Use ambientes bem iluminados
2. **Estabilidade**: Deixe o celular em superfície fixa
3. **Distância**: 1-3 metros do objeto
4. **Ângulo**: Posicione frontal ou levemente acima

### Para Testar EPIs

1. **Capacete**: Use um capacete real ou similar
2. **Luvas**: Luvas de trabalho coloridas
3. **Óculos**: Óculos de segurança claros
4. **Colete**: Colete refletivo amarelo/laranja

### Simular Cenários

1. **Conforme**: Use todos os EPIs obrigatórios
2. **Não conforme**: Falte 1 ou mais EPIs
3. **Parcial**: Use apenas alguns EPIs

---

## ⚠️ Limitações

### Celular vs Câmera IP

| Característica | Celular | Câmera IP |
|---------------|---------|-----------|
| Custo | Baixo/grátis | Alto |
| Qualidade | Boa | Excelente |
| Latência | Média | Baixa |
| Confiabilidade | Média | Alta |
| Uso | Testes | Produção |

### Quando Usar Celular

✅ **Ideal para:**
- Testes iniciais
- Desenvolvimento
- Prototipagem
- Ambientes temporários

❌ **Não ideal para:**
- Produção 24/7
- Ambientes críticos
- Longos períodos
- Múltiplas câmeras

---

## 🆘 Troubleshooting Avançado

### Firewall do Windows

```powershell
# Adicionar regra ao firewall
New-NetFirewallRule -DisplayName "EPI System" -Direction Inbound -LocalPort 8080 -Protocol TCP -Action Allow
```

### Firewall do Mac

```bash
# Permitir conexões na porta 8080
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/bin/python3
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --unblockapp /usr/bin/python3
```

### Linux (UFW)

```bash
# Permitir porta 8080
sudo ufw allow 8080/tcp
```

---

## 📞 Suporte

Se ainda tiver problemas:

1. Verifique a [documentação principal](README.md)
2. Abra uma issue no GitHub
3. Consulte o FAQ no repositório

---

**Próximo passo**: [Testar o Modelo](TEST_MODEL.md) →
