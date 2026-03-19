"""
Streamlit Alerts Page - Real-time Alerts and Violations
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(
    page_title="Alertas - Sistema de Monitoramento de EPI",
    page_icon="🚨",
    layout="wide"
)

st.title("🚨 Alertas e Violações em Tempo Real")
st.markdown("---")


def load_alerts():
    """Load alerts from database (placeholder)"""
    # Sample alerts data
    alerts = []

    severities = ["critical", "high", "medium", "low"]

    for i in range(20):
        is_resolved = i % 4 != 0

        alert = {
            "id": i + 1,
            "detection_id": 100 + i,
            "severity": severities[i % 4],
            "message": f"EPIs não detectados: {['Capacete', 'Luvas', 'Óculos', 'Colete'][i % 4]}",
            "is_resolved": is_resolved,
            "created_at": datetime.now() - timedelta(hours=i),
            "resolved_at": datetime.now() - timedelta(hours=i-1) if is_resolved else None,
            "camera": f"Camera {(i % 3) + 1}",
        }

        alerts.append(alert)

    return alerts


def main():
    """Main alerts page"""
    # Sidebar filters
    with st.sidebar:
        st.header("🔍 Filtros")

        # Severity filter
        severity_filter = st.multiselect(
            "Severidade:",
            options=["critical", "high", "medium", "low"],
            default=["critical", "high", "medium", "low"]
        )

        # Status filter
        status_filter = st.selectbox(
            "Status:",
            options=["Todos", "Não Resolvidos", "Resolvidos"],
            index=1
        )

        # Time filter
        time_filter = st.selectbox(
            "Período:",
            options=["Última hora", "Últimas 24h", "Últimos 7 dias", "Todos"],
            index=2
        )

        st.markdown("---")

        # Quick stats
        st.subheader("📊 Resumo")

        alerts = load_alerts()

        critical_count = sum(1 for a in alerts if a["severity"] == "critical" and not a["is_resolved"])
        high_count = sum(1 for a in alerts if a["severity"] == "high" and not a["is_resolved"])
        medium_count = sum(1 for a in alerts if a["severity"] == "medium" and not a["is_resolved"])
        total_unresolved = sum(1 for a in alerts if not a["is_resolved"])

        st.metric("🚨 Críticos", critical_count, delta_color="inverse")
        st.metric("⚠️ Altos", high_count, delta_color="inverse")
        st.metric("⚡ Médios", medium_count)
        st.metric("📋 Total Não Resolvidos", total_unresolved, delta_color="inverse")

    # Load alerts
    alerts = load_alerts()

    # Apply filters
    filtered_alerts = [
        a for a in alerts
        if a["severity"] in severity_filter
    ]

    if status_filter == "Não Resolvidos":
        filtered_alerts = [a for a in filtered_alerts if not a["is_resolved"]]
    elif status_filter == "Resolvidos":
        filtered_alerts = [a for a in filtered_alerts if a["is_resolved"]]

    # Alert statistics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total de Alertas",
            len(filtered_alerts),
            delta=f"Ativos: {sum(1 for a in filtered_alerts if not a['is_resolved'])}"
        )

    with col2:
        critical = sum(1 for a in filtered_alerts if a["severity"] == "critical")
        st.metric("🚨 Críticos", critical, delta_color="inverse" if critical > 0 else "normal")

    with col3:
        high = sum(1 for a in filtered_alerts if a["severity"] == "high")
        st.metric("⚠️ Altos", high, delta_color="inverse" if high > 0 else "normal")

    with col4:
        unresolved = sum(1 for a in filtered_alerts if not a["is_resolved"])
        st.metric("📋 Não Resolvidos", unresolved, delta_color="inverse" if unresolved > 0 else "normal")

    st.markdown("---")

    # Alerts table
    st.subheader("📋 Lista de Alertas")

    # Prepare table data
    table_data = []
    for alert in filtered_alerts:
        severity_emoji = {
            "critical": "🚨",
            "high": "⚠️",
            "medium": "⚡",
            "low": "ℹ️"
        }

        status_emoji = "✅" if alert["is_resolved"] else "❌"

        table_data.append({
            "ID": alert["id"],
            "Severidade": f"{severity_emoji.get(alert['severity'], '')} {alert['severity'].upper()}",
            "Mensagem": alert["message"],
            "Câmera": alert["camera"],
            "Status": status_emoji,
            "Criado em": alert["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
            "Resolvido em": alert["resolved_at"].strftime("%Y-%m-%d %H:%M:%S") if alert["resolved_at"] else "-",
        })

    df = pd.DataFrame(table_data)

    # Display table
    if not df.empty:
        # Style dataframe by severity
        def color_severity(val):
            if "CRITICAL" in val:
                return ['background-color: #ffebee'] * len(val)
            elif "HIGH" in val:
                return ['background-color: #fff3e0'] * len(val)
            elif "MEDIUM" in val:
                return ['background-color: #f3e5f5'] * len(val)
            else:
                return ['background-color: #e3f2fd'] * len(val)

        styled_df = df.style.apply(color_severity, subset=['Severidade'])
        st.dataframe(styled_df, use_container_width=True, height=500)
    else:
        st.info("Nenhum alerta encontrado com os filtros selecionados.")

    st.markdown("---")

    # Alert resolution
    st.subheader("✅ Resolver Alertas")

    col1, col2 = st.columns([2, 1])

    with col1:
        alert_id = st.number_input("ID do Alerta:", min_value=1, value=1)
        resolution_notes = st.text_area("Notas de Resolução:")

    with col2:
        st.write("Ações")
        resolve_button = st.button("Resolver Alerta", type="primary")

        if resolve_button:
            st.success(f"Alerta {alert_id} resolvido com sucesso!")

    st.markdown("---")

    # Recent alerts timeline
    st.subheader("📈 Linha do Tempo de Alertas")

    # Sort by created date
    sorted_alerts = sorted(filtered_alerts, key=lambda x: x["created_at"], reverse=True)

    # Display timeline
    for alert in sorted_alerts[:5]:
        severity_color = {
            "critical": "red",
            "high": "orange",
            "medium": "purple",
            "low": "blue"
        }.get(alert["severity"], "gray")

        status_text = "Resolvido" if alert["is_resolved"] else "Não Resolvido"
        status_color = "green" if alert["is_resolved"] else "red"

        st.markdown(
            f"""
            <div style='border-left: 3px solid {severity_color}; padding-left: 10px; margin-bottom: 15px;'>
                <p style='margin: 0;'><strong>{alert['message']}</strong></p>
                <p style='margin: 5px 0; color: #666; font-size: 0.9em;'>
                    📹 {alert['camera']} | 🕐 {alert['created_at'].strftime('%Y-%m-%d %H:%M:%S')}
                </p>
                <p style='margin: 5px 0;'>
                    <span style='color: {severity_color}; font-weight: bold;'>{alert['severity'].upper()}</span> |
                    <span style='color: {status_color};'>{status_text}</span>
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )


if __name__ == "__main__":
    main()
