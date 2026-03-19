"""
Streamlit Analytics Page - Detailed Analysis and Trends
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(
    page_title="Análise - Sistema de Monitoramento de EPI",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Análise e Tendências")
st.markdown("---")


def load_analytics_data():
    """Load analytics data (placeholder)"""
    # Sample data for analytics

    # Time series data
    dates = pd.date_range(end=datetime.now(), periods=30, freq='D')

    time_series = []
    for date in dates:
        time_series.append({
            "date": date,
            "total_detections": 50 + (date.day % 20),
            "compliant_detections": 40 + (date.day % 15),
            "compliance_rate": 80 + (date.day % 10)
        })

    # Hourly pattern data
    hourly_data = []
    for hour in range(24):
        hourly_data.append({
            "hour": hour,
            "detections": 10 + (hour % 12) * 5,
            "compliance_rate": 70 + (hour % 8) * 3
        })

    # EPI analysis
    epi_analysis = {
        "helmet": {"detected": 850, "total": 1000, "rate": 85.0},
        "gloves": {"detected": 780, "total": 1000, "rate": 78.0},
        "glasses": {"detected": 620, "total": 1000, "rate": 62.0},
        "vest": {"detected": 900, "total": 1000, "rate": 90.0},
        "boots": {"detected": 950, "total": 1000, "rate": 95.0}
    }

    return time_series, hourly_data, epi_analysis


def main():
    """Main analytics page"""
    # Load data
    time_series, hourly_data, epi_analysis = load_analytics_data()

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configurações de Análise")

        # Time period
        time_period = st.selectbox(
            "Período:",
            options=["Últimos 7 dias", "Últimos 30 dias", "Últimos 90 dias", "Personalizado"],
            index=1
        )

        # Analysis type
        analysis_type = st.multiselect(
            "Tipo de Análise:",
            options=["Tendência Temporal", "Padrões Horários", "Análise por EPI", "Comparativo"],
            default=["Tendência Temporal", "Padrões Horários", "Análise por EPI"]
        )

        # Metrics
        metrics = st.multiselect(
            "Métricas:",
            options=["Taxa de Conformidade", "Volume de Detecções", "EPIs Detectados", "Alertas"],
            default=["Taxa de Conformidade", "Volume de Detecções"]
        )

        st.markdown("---")

        # Export options
        st.subheader("📥 Exportar")
        export_format = st.selectbox("Formato:", options=["CSV", "JSON", "PDF"])

        if st.button("Exportar Análise"):
            st.success(f"Análise exportada em formato {export_format}!")

    # Time Series Analysis
    if "Tendência Temporal" in analysis_type:
        st.subheader("📈 Tendência Temporal")

        df_time = pd.DataFrame(time_series)

        col1, col2 = st.columns(2)

        with col1:
            fig = px.line(
                df_time,
                x='date',
                y='compliance_rate',
                title='Taxa de Conformidade ao Longo do Tempo',
                labels={'compliance_rate': 'Taxa (%)', 'date': 'Data'}
            )
            fig.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="Meta: 80%")
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.bar(
                df_time,
                x='date',
                y=['total_detections', 'compliant_detections'],
                title='Volume de Detecções',
                labels={'value': 'Quantidade', 'date': 'Data', 'variable': 'Tipo'},
                barmode='group'
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

        # Statistics
        st.markdown("**Estatísticas do Período:**")

        col1, col2, col3, col4 = st.columns(4)

        avg_compliance = df_time['compliance_rate'].mean()
        max_compliance = df_time['compliance_rate'].max()
        min_compliance = df_time['compliance_rate'].min()
        total_detections = df_time['total_detections'].sum()

        with col1:
            st.metric("Média de Conformidade", f"{avg_compliance:.1f}%")

        with col2:
            st.metric("Máxima de Conformidade", f"{max_compliance:.1f}%")

        with col3:
            st.metric("Mínima de Conformidade", f"{min_compliance:.1f}%")

        with col4:
            st.metric("Total de Detecções", total_detections)

    st.markdown("---")

    # Hourly Pattern Analysis
    if "Padrões Horários" in analysis_type:
        st.subheader("🕐 Padrões Horários")

        df_hourly = pd.DataFrame(hourly_data)

        col1, col2 = st.columns(2)

        with col1:
            fig = px.line(
                df_hourly,
                x='hour',
                y='detections',
                title='Detecções por Hora do Dia',
                labels={'detections': 'Quantidade', 'hour': 'Hora'},
                markers=True
            )
            fig.update_layout(height=350, xaxis=dict(tickmode='linear', dtick=2))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.line(
                df_hourly,
                x='hour',
                y='compliance_rate',
                title='Taxa de Conformidade por Hora',
                labels={'compliance_rate': 'Taxa (%)', 'hour': 'Hora'},
                markers=True,
                line_color='orange'
            )
            fig.update_layout(height=350, xaxis=dict(tickmode='linear', dtick=2))
            st.plotly_chart(fig, use_container_width=True)

        # Insights
        st.info("💡 **Insight:** A taxa de conformidade tende a ser menor nos horários de pico (10-12h e 14-16h)")

    st.markdown("---")

    # EPI Analysis
    if "Análise por EPI" in analysis_type:
        st.subheader("🛡️ Análise por Tipo de EPI")

        # Prepare EPI data
        epi_data = []
        for epi, stats in epi_analysis.items():
            epi_data.append({
                "EPI": epi,
                "Detectado": stats["detected"],
                "Total": stats["total"],
                "Taxa de Detecção (%)": stats["rate"]
            })

        df_epi = pd.DataFrame(epi_data)

        col1, col2 = st.columns(2)

        with col1:
            fig = px.bar(
                df_epi,
                x='EPI',
                y='Taxa de Detecção (%)',
                title='Taxa de Detecção por EPI',
                labels={'EPI': 'Tipo de EPI', 'Taxa de Detecção (%)': 'Taxa (%)'},
                color='Taxa de Detecção (%)',
                color_continuous_scale='RdYlGn'
            )
            fig.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="Meta: 80%")
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.pie(
                df_epi,
                values='Detectado',
                names='EPI',
                title='Distribuição de EPIs Detectados',
                hole=0.3
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

        # EPI Details Table
        st.markdown("**Detalhes por EPI:**")

        # Add status column
        df_epi['Status'] = df_epi['Taxa de Detecção (%)'].apply(
            lambda x: '✅ Acima da Meta' if x >= 80 else '⚠️ Abaixo da Meta'
        )

        st.dataframe(
            df_epi[['EPI', 'Detectado', 'Total', 'Taxa de Detecção (%)', 'Status']],
            use_container_width=True
        )

    st.markdown("---")

    # Comparative Analysis
    if "Comparativo" in analysis_type:
        st.subheader("📊 Análise Comparativa")

        # Sample comparison data
        comparison_data = {
            "Período Atual": {
                "taxa_conformidade": 82.5,
                "total_deteccoes": 1450,
                "alertas": 45
            },
            "Período Anterior": {
                "taxa_conformidade": 78.3,
                "total_deteccoes": 1320,
                "alertas": 62
            }
        }

        col1, col2, col3 = st.columns(3)

        with col1:
            current = comparison_data["Período Atual"]["taxa_conformidade"]
            previous = comparison_data["Período Anterior"]["taxa_conformidade"]
            delta = current - previous

            st.metric(
                "Taxa de Conformidade",
                f"{current:.1f}%",
                f"{delta:+.1f}% vs período anterior",
                delta_color="normal" if delta >= 0 else "inverse"
            )

        with col2:
            current = comparison_data["Período Atual"]["total_deteccoes"]
            previous = comparison_data["Período Anterior"]["total_deteccoes"]
            delta = current - previous
            delta_pct = (delta / previous * 100) if previous > 0 else 0

            st.metric(
                "Total de Detecções",
                current,
                f"{delta_pct:+.1f}% vs período anterior",
                delta_color="normal" if delta >= 0 else "inverse"
            )

        with col3:
            current = comparison_data["Período Atual"]["alertas"]
            previous = comparison_data["Período Anterior"]["alertas"]
            delta = current - previous
            delta_pct = (delta / previous * 100) if previous > 0 else 0

            st.metric(
                "Alertas",
                current,
                f"{delta_pct:+.1f}% vs período anterior",
                delta_color="inverse" if delta > 0 else "normal"
            )

        # Comparison chart
        st.markdown("**Comparação Visual:**")

        comparison_df = pd.DataFrame([
            {
                "Métrica": "Taxa de Conformidade (%)",
                "Período Atual": comparison_data["Período Atual"]["taxa_conformidade"],
                "Período Anterior": comparison_data["Período Anterior"]["taxa_conformidade"]
            },
            {
                "Métrica": "Total de Detecções",
                "Período Atual": comparison_data["Período Atual"]["total_deteccoes"],
                "Período Anterior": comparison_data["Período Anterior"]["total_deteccoes"]
            },
            {
                "Métrica": "Alertas",
                "Período Atual": comparison_data["Período Atual"]["alertas"],
                "Período Anterior": comparison_data["Período Anterior"]["alertas"]
            }
        ])

        fig = px.bar(
            comparison_df,
            x='Métrica',
            y=['Período Atual', 'Período Anterior'],
            title='Comparação entre Períodos',
            barmode='group'
        )
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Recommendations
    st.subheader("💡 Recomendações")

    recommendations = [
        {
            "priority": "Alta",
            "recommendation": "Aumentar monitoramento de óculos de proteção",
            "reason": "Taxa de detecção de 62%, abaixo da meta de 80%"
        },
        {
            "priority": "Média",
            "recommendation": "Reforçar treinamento sobre uso de luvas",
            "reason": "Taxa de detecção de 78%, ligeiramente abaixo da meta"
        },
        {
            "priority": "Baixa",
            "recommendation": "Manter práticas atuais para botas",
            "reason": "Taxa de detecção de 95%, acima da meta"
        }
    ]

    for rec in recommendations:
        priority_color = {
            "Alta": "🔴",
            "Média": "🟡",
            "Baixa": "🟢"
        }

        st.markdown(
            f"""
            <div style='border: 1px solid #ddd; padding: 15px; margin-bottom: 10px; border-radius: 5px;'>
                <p><strong>{priority_color.get(rec['priority'], '')} Prioridade: {rec['priority']}</strong></p>
                <p>📌 {rec['recommendation']}</p>
                <p style='color: #666; font-size: 0.9em;'>💭 {rec['reason']}</p>
            </div>
            """,
            unsafe_allow_html=True
        )


if __name__ == "__main__":
    main()
