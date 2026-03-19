#!/bin/bash

# Script para configurar repositório no GitHub
# EPI Recognition System

echo "🚀 Configurando repositório GitHub para EPI Recognition System"
echo "================================================================"

# Verificar se gh CLI está instalado
if ! command -v gh &> /dev/null; then
    echo "⚠️  GitHub CLI não encontrado. Instale com: brew install gh (Mac) ou apt install gh (Linux)"
    echo ""
    echo "Instruções manuais:"
    echo "1. Vá para https://github.com/new"
    echo "2. Crie um repositório chamado 'epi-recognition-system'"
    echo "3. Execute os comandos abaixo:"
    echo ""
    echo "   git remote add origin https://github.com/SEU_USUARIO/epi-recognition-system.git"
    echo "   git branch -M main"
    echo "   git push -u origin main"
    echo ""
    exit 1
fi

# Criar repositório no GitHub
echo "📦 Criando repositório no GitHub..."
gh repo create epi-recognition-system \
    --public \
    --description "Sistema de Reconhecimento de EPI com Visão Computacional e Multi-Agentes" \
    --source=. \
    --remote=origin \
    --push

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Sucesso! Repositório criado e código enviado!"
    echo ""
    echo "📂 URL do repositório:"
    gh repo view --web
else
    echo ""
    echo "⚠️  Ocorreu um erro. Tentando método alternativo..."
    echo ""
    echo "Por favor, execute manualmente:"
    echo "1. Crie o repositório em https://github.com/new"
    echo "2. Execute:"
    echo "   git remote add origin https://github.com/SEU_USUARIO/epi-recognition-system.git"
    echo "   git branch -M main"
    echo "   git push -u origin main"
fi
