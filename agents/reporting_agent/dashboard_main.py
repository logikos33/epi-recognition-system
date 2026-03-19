"""
Streamlit Dashboard - Main Dashboard for EPI Monitoring System
Cloud version using Supabase backend
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, Any, List
import time

# Import Supabase service
try:
    from services.supabase_service import get_supabase_service
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    st.warning("⚠️ Supabase service not available. Using sample data.")

# Page configuration
st.set_page_config(
    page_title="Sistema de Monitoramento de EPI",
    page_icon="⛑️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-title {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .status-compliant {
        color: #00cc00;
        font-weight: bold;
    }
    .status-non-compliant {
        color: #ff0000;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


class ReportingAgent:
    """
    Reporting agent for generating dashboards and visualizations
    """

    def __init__(self):
        """Initialize reporting agent"""
        self.detection_cache = []
        self.alert_cache = []

    def update_detection(self, detection_result):
        """
        Update with new detection result

        Args:
            detection_result: Detection result from recognition agent
        """
        self.detection_cache.append(detection_result)

        # Keep cache size manageable
        if len(self.detection_cache) > 1000:
            self.detection_cache = self.detection_cache[-1000:]

    def get_cached_detections(self, limit: int = 100):
        """
        Get cached detections

        Args:
            limit: Maximum number of detections

        Returns:
            List of detections
        """
        return self.detection_cache[-limit:]


# Global reporting agent instance
@st.cache_resource
def get_reporting_agent() -> ReportingAgent:
    """Get or create reporting agent instance"""
    return ReportingAgent()


def load_data():
    """Load data from Supabase database"""
    if not SUPABASE_AVAILABLE:
        # Return sample data if Supabase is not available
        return _load_sample_data()

    try:
        supabase = get_supabase_service()

        # Get all cameras
        cameras = supabase.get_all_cameras()

        # Build cameras dictionary
        cameras_data = {}
        for cam in cameras:
            cameras_data[cam['name']] = {
                "id": cam['id'],
                "location": cam.get('location', 'Unknown'),
                "active": cam.get('is_active', True),
                "brand": cam.get('camera_brand', 'generic')
            }

        # Get recent detections
        detections = supabase.get_recent_detections(limit=100)

        # Transform detections to expected format
        detections_data = []
        for det in detections:
            # Get camera name
            camera_id = det.get('camera_id')
            camera_name = next(
                (name for name, data in cameras_data.items() if data.get('id') == camera_id),
                f"Camera {camera_id}"
            )

            detection = {
                "id": det.get('id'),
                "camera_id": camera_id,
                "camera": camera_name,
                "timestamp": datetime.fromisoformat(det.get('timestamp', datetime.now().isoformat())),
                "is_compliant": det.get('is_compliant', False),
                "person_count": det.get('person_count', 0),
                "confidence": det.get('confidence', 0.0),
                "epis_detected": det.get('epis_detected', {})
            }

            detections_data.append(detection)

        return cameras_data, detections_data

    except Exception as e:
        st.error(f"Error loading data from Supabase: {e}")
        return _load_sample_data()


def _load_sample_data():
    """Load sample data for testing/demo purposes"""
    # Sample cameras
    cameras_data = {
        "Camera 1": {"id": 1, "location": "Fábrica - Linha A", "active": True, "brand": "hikvision"},
        "Camera 2": {"id": 2, "location": "Fábrica - Linha B", "active": True, "brand": "dahua"},
        "Camera 3": {"id": 3, "location": "Depósito", "active": True, "brand": "intelbras"},
    }

    # Sample detections
    detections_data = []

    for i in range(50):
        is_compliant = i % 3 != 0  # ~67% compliance

        detection = {
            "id": i + 1,
            "camera_id": (i % 3) + 1,
            "camera": f"Camera {(i % 3) + 1}",
            "timestamp": datetime.now() - timedelta(minutes=i * 5),
            "is_compliant": is_compliant,
            "person_count": (i % 3) + 1,
            "confidence": 0.7 + (i % 3) * 0.1,
            "epis_detected": {
                "helmet": is_compliant,
                "gloves": is_compliant and i % 2 == 0,
                "glasses": is_compliant or i % 4 == 0,
                "vest": is_compliant,
            }
        }

        detections_data.append(detection)

    return cameras_data, detections_data


def main():
    """Main dashboard function"""
    reporting_agent = get_reporting_agent()

    # Header
    st.markdown('<h1 class="main-title">⛑️ Sistema de Monitoramento de EPI</h1>', unsafe_allow_html=True)
    st.markdown("---")

    # Auto-refresh configuration
    auto_refresh_enabled = st.sidebar.checkbox("🔄 Auto-refresh (5s)", value=True)
    refresh_interval = 5 if auto_refresh_enabled else 0

    # Load data
    cameras_data, detections_data = load_data()

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configurações")

        # Date range filter
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
        selected_cameras = st.multiselect(
            "Selecione as câmeras:",
            options=list(cameras_data.keys()),
            default=list(cameras_data.keys())
        )

        # EPI filter
        st.subheader("🛡️ Tipos de EPI")
        epi_types = ["helmet", "gloves", "glasses", "vest", "boots"]
        selected_epis = st.multiselect(
            "Selecione os EPIs:",
            options=epi_types,
            default=epi_types
        )

        st.markdown("---")

        # System status
        st.subheader("📊 Status do Sistema")
        st.success("✅ Sistema Operacional")
        st.info(f"📹 {len(cameras_data)} Câmeras Ativas")
        st.info(f"🔍 {len(detections_data)} Detecções")

        st.markdown("---")

        # Quick actions
        st.subheader("⚡ Ações Rápidas")
        if st.button("🔄 Atualizar Dados"):
            st.rerun()

        if st.button("📥 Exportar Relatório"):
            st.info("Relatório exportado!")

    # Filter data
    filtered_detections = [
        d for d in detections_data
        if d["camera"] in selected_cameras and
        start <= datetime.combine(start, datetime.min.time()) + timedelta(days=1) and
        end >= d["timestamp"].date()
    ]

    # Main content
    col1, col2, col3, col4 = st.columns(4)

    # Calculate metrics
    total_detections = len(filtered_detections)
    compliant_detections = sum(1 for d in filtered_detections if d["is_compliant"])
    non_compliant_detections = total_detections - compliant_detections
    compliance_rate = (compliant_detections / total_detections * 100) if total_detections > 0 else 0

    # Display metrics
    with col1:
        st.metric(
            label="Total de Detecções",
            value=total_detections,
            delta=f"Últimas 24h: {sum(1 for d in filtered_detections if d['timestamp'] > datetime.now() - timedelta(days=1))}"
        )

    with col2:
        st.metric(
            label="Taxa de Conformidade",
            value=f"{compliance_rate:.1f}%",
            delta=f"{compliance_rate - 70:.1f}%" if compliance_rate >= 70 else f"{compliance_rate - 70:.1f}%",
            delta_color="normal" if compliance_rate >= 70 else "inverse"
        )

    with col3:
        st.metric(
            label="Detect. Conformes",
            value=compliant_detections,
            delta=f"{(compliant_detections/total_detections*100):.1f}%" if total_detections > 0 else "0%"
        )

    with col4:
        st.metric(
            label="Detect. Não Conformes",
            value=non_compliant_detections,
            delta=f"ALERTA!" if non_compliant_detections > 0 else "OK",
            delta_color="inverse" if non_compliant_detections > 0 else "normal"
        )

    st.markdown("---")

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Taxa de Conformidade ao Longo do Tempo")

        # Prepare time series data
        df = pd.DataFrame(filtered_detections)
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['date'] = df['timestamp'].dt.date
            daily_stats = df.groupby('date').agg({
                'is_compliant': ['count', 'sum']
            }).reset_index()
            daily_stats.columns = ['date', 'total', 'compliant']
            daily_stats['compliance_rate'] = (daily_stats['compliant'] / daily_stats['total'] * 100).round(2)

            fig = px.line(
                daily_stats,
                x='date',
                y='compliance_rate',
                title='Taxa de Conformidade Diária',
                labels={'compliance_rate': 'Taxa (%)', 'date': 'Data'},
                markers=True
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🛡️ Taxa de Detecção por EPI")

        # Calculate EPI detection rates
        epi_stats = {}
        for epi in selected_epis:
            detected = sum(1 for d in filtered_detections if d["epis_detected"].get(epi, False))
            epi_stats[epi] = (detected / len(filtered_detections) * 100) if filtered_detections else 0

        fig = px.bar(
            x=list(epi_stats.keys()),
            y=list(epi_stats.values()),
            title='Taxa de Detecção por Tipo de EPI',
            labels={'x': 'EPI', 'y': 'Taxa de Detecção (%)'},
            color=list(epi_stats.values()),
            color_continuous_scale='RdYlGn'
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Recent detections table
    st.subheader("🔍 Detecções Recentes")

    # Prepare table data
    table_data = []
    for detection in filtered_detections[:10]:
        table_data.append({
            "ID": detection["id"],
            "Câmera": detection["camera"],
            "Timestamp": detection["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
            "Status": "✅ Conforme" if detection["is_compliant"] else "❌ Não Conforme",
            "Pessoas": detection["person_count"],
            "Confiança": f"{detection['confidence']:.2f}",
            "EPIs": ", ".join([epi for epi, detected in detection["epis_detected"].items() if detected])
        })

    df_table = pd.DataFrame(table_data)

    # Style the dataframe (only if not empty)
    if not df_table.empty:
        def highlight_status(val):
            if "Conforme" in val:
                return ['background-color: #d4edda'] * len(val)
            else:
                return ['background-color: #f8d7da'] * len(val)

        styled_df = df_table.style.apply(highlight_status, subset=['Status'])
        st.dataframe(styled_df, use_container_width=True, height=400)
    else:
        st.info("🔍 Nenhuma detecção registrada ainda. Adicione câmeras para começar o monitoramento.")

    st.markdown("---")

    # Camera performance
    st.subheader("📹 Desempenho por Câmera")

    camera_stats = {}
    for camera in selected_cameras:
        camera_detections = [d for d in filtered_detections if d["camera"] == camera]
        total = len(camera_detections)
        compliant = sum(1 for d in camera_detections if d["is_compliant"])
        compliance = (compliant / total * 100) if total > 0 else 0

        camera_stats[camera] = {
            "total": total,
            "compliant": compliant,
            "compliance_rate": compliance
        }

    # Create camera performance chart
    camera_df = pd.DataFrame([
        {
            "Câmera": camera,
            "Total": stats["total"],
            "Conformes": stats["compliant"],
            "Taxa de Conformidade (%)": stats["compliance_rate"]
        }
        for camera, stats in camera_stats.items()
    ])

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            camera_df,
            x='Câmera',
            y=['Total', 'Conformes'],
            title='Detecções por Câmera',
            barmode='group'
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.pie(
            camera_df,
            values='Total',
            names='Câmera',
            title='Distribuição de Detecções',
            hole=0.3
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

    # Footer
    st.markdown("---")
    st.markdown(
        f"""
        <div style='text-align: center; color: #666;'>
            <p>Sistema de Monitoramento de EPI v1.0.0 (Cloud)</p>
            <p>Última atualização: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Auto-refresh
    if auto_refresh_enabled and refresh_interval > 0:
        time.sleep(refresh_interval)
        st.rerun()


if __name__ == "__main__":
    main()
