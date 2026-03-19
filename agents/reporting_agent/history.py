"""
Streamlit History Page - Historical Detection Data
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(
    page_title="Histórico - Sistema de Monitoramento de EPI",
    page_icon="📜",
    layout="wide"
)

st.title("📜 Histórico de Detecções")
st.markdown("---")


def load_history_data():
    """Load historical detection data (placeholder)"""
    # Sample historical data
    detections = []

    for i in range(100):
        is_compliant = i % 3 != 0  # ~67% compliance

        detection = {
            "id": i + 1,
            "camera": f"Camera {(i % 3) + 1}",
            "timestamp": datetime.now() - timedelta(hours=i, minutes=(i % 4) * 15),
            "is_compliant": is_compliant,
            "person_count": (i % 4) + 1,
            "confidence": 0.65 + (i % 4) * 0.1,
            "epis_detected": {
                "helmet": is_compliant,
                "gloves": is_compliant and i % 2 == 0,
                "glasses": is_compliant or i % 4 == 0,
                "vest": is_compliant,
                "boots": True
            },
            "image_path": f"/storage/images/detection_{i + 1}.jpg" if is_compliant else f"/storage/images/violation_{i + 1}.jpg",
            "location": ["Fábrica - Linha A", "Fábrica - Linha B", "Depósito"][i % 3]
        }

        detections.append(detection)

    return detections


def main():
    """Main history page"""
    # Load data
    detections = load_history_data()

    # Sidebar filters
    with st.sidebar:
        st.header("🔍 Filtros")

        # Date range
        st.subheader("📅 Período")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        col1, col2 = st.columns(2)
        with col1:
            start = st.date_input("De:", start_date.date())
        with col2:
            end = st.date_input("Até:", end_date.date())

        # Camera filter
        st.subheader("📹 Câmeras")
        cameras = list(set(d["camera"] for d in detections))
        selected_cameras = st.multiselect(
            "Selecione as câmeras:",
            options=cameras,
            default=cameras
        )

        # Compliance filter
        st.subheader("✅ Status de Conformidade")
        compliance_filter = st.selectbox(
            "Filtrar por:",
            options=["Todos", "Apenas Conformes", "Apenas Não Conformes"],
            index=0
        )

        # Person count filter
        st.subheader("👥 Número de Pessoas")
        min_persons = st.slider("Mínimo:", 0, 10, 0)
        max_persons = st.slider("Máximo:", 1, 10, 10)

        # Confidence filter
        st.subheader("📊 Confiança da Detecção")
        min_confidence = st.slider("Mínima:", 0.0, 1.0, 0.5, 0.05)

        st.markdown("---")

        # Quick statistics
        st.subheader("📊 Estatísticas do Período")

        filtered_count = len([
            d for d in detections
            if start <= d["timestamp"].date() <= end
        ])

        st.metric("Detecções no Período", filtered_count)

        st.markdown("---")

        # Export
        st.subheader("📥 Exportar")
        export_format = st.selectbox("Formato:", options=["CSV", "JSON", "Excel"])

        if st.button("Exportar Dados"):
            st.success(f"Dados exportados em formato {export_format}!")

    # Apply filters
    filtered_detections = []

    for detection in detections:
        # Date filter
        if not (start <= detection["timestamp"].date() <= end):
            continue

        # Camera filter
        if detection["camera"] not in selected_cameras:
            continue

        # Compliance filter
        if compliance_filter == "Apenas Conformes" and not detection["is_compliant"]:
            continue
        if compliance_filter == "Apenas Não Conformes" and detection["is_compliant"]:
            continue

        # Person count filter
        if not (min_persons <= detection["person_count"] <= max_persons):
            continue

        # Confidence filter
        if detection["confidence"] < min_confidence:
            continue

        filtered_detections.append(detection)

    # Statistics
    col1, col2, col3, col4 = st.columns(4)

    total = len(filtered_detections)
    compliant = sum(1 for d in filtered_detections if d["is_compliant"])
    non_compliant = total - compliant
    compliance_rate = (compliant / total * 100) if total > 0 else 0

    with col1:
        st.metric("Total de Detecções", total)

    with col2:
        st.metric("Detect. Conformes", compliant, f"{compliance_rate:.1f}%")

    with col3:
        st.metric("Detect. Não Conformes", non_compliant, delta_color="inverse")

    with col4:
        avg_confidence = sum(d["confidence"] for d in filtered_detections) / total if total > 0 else 0
        st.metric("Confiança Média", f"{avg_confidence:.2f}")

    st.markdown("---")

    # Search functionality
    st.subheader("🔍 Busca Avançada")

    col1, col2, col3 = st.columns(3)

    with col1:
        search_id = st.text_input("Buscar por ID:")

    with col2:
        search_location = st.text_input("Buscar por Local:")

    with col3:
        epi_filter = st.multiselect(
            "Filtrar por EPI:",
            options=["helmet", "gloves", "glasses", "vest", "boots"],
            default=[]
        )

    # Apply search filters
    if search_id:
        filtered_detections = [
            d for d in filtered_detections
            if str(d["id"]) == search_id
        ]

    if search_location:
        filtered_detections = [
            d for d in filtered_detections
            if search_location.lower() in d["location"].lower()
        ]

    if epi_filter:
        filtered_detections = [
            d for d in filtered_detections
            if all(d["epis_detected"].get(epi, False) for epi in epi_filter)
        ]

    st.markdown("---")

    # Data table
    st.subheader("📋 Tabela de Detecções")

    # Prepare table data
    table_data = []
    for detection in filtered_detections:
        epis = ", ".join([
            epi for epi, detected in detection["epis_detected"].items()
            if detected
        ])

        table_data.append({
            "ID": detection["id"],
            "Data/Hora": detection["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
            "Câmera": detection["camera"],
            "Local": detection["location"],
            "Status": "✅ Conforme" if detection["is_compliant"] else "❌ Não Conforme",
            "Pessoas": detection["person_count"],
            "Confiança": f"{detection['confidence']:.2f}",
            "EPIs Detectados": epis,
            "Imagem": "📷 Ver"
        })

    # Pagination
    page_size = 20
    page = st.number_input("Página:", min_value=1, value=1)

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size

    paginated_data = table_data[start_idx:end_idx]

    # Display table
    if paginated_data:
        df = pd.DataFrame(paginated_data)

        # Style dataframe
        def highlight_status(val):
            if "Conforme" in val:
                return ['background-color: #d4edda'] * len(val)
            else:
                return ['background-color: #f8d7da'] * len(val)

        styled_df = df.style.apply(highlight_status, subset=['Status'])
        st.dataframe(styled_df, use_container_width=True, height=600)

        # Page info
        total_pages = (len(table_data) // page_size) + 1
        st.caption(f"Página {page} de {total_pages} (Total: {len(table_data)} registros)")

    else:
        st.info("Nenhuma detecção encontrada com os filtros selecionados.")

    st.markdown("---")

    # Detail view
    st.subheader("🔍 Detalhes da Detecção")

    detection_id = st.number_input("ID da Detecção:", min_value=1, value=1, step=1)

    if st.button("Ver Detalhes"):
        detection = next((d for d in detections if d["id"] == detection_id), None)

        if detection:
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown("### Informações Gerais")
                st.json({
                    "ID": detection["id"],
                    "Câmera": detection["camera"],
                    "Local": detection["location"],
                    "Timestamp": detection["timestamp"].isoformat(),
                    "Status": "Conforme" if detection["is_compliant"] else "Não Conforme",
                    "Número de Pessoas": detection["person_count"],
                    "Confiança": f"{detection['confidence']:.2f}"
                })

            with col2:
                st.markdown("### EPIs Detectados")

                for epi, detected in detection["epis_detected"].items():
                    status = "✅ Detectado" if detected else "❌ Não Detectado"
                    st.markdown(f"**{epi.capitalize()}:** {status}")

                st.markdown("---")
                st.markdown("### Imagem")
                st.info(f"📷 Caminho: {detection['image_path']}")
                st.caption("Nota: Visualização de imagem será implementada com integração do banco de imagens")

        else:
            st.warning(f"Detecção com ID {detection_id} não encontrada.")

    st.markdown("---")

    # Timeline view
    st.subheader("📈 Linha do Tempo")

    # Group by date
    from collections import defaultdict

    timeline_data = defaultdict(lambda: {"total": 0, "compliant": 0})

    for detection in filtered_detections:
        date = detection["timestamp"].date()
        timeline_data[date]["total"] += 1
        if detection["is_compliant"]:
            timeline_data[date]["compliant"] += 1

    # Display timeline
    if timeline_data:
        timeline_df = pd.DataFrame([
            {
                "Data": date,
                "Total": stats["total"],
                "Conformes": stats["compliant"],
                "Taxa de Conformidade (%)": (stats["compliant"] / stats["total"] * 100) if stats["total"] > 0 else 0
            }
            for date, stats in sorted(timeline_data.items())
        ])

        st.dataframe(timeline_df, use_container_width=True)

    else:
        st.info("Nenhum dado disponível para o período selecionado.")


if __name__ == "__main__":
    main()
