"""
Home Page - Landing page with navigation and quick actions
"""
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="EPI Recognition System",
    page_icon="⛑️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .hero {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 3rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .hero h1 {
        font-size: 3rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .feature-card {
        background: white;
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        height: 100%;
        transition: transform 0.3s;
    }
    .feature-card:hover {
        transform: translateY(-5px);
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: #667eea;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'page_history' not in st.session_state:
    st.session_state.page_history = []

# Hero Section
st.markdown("""
<div class="hero">
    <h1>⛑️ Sistema de Reconhecimento de EPI</h1>
    <p style="font-size: 1.2rem;">Monitoramento inteligente com Visão Computacional e Multi-Agentes</p>
</div>
""", unsafe_allow_html=True)

# Quick Stats
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("📹 Câmeras", "3", "+1 esta semana")

with col2:
    st.metric("✅ Taxa de Conformidade", "82.5%", "+2.3%")

with col3:
    st.metric("🔍 Detecções", "1,234", "+156 hoje")

with col4:
    st.metric("🚨 Alertas", "12", "5 não resolvidos")

st.markdown("---")

# Quick Actions
st.header("⚡ Ações Rápidas")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    if st.button("📹 Gerenciar Câmeras", type="primary", use_container_width=True):
        st.switch_page("pages/1_Camera_Management.py")

with col2:
    if st.button("📊 Dashboard", use_container_width=True):
        st.switch_page("pages/2_Dashboard.py")

with col3:
    if st.button("🚨 Alertas", use_container_width=True):
        st.switch_page("pages/3_Alerts.py")

with col4:
    if st.button("📈 Análises", use_container_width=True):
        st.switch_page("pages/4_Analytics.py")

with col5:
    if st.button("📜 Histórico", use_container_width=True):
        st.switch_page("pages/5_History.py")

st.markdown("---")

# Feature Cards
st.header("🎯 Funcionalidades")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="feature-card">
        <h3>📹 Gerenciamento de Câmeras</h3>
        <p>Adicione e configure múltiplas câmeras facilmente. Suporte para webcam, câmeras IP (RTSP) e câmeras de celular.</p>
        <ul>
            <li>✅ Detecção automática</li>
            <li>✅ Teste de conexão</li>
            <li>✅ Preview em tempo real</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
        <h3>🔍 Detecção de EPIs</h3>
        <p>Detecção automática de múltiplos EPIs usando YOLOv8:</p>
        <ul>
            <li>⛑️ Capacete</li>
            <li>🧤 Luvas</li>
            <li>🥽 Óculos</li>
            <li>🦺 Colete</li>
            <li>🥾 Botas</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="feature-card">
        <h3>📊 Relatórios e Análises</h3>
        <p>Dashboard completo com:</p>
        <ul>
            <li>📈 Métricas em tempo real</li>
            <li>🚨 Sistema de alertas</li>
            <li>📉 Tendências e análises</li>
            <li>📜 Histórico completo</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Getting Started
st.header("🚀 Começando Agora")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1️⃣ Configure suas Câmeras")
    st.info("""
    **Opções disponíveis:**
    - **Webcam**: Use a webcam do computador (ID: 0, 1, 2...)
    - **Câmera IP**: Configure câmeras RTSP (ex: câmeras de segurança)
    - **Celular**: Use o celular como câmera!

    **Para usar celular:**
    1. Android: Instale "IP Webcam"
    2. iOS: Instale "CamTester"
    3. Conecte na mesma rede Wi-Fi
    4. Use a URL HTTP fornecida
    """)

with col2:
    st.subheader("2️⃣ Teste a Conexão")
    st.success("""
    **Antes de iniciar:**
    1. Vá em "Gerenciar Câmeras"
    2. Adicione uma câmera
    3. Use "Testar Conexão" para verificar
    4. Veja o preview ao vivo

    **Se funcionar:**
    ✅ A câmera está pronta para uso
    ✅ Você pode ver o frame capturado
    ✅ Inicie o monitoramento
    """)

st.markdown("---")

# System Status
st.header("💻 Status do Sistema")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🟢 Sistema")
    st.write("✅ Operacional")
    st.caption("Uptime: 2h 34m")

with col2:
    st.markdown("### 📹 Câmeras")
    st.write("2 de 3 ativas")
    st.caption("Câmera 1: Ativa")
    st.caption("Câmera 2: Ativa")
    st.caption("Câmera 3: Inativa")

with col3:
    st.markdown("### 💾 Database")
    st.write("✅ Conectado")
    st.caption("PostgreSQL: localhost")
    st.caption("1,234 detecções")

st.markdown("---")

# Recent Activity
st.header("🕐 Atividade Recente")

activity_data = [
    {"time": "14:32", "event": "Detecção não conforme", "camera": "Câmera 1", "status": "alert"},
    {"time": "14:30", "event": "Câmera iniciada", "camera": "Câmera 2", "status": "info"},
    {"time": "14:25", "event": "Detecção conforme", "camera": "Câmera 1", "status": "success"},
    {"time": "14:20", "event": "Alerta resolvido", "camera": "Câmera 3", "status": "success"},
    {"time": "14:15", "event": "Nova câmera adicionada", "camera": "Câmera 3", "status": "info"},
]

for activity in activity_data:
    status_icon = {
        "alert": "🚨",
        "info": "ℹ️",
        "success": "✅"
    }

    status_color = {
        "alert": "red",
        "info": "blue",
        "success": "green"
    }

    st.markdown(
        f"""
        <div style='border-left: 3px solid {status_color[activity["status"]]}; padding-left: 10px; margin-bottom: 10px;'>
            <p><strong>{status_icon[activity["status"]]} {activity["event"]}</strong></p>
            <p style='color: #666; font-size: 0.9em;'>📹 {activity["camera"]} | 🕐 {activity["time"]}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("---")

# Documentation Links
st.header("📚 Documentação")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("[📖 README](README.md)")
    st.caption("Documentação principal")

with col2:
    st.markdown("[🔧 Configuração](requirements.txt)")
    st.caption("Dependências")

with col3:
    st.markdown("[🧪 Testes](tests/)")
    st.caption("Suite de testes")

with col4:
    st.markdown("[🐛 Issues](https://github.com)")
    st.caption("Reportar bugs")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; padding: 2rem;'>
        <p><strong>EPI Recognition System</strong> v1.0.0</p>
        <p>Desenvolvido com ❤️ para melhorar a segurança no trabalho</p>
        <p style='font-size: 0.9em;'>Última atualização: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
    </div>
    """,
    unsafe_allow_html=True
)
