#!/bin/bash

# Script de Setup Inicial - EPI Recognition System

echo "🚀 EPI Recognition System - Setup Inicial"
echo "=========================================="
echo ""

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Função para printar sucesso
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Função para printar warning
print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Função para printar erro
print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 1. Verificar Python
echo "1️⃣  Verificando Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python encontrado: $PYTHON_VERSION"
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version | cut -d' ' -f2)
    print_success "Python encontrado: $PYTHON_VERSION"
    PYTHON_CMD=python
else
    print_error "Python não encontrado!"
    echo "Instale Python 3.8+ em https://www.python.org/downloads/"
    exit 1
fi

# 2. Criar ambiente virtual
echo ""
echo "2️⃣  Criando ambiente virtual..."
if [ -d "venv" ]; then
    print_warning "Ambiente virtual já existe"
else
    $PYTHON_CMD -m venv venv
    if [ $? -eq 0 ]; then
        print_success "Ambiente virtual criado"
    else
        print_error "Falha ao criar ambiente virtual"
        exit 1
    fi
fi

# 3. Ativar ambiente virtual
echo ""
echo "3️⃣  Ativando ambiente virtual..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi
print_success "Ambiente virtual ativado"

# 4. Instalar dependências
echo ""
echo "4️⃣  Instalando dependências..."
pip install --upgrade pip
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    print_success "Dependências instaladas"
else
    print_error "Falha ao instalar dependências"
    exit 1
fi

# 5. Criar arquivo .env
echo ""
echo "5️⃣  Configurando variáveis de ambiente..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    print_success ".env criado (edite conforme necessário)"
else
    print_warning ".env já existe"
fi

# 6. Criar diretórios de armazenamento
echo ""
echo "6️⃣  Criando diretórios..."
mkdir -p storage/images
mkdir -p storage/annotated
mkdir -p storage/reports
mkdir -p storage/test_images
print_success "Diretórios criados"

# 7. Executar teste rápido
echo ""
echo "7️⃣  Executando teste rápido..."
$PYTHON_CMD quick_test.py

# 8. Instruções finais
echo ""
echo "=========================================="
echo "🎉 Setup Completo!"
echo "=========================================="
echo ""
echo "Próximos passos:"
echo ""
echo "1️⃣  Testar com webcam:"
echo "   $PYTHON_CMD main.py camera --camera-id 0 --duration 30"
echo ""
echo "2️⃣  Configurar câmera de celular:"
echo "   Veja o guia: docs/CAMERA_SETUP.md"
echo ""
echo "3️⃣  Abrir o dashboard:"
echo "   $PYTHON_CMD main.py dashboard"
echo ""
echo "4️⃣  Ver status do sistema:"
echo "   $PYTHON_CMD main.py status"
echo ""
echo "📚 Documentação disponível em:"
echo "   - README.md (visão geral)"
echo "   - docs/CAMERA_SETUP.md (câmeras de celular)"
echo "   - docs/TEST_MODEL.md (testar modelo)"
echo ""
echo "=========================================="
