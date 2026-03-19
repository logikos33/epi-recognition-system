"""
Camera Management Interface - User-friendly frontend for camera operations
"""
import streamlit as st
import cv2
import numpy as np
from datetime import datetime
import time

# Page configuration
st.set_page_config(
    page_title="Gerenciar Câmeras - EPI Recognition",
    page_icon="📹",
    layout="wide"
)

st.title("📹 Gerenciamento de Câmeras")
st.markdown("---")

# Session state for cameras
if 'cameras' not in st.session_state:
    st.session_state.cameras = {}

if 'camera_test_active' not in st.session_state:
    st.session_state.camera_test_active = False

if 'test_frame' not in st.session_state:
    st.session_state.test_frame = None


def add_camera(camera_id, name, location, source_url, source_type):
    """Add camera to session state"""
    st.session_state.cameras[camera_id] = {
        "id": camera_id,
        "name": name,
        "location": location,
        "source_url": source_url,
        "source_type": source_type,
        "is_active": False,
        "added_at": datetime.now()
    }


def test_camera_connection(source_url, source_type):
    """Test camera connection and return frame"""
    try:
        if source_type == "webcam":
            cap = cv2.VideoCapture(int(source_url))
        elif source_type == "rtsp":
            cap = cv2.VideoCapture(source_url)
        elif source_type == "http":
            cap = cv2.VideoCapture(source_url)
        else:
            return None, "Tipo de fonte não suportado"

        if not cap.isOpened():
            return None, "Não foi possível abrir a câmera"

        ret, frame = cap.read()
        cap.release()

        if not ret:
            return None, "Não foi possível capturar frame"

        return frame, "Conexão bem-sucedida!"

    except Exception as e:
        return None, f"Erro: {str(e)}"


# Sidebar - Adicionar Nova Câmera
with st.sidebar:
    st.header("➕ Adicionar Câmera")

    with st.form("add_camera_form"):
        camera_name = st.text_input("Nome da Câmera*", placeholder="Ex: Câmera Entrada Principal")

        camera_location = st.text_input(
            "Localização*",
            placeholder="Ex: Fábrica - Linha A"
        )

        source_type = st.selectbox(
            "Tipo de Fonte*",
            options=["webcam", "rtsp", "http"],
            help="""
            - **webcam**: Câmera conectada ao computador (0, 1, 2...)
            - **rtsp**: Câmera IP com protocolo RTSP
            - **http**: Stream HTTP (ex: app de celular)
            """
        )

        if source_type == "webcam":
            source_url_help = "Número da webcam (ex: 0 para webcam padrão)"
            source_url_placeholder = "0"
        elif source_type == "rtsp":
            source_url_help = "URL RTSP (ex: rtsp://192.168.1.100:554/stream)"
            source_url_placeholder = "rtsp://192.168.1.100:554/stream"
        else:  # http
            source_url_help = "URL HTTP do stream"
            source_url_placeholder = "http://192.168.1.100:8080/video"

        source_url = st.text_input(
            "URL/ID da Fonte*",
            placeholder=source_url_placeholder,
            help=source_url_help
        )

        submitted = st.form_submit_button("Adicionar Câmera", type="primary")

        if submitted:
            if not camera_name or not camera_location or not source_url:
                st.error("❌ Por favor, preencha todos os campos obrigatórios")
            else:
                camera_id = f"cam_{len(st.session_state.cameras) + 1}"
                add_camera(camera_id, camera_name, camera_location, source_url, source_type)
                st.success(f"✅ Câmera '{camera_name}' adicionada com sucesso!")
                st.rerun()

    st.markdown("---")

    # Testar conexão com câmera
    st.header("🧪 Testar Conexão")

    with st.form("test_camera_form"):
        test_type = st.selectbox(
            "Tipo de Câmera",
            options=["webcam", "http", "rtsp"],
            index=0
        )

        if test_type == "webcam":
            test_url = st.number_input("ID da Webcam", value=0, min_value=0, max_value=10)
        else:
            test_url = st.text_input(
                "URL da Câmera",
                placeholder="http://192.168.1.100:8080/video" if test_type == "http" else "rtsp://192.168.1.100:554/stream"
            )

        test_button = st.form_submit_button("Testar Conexão")

    if test_button:
        with st.spinner("Testando conexão..."):
            if test_type == "webcam":
                frame, message = test_camera_connection(str(int(test_url)), test_type)
            else:
                frame, message = test_camera_connection(test_url, test_type)

            if frame is not None:
                st.success(f"✅ {message}")
                st.session_state.test_frame = frame
                st.session_state.camera_test_active = True
            else:
                st.error(f"❌ {message}")
                st.session_state.camera_test_active = False

    # Instruções para celular
    st.markdown("---")
    st.header("📱 Câmera de Celular")

    with st.expander("Como usar câmera do celular"):
        st.markdown("""
        ### Opção 1: IP Webcam (Android)

        1. Instale o app **IP Webcam** no Android
        2. Abra o app e role para baixo até "Start Server"
        3. Anote o IP mostrado (ex: http://192.168.1.100:8080)
        4. Use a URL: `http://SEU_IP:8080/video`

        ### Opção 2: CamTester (iOS)

        1. Instale o app **CamTester** no iPhone
        2. Inicie o servidor de vídeo
        3. Use a URL HTTP fornecida

        ### Importante:
        - Celular e computador devem estar na **mesma rede Wi-Fi**
        - Verifique o firewall se não funcionar
        - Use o endereço IP local (não o IP externo)
        """)

# Main Content
col1, col2 = st.columns([2, 1])

with col1:
    st.header("📋 Câmeras Configuradas")

    if not st.session_state.cameras:
        st.info("🔍 Nenhuma câmera configurada. Use o formulário ao lado para adicionar.")
    else:
        # Display cameras
        for cam_id, cam in st.session_state.cameras.items():
            with st.container():
                col_a, col_b, col_c = st.columns([3, 2, 1])

                with col_a:
                    st.markdown(f"### 📹 {cam['name']}")
                    st.caption(f"📍 {cam['location']}")
                    st.caption(f"🔗 {cam['source_type']}: {cam['source_url']}")

                with col_b:
                    status = "🟢 Ativa" if cam['is_active'] else "⚪ Inativa"
                    st.metric("Status", status)
                    st.caption(f"Adicionada: {cam['added_at'].strftime('%d/%m %H:%M')}")

                with col_c:
                    if st.button("▶️ Ativar", key=f"start_{cam_id}", disabled=cam['is_active']):
                        cam['is_active'] = True
                        st.rerun()

                    if st.button("⏹️ Parar", key=f"stop_{cam_id}", disabled=not cam['is_active']):
                        cam['is_active'] = False
                        st.rerun()

                    if st.button("🗑️", key=f"delete_{cam_id}"):
                        del st.session_state.cameras[cam_id]
                        st.rerun()

                st.markdown("---")

with col2:
    st.header("📊 Resumo")

    total_cameras = len(st.session_state.cameras)
    active_cameras = sum(1 for cam in st.session_state.cameras.values() if cam['is_active'])

    st.metric("Total de Câmeras", total_cameras)
    st.metric("Câmeras Ativas", active_cameras)

    # Type distribution
    if st.session_state.cameras:
        types = {}
        for cam in st.session_state.cameras.values():
            cam_type = cam['source_type']
            types[cam_type] = types.get(cam_type, 0) + 1

        st.subheader("Por Tipo")
        for cam_type, count in types.items():
            st.write(f"📹 {cam_type.upper()}: {count}")

# Test frame display
if st.session_state.camera_test_active and st.session_state.test_frame is not None:
    st.markdown("---")
    st.header("📺 Preview da Câmera")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Frame Capturado")
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(st.session_state.test_frame, cv2.COLOR_BGR2RGB)
        st.image(frame_rgb, channels="RGB", use_column_width=True)

    with col2:
        st.subheader("Informações")
        height, width = st.session_state.test_frame.shape[:2]
        st.write(f"📐 Resolução: {width}x{height}")
        st.write(f"🎨 Canais: {st.session_state.test_frame.shape[2]}")
        st.write(f"💾 Tamanho: {st.session_state.test_frame.nbytes / 1024:.2f} KB")

        st.success("✅ Câmera funcionando corretamente!")

        if st.button("Adicionar esta câmera", type="primary"):
            # Add to cameras list
            camera_id = f"cam_test_{int(time.time())}"
            add_camera(
                camera_id,
                f"Câmera Teste {camera_id}",
                "Localização Teste",
                st.session_state.get('test_url', ''),
                st.session_state.get('test_type', 'webcam')
            )
            st.success("Câmera adicionada!")
            st.rerun()

# Quick Actions
st.markdown("---")
st.header("⚡ Ações Rápidas")

col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("▶️ Iniciar Todas", use_container_width=True):
        for cam in st.session_state.cameras.values():
            cam['is_active'] = True
        st.success("Todas as câmeras iniciadas!")
        st.rerun()

with col2:
    if st.button("⏹️ Parar Todas", use_container_width=True):
        for cam in st.session_state.cameras.values():
            cam['is_active'] = False
        st.success("Todas as câmeras paradas!")
        st.rerun()

with col3:
    if st.button("🧪 Testar Todas", use_container_width=True):
        st.info("Iniciando teste de todas as câmeras...")
        # Test logic would go here
        for cam_id, cam in st.session_state.cameras.items():
            frame, message = test_camera_connection(cam['source_url'], cam['source_type'])
            if frame is not None:
                st.success(f"✅ {cam['name']}: OK")
            else:
                st.error(f"❌ {cam['name']}: {message}")

with col4:
    if st.button("🗑️ Limpar Todas", use_container_width=True):
        if st.session_state.cameras:
            st.warning("Isso removerá todas as câmeras!")
            confirm = st.checkbox("Confirmar exclusão")
            if confirm:
                st.session_state.cameras = {}
                st.success("Todas as câmeras removidas!")
                st.rerun()

# Export configuration
st.markdown("---")
st.header("📥 Exportar/Importar Configuração")

col1, col2 = st.columns(2)

with col1:
    if st.button("📤 Exportar Configuração", use_container_width=True):
        import json
        config = {
            "cameras": st.session_state.cameras,
            "exported_at": datetime.now().isoformat()
        }
        st.download_button(
            label="Baixar cameras.json",
            data=json.dumps(config, indent=2, default=str),
            file_name="cameras_config.json",
            mime="application/json"
        )

with col2:
    uploaded_file = st.file_uploader("📥 Importar Configuração", type=["json"])
    if uploaded_file is not None:
        import json
        try:
            config = json.load(uploaded_file)
            st.session_state.cameras = config.get("cameras", {})
            st.success(f"✅ Configuração importada com sucesso!")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Erro ao importar: {str(e)}")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        <p>💡 Dica: Use câmeras de celular para testar facilmente!</p>
        <p>📱 Instale IP Webcam (Android) ou CamTester (iOS)</p>
    </div>
    """,
    unsafe_allow_html=True
)
