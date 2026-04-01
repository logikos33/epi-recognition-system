import { useState, useEffect, useRef, useCallback } from "react";
import { useCameras } from "./hooks/useCameras";
import { useStreams } from "./hooks/useStreams";
import { useToast } from "./hooks/useToast";
import CameraForm from "./components/CameraForm";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import Modal from "./components/Modal";
import ToastContainer from "./components/Toast";
import ImageUploadZone from "./components/ImageUploadZone.jsx";
import { api } from "./services/api";

import AnnotationInterface from "./components/AnnotationInterface.jsx";
import VideoTimelineSelector from "./components/VideoTimelineSelector.jsx";

// ══════════════════════════════════════════════════
// DEMO DATA — Câmeras e Detecções (Mock para demonstração)
// Em produção: vem do backend via API
// ══════════════════════════════════════════════════

const DEMO_CAMERAS = [
  { id: 1, name: 'Doca 01 — Carga', ip: '192.168.1.101', status: 'online', location: 'Galpão A', model: 'Intelbras VIP 3230', resolution: '1080p' },
  { id: 2, name: 'Doca 02 — Descarga', ip: '192.168.1.102', status: 'online', location: 'Galpão A', model: 'Hikvision DS-2CD', resolution: '4K' },
  { id: 3, name: 'Pátio Externo', ip: '192.168.1.103', status: 'offline', location: 'Externo', model: 'Intelbras VIP 1230', resolution: '720p' },
  { id: 4, name: 'Doca 03 — Lateral', ip: '192.168.1.104', status: 'online', location: 'Galpão B', model: 'Intelbras VIP 3230', resolution: '1080p' },
  { id: 5, name: 'Portaria — Entrada', ip: '192.168.1.105', status: 'online', location: 'Portaria', model: 'Hikvision DS-2CD', resolution: '1080p' },
  { id: 6, name: 'Doca 04 — Fundo', ip: '192.168.1.106', status: 'online', location: 'Galpão B', model: 'Intelbras VIP 3230', resolution: '1080p' },
  { id: 7, name: 'Estacionamento', ip: '192.168.1.107', status: 'online', location: 'Externo', model: 'Intelbras VIP 1230', resolution: '720p' },
  { id: 8, name: 'Sala de Controle', ip: '192.168.1.108', status: 'online', location: 'Adm', model: 'Intelbras VIP 3230', resolution: '1080p' },
  { id: 9, name: 'Corredor Central', ip: '192.168.1.109', status: 'offline', location: 'Galpão A', model: 'Hikvision DS-2CD', resolution: '1080p' },
]

const CAMERA_DETECTIONS = {
  1: {
    truck_plate: 'ABC-1234',
    start_time: '14:32:15',
    elapsed: '00:12:45',
    products_counted: 47,
    status: 'counting',
    confidence: 94,
  },
  2: {
    truck_plate: 'XYZ-5678',
    start_time: '14:15:00',
    elapsed: '00:30:10',
    products_counted: 132,
    status: 'completed',
    confidence: 97,
  },
  4: {
    truck_plate: 'ABC-1234',
    start_time: '14:32:15',
    elapsed: '00:12:45',
    products_counted: 47,
    status: 'counting',
    confidence: 94,
    linked_camera: 1,
  },
  5: null,
  6: {
    truck_plate: 'DEF-9012',
    start_time: '14:50:00',
    elapsed: '00:05:20',
    products_counted: 18,
    status: 'validating',
    confidence: 88,
  },
  7: {
    truck_plate: null,
    start_time: '14:45:00',
    elapsed: '00:01:30',
    products_counted: 0,
    status: 'idle',
    confidence: 0,
  },
  8: null,
}

// ══════════════════════════════════════════════════
// SLIDESHOW FRAMES — Frames para câmeras sem frameId
// Troca a cada 5 segundos (câmera usa offset diferente)
// ══════════════════════════════════════════════════
// NOTA: Slideshow desabilitado - IDs hardcoded foram removidos
// para evitar 404 ao tentar carregar frames que não existem no banco
const SLIDESHOW_FRAMES = [];

// ── Icons ──
const Icons = {
  menu: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M3 12h18M3 6h18M3 18h18"/></svg>,
  x: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M18 6L6 18M6 6l12 12"/></svg>,
  dashboard: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>,
  camera: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z"/><circle cx="12" cy="13" r="4"/></svg>,
  monitor: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>,
  classes: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 002 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0022 16z"/><path d="M3.27 6.96L12 12.01l8.73-5.05M12 22.08V12"/></svg>,
  training: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>,
  bell: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 01-3.46 0"/></svg>,
  user: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>,
  plus: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M12 5v14M5 12h14"/></svg>,
  search: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>,
  wifi: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12.55a11 11 0 0114.08 0M1.42 9a16 16 0 0121.16 0M8.53 16.11a6 6 0 016.95 0M12 20h.01"/></svg>,
  wifiOff: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 1l22 22M16.72 11.06A10.94 10.94 0 0119 12.55M5 12.55a10.94 10.94 0 015.17-2.39M10.71 5.05A16 16 0 0122.56 9M1.42 9a15.91 15.91 0 014.7-2.88M8.53 16.11a6 6 0 016.95 0M12 20h.01"/></svg>,
  activity: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>,
  shield: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>,
  alertTriangle: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0zM12 9v4M12 17h.01"/></svg>,
  settings: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.32 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/></svg>,
  sliders: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/></svg>,
  logout: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9"/></svg>,
  eye: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>,
  edit: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>,
  trash: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>,
  play: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>,
  grip: <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><circle cx="9" cy="5" r="1.8"/><circle cx="15" cy="5" r="1.8"/><circle cx="9" cy="12" r="1.8"/><circle cx="15" cy="12" r="1.8"/><circle cx="9" cy="19" r="1.8"/><circle cx="15" cy="19" r="1.8"/></svg>,
  maximize: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>,
  minimize: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="4 14 10 14 10 20"/><polyline points="20 10 14 10 14 4"/><line x1="14" y1="10" x2="21" y2="3"/><line x1="3" y1="21" x2="10" y2="14"/></svg>,
  panelRight: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="15" y1="3" x2="15" y2="21"/></svg>,
  check: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>,
};

// ── Data ──
const CLASSES = [
  { id: 1, name: "Capacete", color: "#22c55e", count: 1247, icon: "🪖" },
  { id: 2, name: "Colete", color: "#f59e0b", count: 1089, icon: "🦺" },
  { id: 3, name: "Óculos", color: "#3b82f6", count: 856, icon: "🥽" },
  { id: 4, name: "Luvas", color: "#8b5cf6", count: 723, icon: "🧤" },
  { id: 5, name: "Bota", color: "#ec4899", count: 945, icon: "👢" },
  { id: 6, name: "Sem EPI", color: "#ef4444", count: 156, icon: "⚠️" },
];

const ALERTS = [
  { id: 1, time: "14:32", camera: "Entrada Principal", type: "warning", message: "Operador sem capacete detectado" },
  { id: 2, time: "14:28", camera: "Área de Produção", type: "critical", message: "Múltiplas violações de EPI" },
  { id: 3, time: "14:15", camera: "Depósito", type: "info", message: "Todos os EPIs conformes" },
  { id: 4, time: "13:58", camera: "Refeitório", type: "warning", message: "Sem colete na área restrita" },
  { id: 5, time: "13:42", camera: "Entrada Principal", type: "info", message: "Detecção calibrada com sucesso" },
];

// ── Shared ──
const StatCard = ({ icon, label, value, sub, color, delay }) => (
  <div style={{ background: "var(--card)", borderRadius: 16, padding: "20px 24px", display: "flex", alignItems: "center", gap: 16, animation: `fadeUp 0.5s ease ${delay}s both`, border: "1px solid var(--border)", transition: "transform 0.2s, box-shadow 0.2s", cursor: "default" }}
    onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.boxShadow = "0 8px 32px rgba(0,0,0,0.12)"; }}
    onMouseLeave={e => { e.currentTarget.style.transform = ""; e.currentTarget.style.boxShadow = ""; }}>
    <div style={{ width: 48, height: 48, borderRadius: 12, background: `${color}18`, color, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>{icon}</div>
    <div>
      <div style={{ fontSize: 13, color: "var(--muted)", fontWeight: 500, marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color: "var(--text)", lineHeight: 1.1 }}>{value}</div>
      {sub && <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 2 }}>{sub}</div>}
    </div>
  </div>
);

// ── Dashboard (FASE 5 - Atualizado com dados reais) ──
const DashboardPage = ({ cameras }) => {
  const [kpis, setKpis] = useState(null);
  const [productsPerHour, setProductsPerHour] = useState([]);
  const [sessionsPerBay, setSessionsPerBay] = useState([]);
  const [recentAlerts, setRecentAlerts] = useState([]);
  const [recentValidated, setRecentValidated] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [period, setPeriod] = useState("today");
  const { success, error: toastError } = useToast();

  // Polling para dashboard data (30s com backoff)
  useEffect(() => {
    let mounted = true;
    let failCount = 0;
    let pollInterval = 30000; // 30s inicial

    const fetchDashboardData = async () => {
      try {
        const token = localStorage.getItem("token") || "";
        const headers = { "Authorization": `Bearer ${token}` };

        // Buscar dados em paralelo
        const [
          kpisRes,
          productsRes,
          sessionsRes,
          alertsRes,
          validatedRes,
        ] = await Promise.all([
          fetch(`http://localhost:5001/api/dashboard/kpis?period=${period}`, { headers }),
          fetch("http://localhost:5001/api/dashboard/chart/products-per-hour", { headers }),
          fetch("http://localhost:5001/api/dashboard/chart/sessions-per-bay", { headers }),
          fetch("http://localhost:5001/api/dashboard/alerts/recent?limit=5", { headers }),
          fetch("http://localhost:5001/api/dashboard/sessions/recent-validated?limit=5", { headers }),
        ]);

        if (!kpisRes.ok) throw new Error(`KPIs: HTTP ${kpisRes.status}`);
        if (!productsRes.ok) throw new Error(`Products: HTTP ${productsRes.status}`);
        if (!sessionsRes.ok) throw new Error(`Sessions: HTTP ${sessionsRes.status}`);
        if (!alertsRes.ok) throw new Error(`Alerts: HTTP ${alertsRes.status}`);
        if (!validatedRes.ok) throw new Error(`Validated: HTTP ${validatedRes.status}`);

        const kpisData = await kpisRes.json();
        const productsData = await productsRes.json();
        const sessionsData = await sessionsRes.json();
        const alertsData = await alertsRes.json();
        const validatedData = await validatedRes.json();

        if (mounted) {
          if (kpisData.success) setKpis(kpisData.kpis);
          if (productsData.success) setProductsPerHour(productsData.data);
          if (sessionsData.success) setSessionsPerBay(sessionsData.data);
          if (alertsData.success) setRecentAlerts(alertsData.alerts);
          if (validatedData.success) setRecentValidated(validatedData.sessions);
          setError(null);
          failCount = 0;
          pollInterval = 30000;
        }
      } catch (err) {
        if (mounted) {
          console.error("Erro ao buscar dados do dashboard:", err);
          failCount++;
          pollInterval = Math.min(30000 * Math.pow(2, failCount - 1), 60000);
        }
      } finally {
        if (mounted) setLoading(false);
      }
    };

    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, pollInterval);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [period]);

  // Export Excel
  const handleExportExcel = async () => {
    try {
      const token = localStorage.getItem("token") || "";
      const res = await fetch("http://localhost:5001/api/dashboard/export/excel", {
        headers: { "Authorization": `Bearer ${token}` },
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      // Download file
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `EPI_Monitor_Relatorio_${new Date().toISOString().split('T')[0]}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      success("Relatório Excel exportado com sucesso!");
    } catch (err) {
      console.error("Erro ao exportar Excel:", err);
      toastError(err.message || "Erro ao exportar Excel");
    }
  };

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, color: "var(--text)", margin: 0 }}>
          Dashboard
        </h1>
        <p style={{ color: "var(--muted)", margin: "4px 0 0", fontSize: 14 }}>
          Visão geral do sistema de monitoramento
        </p>
      </div>

      {loading ? (
        <div style={{ textAlign: "center", padding: 60 }}>
          <div style={{
            width: 40, height: 40, margin: "0 auto 16px",
            border: "3px solid var(--border)", borderTopColor: "var(--accent)",
            borderRadius: "50%", animation: "spin 1s linear infinite"
          }} />
          <p style={{ color: "var(--muted)", fontSize: 14 }}>Carregando dashboard...</p>
        </div>
      ) : kpis ? (
        <>
          {/* KPI Cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16, marginBottom: 32 }}>
            <StatCard icon={Icons.camera} label="Câmeras" value={cameras.length} sub={`${cameras.filter(c=>c.status==="online").length} online`} color="#3b82f6" delay={0} />
            <StatCard icon={Icons.shield} label="Produtos Hoje" value={kpis.products_total.toLocaleString()} sub={`${kpis.sessions_total} sessões`} color="#22c55e" delay={0.05} />
            <StatCard icon={Icons.alertTriangle} label="Pendentes" value={kpis.pending_validation} sub="Aguardando validação" color="#f59e0b" delay={0.1} />
            <StatCard icon={Icons.activity} label="Precisão IA" value={`${kpis.accuracy_rate}%`} sub={`${kpis.avg_duration_minutes}min médio`} color="#8b5cf6" delay={0.15} />
          </div>

          {/* Period Selector + Export Button */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20, flexWrap: "wrap", gap: 12 }}>
            <div style={{ display: "flex", gap: 8 }}>
              {["today", "7days", "30days", "all"].map(p => (
                <button
                  key={p}
                  onClick={() => setPeriod(p)}
                  style={{
                    padding: "8px 16px", borderRadius: 8,
                    background: period === p ? "var(--accent)" : "var(--bg)",
                    color: period === p ? "#fff" : "var(--text)",
                    border: period === p ? "none" : "1px solid var(--border)",
                    fontSize: 13, fontWeight: period === p ? 600 : 500, cursor: "pointer",
                    transition: "all 0.15s"
                  }}
                  onMouseEnter={e => { if (period !== p) e.currentTarget.style.borderColor = "var(--accent)"; }}
                  onMouseLeave={e => { if (period !== p) e.currentTarget.style.borderColor = "var(--border)"; }}
                >
                  {p === "today" && "Hoje"}
                  {p === "7days" && "7 dias"}
                  {p === "30days" && "30 dias"}
                  {p === "all" && "Tudo"}
                </button>
              ))}
            </div>
            <button
              onClick={handleExportExcel}
              style={{
                display: "flex", alignItems: "center", gap: 8,
                padding: "10px 18px", borderRadius: 8,
                background: "#22c55e", color: "#fff",
                border: "none", fontSize: 13, fontWeight: 600, cursor: "pointer",
                transition: "opacity 0.15s"
              }}
              onMouseEnter={e => e.currentTarget.style.opacity = "0.9"}
              onMouseLeave={e => e.currentTarget.style.opacity = "1"}
            >
              {Icons.activity} Exportar Excel
            </button>
          </div>

          {/* Charts */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))", gap: 20, marginBottom: 20 }}>
            {/* Products per Hour Chart */}
            <div style={{ background: "var(--card)", borderRadius: 16, border: "1px solid var(--border)", padding: 24, animation: "fadeUp 0.5s ease 0.2s both" }}>
              <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--text)", margin: "0 0 20px" }}>
                Produtos por Hora
              </h3>
              {productsPerHour.length > 0 ? (
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={productsPerHour}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis dataKey="hour" tick={{ fill: "var(--muted)", fontSize: 12 }} />
                    <YAxis tick={{ fill: "var(--muted)", fontSize: 12 }} />
                    <Tooltip contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8 }} />
                    <Line type="monotone" dataKey="count" stroke="#2563eb" strokeWidth={2} dot={{ r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <p style={{ color: "var(--muted)", fontSize: 14, textAlign: "center", padding: 40 }}>
                  Nenhum dado disponível
                </p>
              )}
            </div>

            {/* Sessions per Bay Chart */}
            <div style={{ background: "var(--card)", borderRadius: 16, border: "1px solid var(--border)", padding: 24, animation: "fadeUp 0.5s ease 0.25s both" }}>
              <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--text)", margin: "0 0 20px" }}>
                Sessões por Baia
              </h3>
              {sessionsPerBay.length > 0 ? (
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={sessionsPerBay}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis dataKey="bay_id" tick={{ fill: "var(--muted)", fontSize: 12 }} />
                    <YAxis tick={{ fill: "var(--muted)", fontSize: 12 }} />
                    <Tooltip contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8 }} />
                    <Bar dataKey="sessions" fill="#8b5cf6" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p style={{ color: "var(--muted)", fontSize: 14, textAlign: "center", padding: 40 }}>
                  Nenhum dado disponível
                </p>
              )}
            </div>
          </div>

          {/* Recent Validated Sessions */}
          {recentValidated.length > 0 && (
            <div style={{ background: "var(--card)", borderRadius: 16, border: "1px solid var(--border)", padding: 24, animation: "fadeUp 0.5s ease 0.3s both" }}>
              <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--text)", margin: "0 0 20px" }}>
                Últimas Validações
              </h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {recentValidated.map((session, index) => (
                  <div key={session.id} style={{
                    padding: 14, borderRadius: 10,
                    background: "var(--bg)", border: "1px solid var(--border)",
                    display: "flex", alignItems: "center", gap: 12,
                    animation: `fadeUp 0.3s ease ${0.35 + index * 0.05}s both`
                  }}>
                    <span style={{ fontSize: 24 }}>✅</span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{
                        fontSize: 14, fontWeight: 500, color: "var(--text)",
                        whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis"
                      }}>
                        {session.truck_plate || "Placa não identificada"}
                      </div>
                      <div style={{ fontSize: 12, color: "var(--muted)" }}>
                        Baia {session.bay_id || session.camera_id || "?"} · IA: {session.ai_count}
                        {session.operator_count && session.operator_count !== session.ai_count && (
                          <span style={{ color: "#f59e0b", fontWeight: 500 }}>
                            → Operador: {session.operator_count}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      ) : (
        <div style={{
          background: "#fef2f2", border: "1px solid #fecaca",
          borderRadius: 12, padding: 24, textAlign: "center"
        }}>
          <p style={{ color: "#dc2626", fontSize: 14, fontWeight: 500, margin: "0 0 8px" }}>
            Erro ao carregar dados
          </p>
          <button
            onClick={() => window.location.reload()}
            style={{
              padding: "10px 20px", borderRadius: 8,
              background: "#dc2626", color: "#fff",
              border: "none", fontSize: 14, fontWeight: 600, cursor: "pointer"
            }}
          >
            Recarregar Página
          </button>
        </div>
      )}
    </div>
  );
};

// ── Cameras ──
const CamerasPage = () => {
  const [search, setSearch] = useState("");
  const [deleteConfirm, setDeleteConfirm] = useState(null);

  const filteredCameras = DEMO_CAMERAS.filter(c =>
    c.name.toLowerCase().includes(search.toLowerCase()) ||
    (c.location && c.location.toLowerCase().includes(search.toLowerCase())) ||
    c.ip.includes(search)
  );

  const handleDeleteClick = (camera) => {
    setDeleteConfirm(camera);
  };

  const confirmDelete = () => {
    if (deleteConfirm) {
      // Em produção: chamar API de deletar
      console.log("Deletar câmera:", deleteConfirm.id);
      setDeleteConfirm(null);
    }
  };

  return (
    <div>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 28, flexWrap: "wrap", gap: 16 }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 700, color: "var(--text)", margin: 0 }}>Câmeras</h1>
          <p style={{ color: "var(--muted)", margin: "4px 0 0", fontSize: 14 }}>Gerencie suas câmeras IP</p>
        </div>
        <button style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 20px", borderRadius: 10, background: "var(--accent)", color: "#fff", border: "none", fontSize: 14, fontWeight: 600, cursor: "pointer" }}>
          {Icons.plus} Nova Câmera
        </button>
      </div>

      {/* Stats Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12, marginBottom: 24 }}>
        {[
          { label: "Total", value: DEMO_CAMERAS.length, color: "var(--accent)" },
          { label: "Online", value: DEMO_CAMERAS.filter(c => c.status === "online").length, color: "#22c55e" },
          { label: "Offline", value: DEMO_CAMERAS.filter(c => c.status === "offline").length, color: "#ef4444" }
        ].map((stat, i) => (
          <div key={i} style={{ background: "var(--card)", borderRadius: 12, padding: "16px 20px", border: "1px solid var(--border)" }}>
            <div style={{ fontSize: 12, color: "var(--muted)", fontWeight: 500, marginBottom: 4 }}>{stat.label}</div>
            <div style={{ fontSize: 24, fontWeight: 700, color: stat.color }}>{stat.value}</div>
          </div>
        ))}
      </div>

      {/* Search Bar */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, background: "var(--card)", border: "1px solid var(--border)", borderRadius: 10, padding: "10px 16px", marginBottom: 20 }}>
        <span style={{ color: "var(--muted)" }}>{Icons.search}</span>
        <input
          type="text"
          placeholder="Buscar câmera por nome, localização ou IP..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ background: "none", border: "none", outline: "none", color: "var(--text)", fontSize: 14, width: "100%", fontFamily: "inherit" }}
        />
      </div>

      {/* Cameras Grid */}
      {filteredCameras.length === 0 ? (
        <div style={{ textAlign: "center", padding: "60px 20px", background: "var(--card)", borderRadius: 14, border: "1px dashed var(--border)" }}>
          <div style={{ fontSize: 48, marginBottom: 16, opacity: 0.3 }}>{Icons.camera}</div>
          <div style={{ fontSize: 16, fontWeight: 600, color: "var(--text)", marginBottom: 8 }}>Nenhuma câmera encontrada</div>
          <div style={{ fontSize: 14, color: "var(--muted)", marginBottom: 20 }}>Tente buscar com outro termo</div>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 16 }}>
          {filteredCameras.map((cam, i) => {
            const isOnline = cam.status === "online";
            const hasFrame = cam.frameId && isOnline;
            const detections = CAMERA_DETECTIONS[cam.id];

            return (
              <div
                key={cam.id}
                style={{
                  background: "var(--card)",
                  borderRadius: 14,
                  border: "1px solid var(--border)",
                  overflow: "hidden",
                  animation: `fadeUp 0.4s ease ${0.05 + i * 0.04}s both`,
                  transition: "transform 0.2s",
                }}
                onMouseEnter={e => e.currentTarget.style.transform = "translateY(-2px)"}
                onMouseLeave={e => e.currentTarget.style.transform = ""}
              >
                {/* Camera Preview Image */}
                <div style={{ height: 180, position: "relative", background: "#0a0e1a" }}>
                  {hasFrame ? (
                    <>
                      {/* Real Frame Image */}
                      <img
                        src={`/api/training/frames/${cam.frameId}/image`}
                        alt={cam.name}
                        style={{
                          position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover",
                          filter: "brightness(0.9) contrast(1.05)",
                        }}
                        draggable={false}
                      />
                      {/* Scanlines */}
                      <div style={{
                        position: "absolute", inset: 0,
                        background: "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.03) 2px, rgba(0,0,0,0.03) 4px)",
                        pointerEvents: "none",
                      }} />
                      {/* Vignette */}
                      <div style={{
                        position: "absolute", inset: 0,
                        background: "radial-gradient(circle at center, transparent 0%, rgba(0,0,0,0.25) 100%)",
                        pointerEvents: "none",
                      }} />
                    </>
                  ) : (
                    <div style={{
                      position: "absolute", inset: 0,
                      background: isOnline
                        ? "linear-gradient(135deg, #1a1a2e, #16213e, #0f3460)"
                        : "linear-gradient(135deg, #1a1a1a, #2d2d2d)",
                      display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 8
                    }}>
                      <div style={{ color: "rgba(255,255,255,0.15)" }}>{Icons.wifiOff}</div>
                      <div style={{ color: "rgba(255,255,255,0.25)", fontSize: 11, fontFamily: "var(--mono)", letterSpacing: 2 }}>
                        {isOnline ? "SEM SINAL" : "OFFLINE"}
                      </div>
                    </div>
                  )}

                  {/* Status Badge */}
                  {isOnline && (
                    <div style={{
                      position: "absolute", top: 10, left: 10,
                      display: "flex", alignItems: "center", gap: 4,
                      background: "rgba(34, 197, 94, 0.9)",
                      padding: "4px 8px", borderRadius: 5,
                      fontSize: 10, fontWeight: 700, color: "#fff", fontFamily: "var(--mono)",
                      boxShadow: "0 2px 8px rgba(0,0,0,0.3)"
                    }}>
                      <span style={{ width: 5, height: 5, borderRadius: "50%", background: "#fff", animation: "pulse 1.5s infinite" }} />
                      ONLINE
                    </div>
                  )}

                  {/* REC Badge */}
                  {isOnline && (
                    <div style={{
                      position: "absolute", top: 10, right: 10,
                      display: "flex", alignItems: "center", gap: 4,
                      background: "rgba(220, 38, 38, 0.9)",
                      padding: "3px 8px", borderRadius: 5,
                      fontSize: 10, fontWeight: 700, color: "#fff", fontFamily: "var(--mono)",
                      boxShadow: "0 2px 8px rgba(0,0,0,0.3)"
                    }}>
                      <span style={{ width: 5, height: 5, borderRadius: "50%", background: "#fff", animation: "pulse 1.5s infinite" }} />
                      REC
                    </div>
                  )}

                  {/* YOLO Detection Info (Bottom Left) */}
                  {isOnline && detections && (
                    <div style={{
                      position: "absolute", bottom: 10, left: 10,
                      background: "rgba(0, 0, 0, 0.75)", backdropFilter: "blur(8px)",
                      border: "1px solid rgba(255,255,255,0.15)",
                      borderRadius: 6, padding: "6px 10px",
                      boxShadow: "0 2px 8px rgba(0,0,0,0.4)",
                    }}>
                      {detections.truck_plate && (
                        <div style={{ fontSize: 10, color: "rgba(255,255,255,0.5)", fontFamily: "var(--mono)", marginBottom: 2 }}>PLACA</div>
                      )}
                      {detections.truck_plate && (
                        <div style={{ fontSize: 13, fontWeight: 700, color: "#fff", fontFamily: "var(--mono)", letterSpacing: 1, marginBottom: detections.products_counted > 0 ? 6 : 0 }}>
                          {detections.truck_plate}
                        </div>
                      )}
                      {detections.products_counted > 0 && (
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <div style={{ fontSize: 10, color: "rgba(255,255,255,0.5)", fontFamily: "var(--mono)" }}>PRODUTOS</div>
                          <div style={{ fontSize: 14, fontWeight: 700, color: "#22c55e", fontFamily: "var(--mono)" }}>
                            {detections.products_counted}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Camera Info */}
                <div style={{ padding: "16px 18px" }}>
                  {/* Name and Status */}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                    <div style={{ fontSize: 16, fontWeight: 600, color: "var(--text)" }}>{cam.name}</div>
                    <span style={{
                      display: "inline-flex", alignItems: "center", gap: 4, padding: "3px 9px", borderRadius: 20,
                      fontSize: 10, fontWeight: 600,
                      background: isOnline ? "#22c55e18" : "#ef444418",
                      color: isOnline ? "#22c55e" : "#ef4444"
                    }}>
                      <span style={{ width: 5, height: 5, borderRadius: "50%", background: isOnline ? "#22c55e" : "#ef4444" }} />
                      {isOnline ? "Online" : "Offline"}
                    </span>
                  </div>

                  {/* Location and Model */}
                  <div style={{ fontSize: 13, color: "var(--muted)", marginBottom: 2 }}>{cam.location || "Sem localização"}</div>
                  <div style={{ fontSize: 12, color: "var(--muted)" }}>{cam.model || "Modelo não informado"}</div>

                  {/* IP and Resolution */}
                  <div style={{ fontSize: 11, color: "var(--muted)", fontFamily: "var(--mono)", marginTop: 6, display: "flex", alignItems: "center", gap: 8 }}>
                    <span>{cam.ip}</span>
                    <span style={{ color: "rgba(107,114,128,0.5)" }}>•</span>
                    <span>{cam.resolution || "1080p"}</span>
                  </div>

                  {/* Action Buttons */}
                  <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
                    <button
                      style={{
                        flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
                        padding: "9px 12px", borderRadius: 8,
                        background: "var(--bg)", border: "1px solid var(--border)",
                        color: "var(--text)", fontSize: 12, fontWeight: 500, cursor: "pointer",
                        transition: "all 0.15s"
                      }}
                      onMouseEnter={e => e.currentTarget.style.borderColor = "var(--accent)"}
                      onMouseLeave={e => e.currentTarget.style.borderColor = "var(--border)"}
                    >
                      {Icons.edit} Editar
                    </button>
                    <button
                      onClick={() => handleDeleteClick(cam)}
                      style={{
                        flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
                        padding: "9px 12px", borderRadius: 8,
                        background: "var(--bg)", border: "1px solid var(--border)",
                        color: "var(--muted)", fontSize: 12, fontWeight: 500, cursor: "pointer",
                        transition: "all 0.15s"
                      }}
                      onMouseEnter={e => { e.currentTarget.style.borderColor = "#ef4444"; e.currentTarget.style.color = "#ef4444"; }}
                      onMouseLeave={e => { e.currentTarget.style.borderColor = "var(--border)"; e.currentTarget.style.color = "var(--muted)"; }}
                    >
                      {Icons.trash} Excluir
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div style={{
          position: "fixed", inset: 0, zIndex: 100,
          display: "flex", alignItems: "center", justifyContent: "center",
          background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)",
          animation: "fadeUp 0.2s ease both"
        }}>
          <div style={{
            background: "var(--card)", borderRadius: 16, border: "1px solid var(--border)",
            padding: 24, maxWidth: 420, width: "90%", boxShadow: "0 20px 60px rgba(0,0,0,0.3)"
          }}>
            <h3 style={{ fontSize: 18, fontWeight: 700, color: "var(--text)", margin: "0 0 12px" }}>Confirmar Exclusão</h3>
            <p style={{ fontSize: 14, color: "var(--muted)", lineHeight: 1.5, margin: "0 0 20px" }}>
              Tem certeza que deseja excluir a câmera <strong>{deleteConfirm.name}</strong>? Esta ação não pode ser desfeita.
            </p>
            <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
              <button
                onClick={() => setDeleteConfirm(null)}
                style={{
                  padding: "10px 20px", borderRadius: 8,
                  background: "var(--bg)", color: "var(--text)",
                  border: "1px solid var(--border)", fontSize: 14, fontWeight: 500, cursor: "pointer"
                }}
              >
                Cancelar
              </button>
              <button
                onClick={confirmDelete}
                style={{
                  padding: "10px 20px", borderRadius: 8,
                  background: "#ef4444", color: "#fff",
                  border: "none", fontSize: 14, fontWeight: 600, cursor: "pointer"
                }}
              >
                Excluir Câmera
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ── Classes ──
const ClassesPage = () => (
  <div>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 28, flexWrap: "wrap", gap: 16 }}>
      <div><h1 style={{ fontSize: 28, fontWeight: 700, color: "var(--text)", margin: 0 }}>Classes YOLO</h1><p style={{ color: "var(--muted)", margin: "4px 0 0", fontSize: 14 }}>Configure as classes para detecção</p></div>
      <button style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 20px", borderRadius: 10, background: "var(--accent)", color: "#fff", border: "none", fontSize: 14, fontWeight: 600, cursor: "pointer" }}>{Icons.plus} Nova Classe</button>
    </div>
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(270px, 1fr))", gap: 16 }}>
      {CLASSES.map((cls,i) => (
        <div key={cls.id} style={{ background: "var(--card)", borderRadius: 14, border: "1px solid var(--border)", padding: 24, animation: `fadeUp 0.4s ease ${i*0.06}s both`, transition: "transform 0.2s" }}
          onMouseEnter={e=>e.currentTarget.style.transform="translateY(-2px)"} onMouseLeave={e=>e.currentTarget.style.transform=""}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
            <span style={{ fontSize: 28, width: 48, height: 48, borderRadius: 12, background: `${cls.color}15`, display: "flex", alignItems: "center", justifyContent: "center" }}>{cls.icon}</span>
            <div><div style={{ fontSize: 16, fontWeight: 600, color: "var(--text)" }}>{cls.name}</div><div style={{ fontSize: 12, color: "var(--muted)" }}>class_{cls.id}</div></div>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", background: "var(--bg)", borderRadius: 10 }}>
            <div><div style={{ fontSize: 10, color: "var(--muted)", fontWeight: 600, letterSpacing: 0.5 }}>DETECÇÕES</div><div style={{ fontSize: 22, fontWeight: 700, color: cls.color }}>{cls.count.toLocaleString()}</div></div>
            <div style={{ display: "flex", gap: 6 }}>
              <button style={{ width: 32, height: 32, borderRadius: 8, background: "var(--card)", border: "1px solid var(--border)", color: "var(--muted)", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}>{Icons.edit}</button>
              <button style={{ width: 32, height: 32, borderRadius: 8, background: "var(--card)", border: "1px solid var(--border)", color: "var(--muted)", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}>{Icons.trash}</button>
            </div>
          </div>
        </div>
      ))}
    </div>
  </div>
);

// ── Training ──
const TrainingPage = () => {
  const [trainingTab, setTrainingTab] = useState('videos'); // 'videos', 'train', 'history'
  const [videos, setVideos] = useState([]);
  const [selectedVideoId, setSelectedVideoId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  // States para renomear
  const [renamingVideoId, setRenamingVideoId] = useState(null);
  const [renameValue, setRenameValue] = useState('');

  // State para upload de imagens
  const [imageUploadModalOpen, setImageUploadModalOpen] = useState(false);

  // State para timeline selector (vídeos > 10min)
  const [timelineModal, setTimelineModal] = useState({
    open: false,
    video: null
  });

  useEffect(() => {
    loadVideos();
  }, []);

  const loadVideos = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/training/videos', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const result = await response.json();
      if (result.success && result.videos) {
        setVideos(result.videos);
      }
    } catch (e) {
      // Silencioso
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadProgress(0);

    const formData = new FormData();
    formData.append('video', file);

    try {
      const token = localStorage.getItem('token');
      const res = await fetch('/api/training/videos/upload', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      const data = await res.json();
      if (data.success) {
        loadVideos();
      }
    } catch (e) {
      console.error('Upload error:', e);
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const handleDeleteVideo = async (videoId, e) => {
    e.stopPropagation();
    if (!confirm('Tem certeza que deseja excluir este vídeo e todos os seus frames e anotações?')) return;

    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`/api/training/videos/${videoId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        setVideos(prev => prev.filter(v => v.id !== videoId));
      }
    } catch (e) {
      console.error('Delete error:', e);
    }
  };

  const handleRenameVideo = async (videoId) => {
    if (!renameValue.trim()) {
      setRenamingVideoId(null);
      return;
    }

    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`/api/training/videos/${videoId}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name: renameValue.trim() })
      });
      if (res.ok) {
        setVideos(prev => prev.map(v =>
          v.id === videoId ? { ...v, name: renameValue.trim() } : v
        ));
      }
    } catch (e) {
      console.error('Rename error:', e);
    } finally {
      setRenamingVideoId(null);
      setRenameValue('');
    }
  };

  const handleExtractFrames = (video) => {
    // Para vídeos > 10min (600s), mostrar timeline selector
    const duration = video.duration_seconds || 0;
    if (duration > 600) {
      setTimelineModal({
        open: true,
        video: video
      });
    } else {
      // Para vídeos curtos, extrair direto
      extractVideoFrames(video.id);
    }
  };

  const extractVideoFrames = async (videoId, startTime = null, endTime = null) => {
    try {
      const token = localStorage.getItem('token');

      const body = {};
      if (startTime !== null && endTime !== null) {
        body.start_time = startTime;
        body.end_time = endTime;
      }

      const res = await fetch(`/api/training/videos/${videoId}/extract`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
      });

      const data = await res.json();

      if (data.success) {
        // Atualizar status do vídeo para 'extracting'
        setVideos(prev => prev.map(v => {
          if (v.id === videoId) {
            return { ...v, status: 'extracting' };
          }
          return v;
        }));

        // Fechar modal se estiver aberto
        if (timelineModal.open) {
          setTimelineModal({ open: false, video: null });
        }

        // Poll para atualizar progresso
        const pollInterval = setInterval(async () => {
          try {
            const token = localStorage.getItem('token');
            const statusRes = await fetch(`/api/training/videos`, {
              headers: { 'Authorization': `Bearer ${token}` }
            });
            const statusData = await statusRes.json();

            if (statusData.success && statusData.videos) {
              const updatedVideo = statusData.videos.find(v => v.id === videoId);
              if (updatedVideo && updatedVideo.status !== 'extracting') {
                clearInterval(pollInterval);
                setVideos(statusData.videos);
              }
            }
          } catch (e) {
            clearInterval(pollInterval);
          }
        }, 2000);

      } else {
        alert('Erro ao extrair frames: ' + (data.error || 'Erro desconhecido'));
      }
    } catch (e) {
      console.error('Extract error:', e);
      alert('Erro ao extrair frames');
    }
  };

  // Se um vídeo foi selecionado, mostrar a interface de anotação
  if (selectedVideoId) {
    return (
      <AnnotationInterface
        videoId={selectedVideoId}
        onBack={() => setSelectedVideoId(null)}
      />
    );
  }

  // Caso contrário, mostrar a lista de vídeos ou outras tabs
  const tabs = [
    { id: 'videos', label: 'Vídeos & Dados' },
    { id: 'train', label: 'Treinar' },
    { id: 'history', label: 'Histórico' },
  ];

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, color: "var(--text)", margin: 0 }}>Treinamento</h1>
        <p style={{ color: "var(--muted)", margin: "4px 0 0", fontSize: 14 }}>
          {trainingTab === 'videos' ? 'Selecione um vídeo para anotar' :
           trainingTab === 'train' ? 'Acompanhe e gerencie o treinamento do modelo YOLO' :
           'Histórico completo de treinamentos YOLO'}
        </p>
      </div>

      {/* Tab Navigation */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 24, borderBottom: '1px solid var(--border)', paddingBottom: 0 }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setTrainingTab(tab.id)}
            style={{
              padding: '10px 16px',
              background: trainingTab === tab.id ? 'rgba(37,99,235,0.8)' : 'transparent',
              color: trainingTab === tab.id ? '#fff' : 'var(--text)',
              border: 'none',
              borderBottom: trainingTab === tab.id ? '2px solid var(--accent)' : '2px solid transparent',
              borderRadius: '8px 8px 0 0',
              fontSize: 14,
              fontWeight: trainingTab === tab.id ? '600' : '400',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {trainingTab === 'train' && <TrainingTrainTab />}
      {trainingTab === 'history' && <TrainingHistoryTab />}

      {trainingTab === 'videos' && (
      <>
      {/* Tab 1 - Educational Banner */}
      <div style={{
        background: "linear-gradient(135deg, rgba(37,99,235,0.08) 0%, rgba(124,58,237,0.05) 100%)",
        borderRadius: 16, border: "1px solid rgba(37,99,235,0.2)",
        padding: 24, marginBottom: 28
      }}>
        <div style={{ marginBottom: 16 }}>
          <span style={{
            fontSize: 11, padding: "4px 10px", borderRadius: 6,
            background: "rgba(37,99,235,0.15)", color: "var(--accent)",
            fontWeight: 600, letterSpacing: 0.5, textTransform: "uppercase"
          }}>
            Passo 1 de 3
          </span>
        </div>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--text)", margin: "0 0 12px" }}>
          Envie seus vídeos ou imagens
        </h2>
        <p style={{ fontSize: 14, color: "var(--text-muted)", lineHeight: 1.6, margin: 0 }}>
          Esta é a primeira etapa do treinamento. Aqui você envia os vídeos gravados pelas câmeras das baias de carregamento ou fotos individuais dos produtos. O sistema vai extrair automaticamente os frames (imagens) do vídeo para que você possa anotá-los na etapa seguinte.
        </p>
      </div>

      {/* Requirements Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16, marginBottom: 28 }}>
        {/* Card 1 - Vídeos */}
        <div style={{
          background: "var(--card)", borderRadius: 12, border: "1px solid var(--border)",
          padding: 20
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
            <div style={{ fontSize: 28 }}>🎥</div>
            <h3 style={{ fontSize: 15, fontWeight: 600, color: "var(--text)", margin: 0 }}>Vídeos aceitos</h3>
          </div>
          <ul style={{ fontSize: 13, color: "var(--text-muted)", margin: 0, paddingLeft: 20, lineHeight: 1.8 }}>
            <li><strong>Formatos:</strong> MP4, AVI, MOV, MKV</li>
            <li><strong>Tamanho máximo:</strong> 2GB por arquivo</li>
            <li><strong>Duração recomendada:</strong> 2 a 10 minutos</li>
            <li><strong>Conteúdo:</strong> câmera da baia com operação real</li>
          </ul>
        </div>

        {/* Card 2 - Imagens */}
        <div style={{
          background: "var(--card)", borderRadius: 12, border: "1px solid var(--border)",
          padding: 20
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
            <div style={{ fontSize: 28 }}>🖼️</div>
            <h3 style={{ fontSize: 15, fontWeight: 600, color: "var(--text)", margin: 0 }}>Imagens aceitas</h3>
          </div>
          <ul style={{ fontSize: 13, color: "var(--text-muted)", margin: 0, paddingLeft: 20, lineHeight: 1.8 }}>
            <li><strong>Formatos:</strong> JPG, PNG</li>
            <li><strong>Tamanho máximo:</strong> 10MB por imagem</li>
            <li><strong>Limite:</strong> 100 imagens por envio</li>
            <li><strong>Conteúdo:</strong> fotos dos produtos ou operação</li>
          </ul>
        </div>

        {/* Card 3 - Quantidade mínima */}
        <div style={{
          background: "rgba(245,158,11,0.08)", borderRadius: 12,
          border: "1px solid rgba(245,158,11,0.3)", padding: 20
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
            <div style={{ fontSize: 28 }}>⚠️</div>
            <h3 style={{ fontSize: 15, fontWeight: 600, color: "#f59e0b", margin: 0 }}>Mínimo para treinar</h3>
          </div>
          <ul style={{ fontSize: 13, color: "var(--text-muted)", margin: 0, paddingLeft: 20, lineHeight: 1.8 }}>
            <li><strong>Pelo menos</strong> 50 frames anotados</li>
            <li><strong>Pelo menos</strong> 2 classes diferentes</li>
            <li><strong>Pelo menos</strong> 10 exemplos por classe</li>
            <li><strong>Quanto mais dados,</strong> melhor o modelo</li>
          </ul>
        </div>
      </div>

      {/* Visual Flow */}
      <div style={{
        background: "var(--card)", borderRadius: 12, border: "1px solid var(--border)",
        padding: 20, marginBottom: 32
      }}>
        <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 16, fontWeight: 500 }}>
          FLUXO DO TREINAMENTO
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
          {[
            { icon: '📤', label: 'Enviar vídeo', active: true },
            { icon: '🎞️', label: 'Extrair frames', active: false },
            { icon: '✏️', label: 'Anotar frames', active: false },
            { icon: '🚀', label: 'Treinar', active: false }
          ].map((step, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '10px 16px', borderRadius: 8,
                background: step.active ? 'rgba(37,99,235,0.1)' : 'transparent',
                border: step.active ? '1px solid rgba(37,99,235,0.3)' : '1px solid transparent'
              }}>
                <span style={{ fontSize: 20 }}>{step.icon}</span>
                <span style={{
                  fontSize: 13, fontWeight: 500,
                  color: step.active ? 'var(--accent)' : 'var(--text-muted)'
                }}>
                  {step.label}
                </span>
              </div>
              {i < 3 && (
                <span style={{ fontSize: 18, color: 'var(--border)', margin: '0 4px' }}>→</span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Upload Zone */}
      <div
        onClick={() => !uploading && document.getElementById('video-upload').click()}
        style={{
          border: '2px dashed rgba(37,99,235,0.3)',
          borderRadius: 12,
          padding: 32,
          textAlign: 'center',
          marginBottom: 24,
          background: 'rgba(37,99,235,0.05)',
          cursor: uploading ? 'not-allowed' : 'pointer',
          transition: 'all 0.2s',
          opacity: uploading ? 0.6 : 1,
        }}
        onMouseEnter={(e) => {
          if (!uploading) e.currentTarget.style.borderColor = 'rgba(37,99,235,0.6)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = '';
        }}
      >
        <input
          id="video-upload"
          type="file"
          accept="video/*"
          onChange={handleUpload}
          disabled={uploading}
          style={{ display: 'none' }}
        />
        {uploading ? (
          <div>
            <div style={{ fontSize: 14, color: 'var(--accent)', fontWeight: 600, marginBottom: 8 }}>
              Enviando vídeo... {uploadProgress}%
            </div>
            <div style={{ height: 4, background: 'rgba(37,99,235,0.2)', borderRadius: 2, maxWidth: 300, margin: '0 auto' }}>
              <div style={{ height: '100%', background: 'var(--accent)', borderRadius: 2, width: `${uploadProgress}%`, transition: 'width 0.3s' }} />
            </div>
          </div>
        ) : (
          <div>
            <div style={{ fontSize: 32, marginBottom: 8 }}>📹</div>
            <div style={{ fontSize: 14, color: 'var(--text)', fontWeight: 600, marginBottom: 4 }}>
              Clique para enviar vídeo
            </div>
            <div style={{ fontSize: 12, color: 'var(--muted)' }}>
              MP4, AVI, MOV — O sistema extrai frames automaticamente
            </div>
          </div>
        )}
      </div>

      {/* Upload Buttons */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '24px' }}>
        <button
          onClick={() => setImageUploadModalOpen(true)}
          disabled={uploading}
          style={{
            flex: 1,
            padding: '12px 20px',
            borderRadius: '8px',
            background: 'var(--card)',
            border: '1px solid var(--border)',
            color: 'var(--text)',
            fontSize: '14px',
            fontWeight: '600',
            cursor: uploading ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            transition: 'all 0.15s',
          }}
          onMouseEnter={(e) => {
            if (!uploading) {
              e.currentTarget.style.background = 'var(--bg)';
              e.currentTarget.style.borderColor = 'var(--accent)';
            }
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'var(--card)';
            e.currentTarget.style.borderColor = 'var(--border)';
          }}
        >
          <span>📷</span>
          Upload Imagens
        </button>
      </div>

      {/* Image Upload Modal */}
      <Modal
        isOpen={imageUploadModalOpen}
        onClose={() => setImageUploadModalOpen(false)}
        title="Upload de Imagens"
        size="lg"
      >
        <ImageUploadZone
          onUploadComplete={(response) => {
            console.log('Upload completo:', response);
            loadVideos();
          }}
          onClose={() => setImageUploadModalOpen(false)}
        />
      </Modal>

      {/* Timeline Selector Modal (para vídeos > 10min) */}
      {timelineModal.open && timelineModal.video && (
        <VideoTimelineSelector
          video={{
            id: timelineModal.video.id,
            filename: timelineModal.video.name || timelineModal.video.id?.slice(0, 8),
            duration_seconds: timelineModal.video.duration_seconds || 0,
            storage_path: timelineModal.video.storage_path
          }}
          onExtract={(startTime, endTime) => {
            extractVideoFrames(timelineModal.video.id, startTime, endTime);
          }}
          onExtractFull={() => {
            extractVideoFrames(timelineModal.video.id);
          }}
          onClose={() => setTimelineModal({ open: false, video: null })}
        />
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: 80, color: 'var(--muted)' }}>
          Carregando vídeos...
        </div>
      ) : videos.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 80, color: 'var(--muted)' }}>
          Nenhum vídeo encontrado
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16 }}>
          {videos.map((video) => (
            <div
              key={video.id}
              onClick={() => setSelectedVideoId(video.id)}
              style={{
                background: "var(--card)",
                borderRadius: 14,
                border: "1px solid var(--border)",
                padding: 20,
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
              onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-2px)'}
              onMouseLeave={e => e.currentTarget.style.transform = ''}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                <div style={{
                  width: 48,
                  height: 48,
                  borderRadius: 10,
                  background: 'rgba(37,99,235,0.15)',
                  color: '#2563eb',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 24
                }}>
                  🎬
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  {renamingVideoId === video.id ? (
                    <input
                      type="text"
                      value={renameValue}
                      onChange={(e) => setRenameValue(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleRenameVideo(video.id);
                        if (e.key === 'Escape') setRenamingVideoId(null);
                      }}
                      onBlur={() => handleRenameVideo(video.id)}
                      autoFocus
                      onClick={(e) => e.stopPropagation()}
                      style={{
                        width: '100%',
                        padding: '4px 8px',
                        background: 'rgba(255,255,255,0.9)',
                        border: '2px solid var(--accent)',
                        borderRadius: 6,
                        fontSize: 15,
                        fontWeight: 600,
                        color: 'var(--text)',
                        outline: 'none',
                      }}
                    />
                  ) : (
                    <div style={{ fontSize: 15, fontWeight: 600, color: "var(--text)" }}>
                      {video.name || video.id?.slice(0,8)}
                    </div>
                  )}
                  <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 2 }}>
                    {video.frame_count || 0} frames
                  </div>
                </div>

                {/* Botões de ação */}
                <div style={{ display: 'flex', gap: 4 }}>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setRenamingVideoId(video.id);
                      setRenameValue(video.name || video.id?.slice(0, 8));
                    }}
                    title="Renomear"
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: 8,
                      background: 'rgba(255,255,255,0.8)',
                      border: '1px solid var(--border)',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 14,
                    }}
                  >
                    ✏️
                  </button>
                  <button
                    onClick={(e) => handleDeleteVideo(video.id, e)}
                    title="Excluir vídeo"
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: 8,
                      background: 'rgba(239,68,68,0.1)',
                      border: '1px solid rgba(239,68,68,0.2)',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 14,
                      color: '#ef4444',
                    }}
                  >
                    🗑️
                  </button>
                </div>
              </div>

              <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 12 }}>
                <span style={{ fontSize: 12, color: 'var(--muted)' }}>
                  {video.frame_count || 0} frames • {Math.round((video.duration_seconds || 0) / 60)}min
                </span>
                <span style={{
                  padding: '4px 10px',
                  fontSize: 12,
                  borderRadius: 6,
                  fontWeight: 500,
                  background: video.status === 'completed' ? 'rgba(34,197,94,0.15)' : 'rgba(245,158,11,0.15)',
                  color: video.status === 'completed' ? '#22c55e' : '#f59e0b',
                }}>
                  {video.status === 'completed' ? '✓ Completo' : 'Processando'}
                </span>
              </div>

              {/* Botão Extrair Frames (apenas se não estiver completado) */}
              {video.status !== 'completed' && video.status !== 'extracting' && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleExtractFrames(video);
                  }}
                  style={{
                    width: '100%',
                    padding: '10px 16px',
                    background: 'linear-gradient(135deg, rgba(37,99,235,0.9) 0%, rgba(59,130,246,0.9) 100%)',
                    border: 'none',
                    borderRadius: 8,
                    color: '#fff',
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    marginBottom: 8
                  }}
                  onMouseEnter={(e) => {
                    e.target.style.background = 'linear-gradient(135deg, rgba(37,99,235,1) 0%, rgba(59,130,246,1) 100%)';
                    e.target.style.transform = 'translateY(-1px)';
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.background = 'linear-gradient(135deg, rgba(37,99,235,0.9) 0%, rgba(59,130,246,0.9) 100%)';
                    e.target.style.transform = '';
                  }}
                >
                  🎞️ Extrair Frames
                </button>
              )}

              {/* BOTÃO ANOTAR — visível e claro */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedVideoId(video.id);
                }}
                style={{
                  marginTop: 12,
                  width: '100%',
                  padding: '10px',
                  background: 'rgba(37,99,235,0.8)',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 8,
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                ✏️ Anotar Frames
              </button>
            </div>
          ))}
        </div>
      )}
      </>
      )}
    </div>
  );
};

// ══════════════════════════════════════════════════
// ── TRAINING TRAIN TAB (Treinar) ──
// ══════════════════════════════════════════════════
const TrainingTrainTab = () => {
  const [datasetStats, setDatasetStats] = useState(null);
  const [exportedDatasetPath, setExportedDatasetPath] = useState(null);
  const [activeJob, setActiveJob] = useState(null);
  const [selectedPreset, setSelectedPreset] = useState('balanced');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [starting, setStarting] = useState(false);

  const token = localStorage.getItem('token');

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch('/api/training/dataset/stats', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        if (data.success) {
          setDatasetStats(data.stats);
        } else {
          setError(data.error || 'Failed to load dataset stats');
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, [token]);

  useEffect(() => {
    if (!activeJob || activeJob.status === 'completed' || activeJob.status === 'failed') {
      return;
    }

    const pollInterval = setInterval(async () => {
      try {
        const res = await fetch(`/api/training/status/${activeJob.id}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        if (data.success) {
          setActiveJob(data.job);
        }
      } catch (err) {
        console.error('Poll error:', err);
      }
    }, 5000);

    return () => clearInterval(pollInterval);
  }, [activeJob, token]);

  const handleExport = async () => {
    setExporting(true);
    setError(null);
    try {
      const res = await fetch('/api/training/dataset/export', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.success) {
        setExportedDatasetPath(data.yaml_path);
      } else {
        setError(data.error || 'Failed to export dataset');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setExporting(false);
    }
  };

  const handleStart = async () => {
    if (!exportedDatasetPath) {
      setError('Please export dataset first');
      return;
    }

    setStarting(true);
    setError(null);
    try {
      const res = await fetch('/api/training/start', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: `Training ${new Date().toLocaleString()}`,
          preset: selectedPreset,
          dataset_yaml_path: exportedDatasetPath
        })
      });
      const data = await res.json();
      if (data.success) {
        const statusRes = await fetch(`/api/training/status/${data.job_id}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const statusData = await statusRes.json();
        if (statusData.success) {
          setActiveJob(statusData.job);
        }
      } else {
        setError(data.error || 'Failed to start training');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setStarting(false);
    }
  };

  const handleStop = async () => {
    if (!activeJob) return;
    try {
      await fetch(`/api/training/stop/${activeJob.id}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      setActiveJob(prev => ({ ...prev, status: 'stopped' }));
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 60 }}>
        <div style={{ fontSize: 14, color: 'var(--text-muted)' }}>Carregando estatísticas...</div>
      </div>
    );
  }

  if (error && !datasetStats) {
    return (
      <div style={{ textAlign: 'center', padding: 60 }}>
        <div style={{ color: '#ef4444', marginBottom: 12 }}>{error}</div>
        <button onClick={() => window.location.reload()} style={{
          padding: '10px 20px', borderRadius: 8, background: 'var(--accent)',
          color: '#fff', border: 'none', cursor: 'pointer'
        }}>
          Tentar Novamente
        </button>
      </div>
    );
  }

  if (!datasetStats || datasetStats.total_frames === 0) {
    return (
      <div style={{ textAlign: 'center', padding: 60 }}>
        <p style={{ color: 'var(--text-muted)', marginBottom: 16 }}>
          Nenhum dado de treinamento disponível
        </p>
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
          Faça upload de vídeos ou imagens e anote os frames primeiro
        </p>
      </div>
    );
  }

  const isTraining = activeJob?.status === 'running';
  const progress = activeJob?.progress || 0;
  const jobMetrics = activeJob?.metrics || {};

  // Calculate if requirements are met
  const requirementsMet = datasetStats.total_frames >= 50 && Object.keys(datasetStats.class_distribution || {}).length >= 2;

  return (
    <div>
      {/* Tab 2 - Educational Banner */}
      <div style={{
        background: "linear-gradient(135deg, rgba(37,99,235,0.08) 0%, rgba(124,58,237,0.05) 100%)",
        borderRadius: 16, border: "1px solid rgba(37,99,235,0.2)",
        padding: 24, marginBottom: 28
      }}>
        <div style={{ marginBottom: 16 }}>
          <span style={{
            fontSize: 11, padding: "4px 10px", borderRadius: 6,
            background: "rgba(37,99,235,0.15)", color: "var(--accent)",
            fontWeight: 600, letterSpacing: 0.5, textTransform: "uppercase"
          }}>
            Passo 2 de 3
          </span>
        </div>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--text)", margin: "0 0 12px" }}>
          Configure e inicie o treinamento
        </h2>
        <p style={{ fontSize: 14, color: "var(--text-muted)", lineHeight: 1.6, margin: 0 }}>
          Com os frames anotados, o sistema está pronto para aprender a reconhecer os objetos que você marcou. O treinamento usa o modelo YOLOv8, especializado em detecção de objetos em tempo real. Escolha o preset de acordo com seu tempo disponível e a qualidade necessária.
        </p>
      </div>

      {/* Presets Comparison Table */}
      <div style={{
        background: "var(--card)", borderRadius: 12, border: "1px solid var(--border)",
        padding: 20, marginBottom: 24
      }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: "var(--text)", margin: "0 0 16px" }}>
          Comparação de Presets
        </h3>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <th style={{ padding: '12px 8px', textAlign: 'left', fontWeight: 600, color: 'var(--text)' }}>Preset</th>
                <th style={{ padding: '12px 8px', textAlign: 'left', fontWeight: 600, color: 'var(--text)' }}>Modelo</th>
                <th style={{ padding: '12px 8px', textAlign: 'left', fontWeight: 600, color: 'var(--text)' }}>Épocas</th>
                <th style={{ padding: '12px 8px', textAlign: 'left', fontWeight: 600, color: 'var(--text)' }}>Tempo estimado</th>
                <th style={{ padding: '12px 8px', textAlign: 'left', fontWeight: 600, color: 'var(--text)' }}>Quando usar</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <td style={{ padding: '12px 8px' }}>⚡ <strong>Rápido</strong></td>
                <td style={{ padding: '12px 8px', fontFamily: "'DM Mono', monospace" }}>YOLOv8n</td>
                <td style={{ padding: '12px 8px' }}>50</td>
                <td style={{ padding: '12px 8px' }}>~15 minutos</td>
                <td style={{ padding: '12px 8px', color: 'var(--text-muted)' }}>Testes iniciais, poucos dados</td>
              </tr>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <td style={{ padding: '12px 8px' }}>⚖️ <strong>Balanceado</strong></td>
                <td style={{ padding: '12px 8px', fontFamily: "'DM Mono', monospace" }}>YOLOv8s</td>
                <td style={{ padding: '12px 8px' }}>100</td>
                <td style={{ padding: '12px 8px' }}>~45 minutos</td>
                <td style={{ padding: '12px 8px', color: 'var(--text-muted)' }}>Uso geral, recomendado</td>
              </tr>
              <tr>
                <td style={{ padding: '12px 8px' }}>🏆 <strong>Qualidade</strong></td>
                <td style={{ padding: '12px 8px', fontFamily: "'DM Mono', monospace" }}>YOLOv8m</td>
                <td style={{ padding: '12px 8px' }}>150</td>
                <td style={{ padding: '12px 8px' }}>~2 horas</td>
                <td style={{ padding: '12px 8px', color: 'var(--text-muted)' }}>Produção, dataset grande</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Requirements Disclaimer */}
      <div style={{
        background: requirementsMet ? "rgba(34,197,94,0.08)" : "rgba(239,68,68,0.08)",
        borderRadius: 12, border: requirementsMet ? "1px solid rgba(34,197,94,0.3)" : "1px solid rgba(239,68,68,0.3)",
        padding: 20, marginBottom: 24
      }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
          <div style={{ fontSize: 24 }}>{requirementsMet ? '✅' : '⚠️'}</div>
          <div style={{ flex: 1 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, color: requirementsMet ? '#22c55e' : '#ef4444', margin: "0 0 8px" }}>
              {requirementsMet ? 'Dataset pronto para treinamento' : 'Requisitos mínimos não atendidos'}
            </h3>
            <ul style={{ fontSize: 13, color: "var(--text-muted)", margin: 0, paddingLeft: 20, lineHeight: 1.8 }}>
              <li>
                <strong>Frames anotados:</strong> {datasetStats.total_frames}/50 {' '}
                {datasetStats.total_frames >= 50 ? '✓' : `✗ (falta: ${50 - datasetStats.total_frames})`}
              </li>
              <li>
                <strong>Classes com anotações:</strong> {Object.keys(datasetStats.class_distribution || {}).length}/2 {' '}
                {Object.keys(datasetStats.class_distribution || {}).length >= 2 ? '✓' : `✗ (falta: ${2 - Object.keys(datasetStats.class_distribution || {}).length})`}
              </li>
              <li>
                <strong>Exemplos por classe:</strong> {datasetStats.total_frames > 0 && Object.keys(datasetStats.class_distribution || {}).length > 0
                  ? Math.round(datasetStats.total_frames / Object.keys(datasetStats.class_distribution || {}).length)
                  : 0}/10 {' '}
                {datasetStats.total_frames > 0 && Object.keys(datasetStats.class_distribution || {}).length > 0 && Math.round(datasetStats.total_frames / Object.keys(datasetStats.class_distribution || {}).length) >= 10 ? '✓' : '✗'}
              </li>
            </ul>
            {!requirementsMet && (
              <div style={{ marginTop: 12, padding: 12, background: 'rgba(239,68,68,0.1)', borderRadius: 8, fontSize: 12 }}>
                ❌ Para treinar, volte à aba <strong>Vídeos & Dados</strong> e anote mais frames antes de continuar.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Technical Disclaimer (Collapsible) */}
      <details style={{ marginBottom: 24 }}>
        <summary style={{
          cursor: 'pointer', fontSize: 13, fontWeight: 500, color: 'var(--accent)',
          padding: '8px 0', userSelect: 'none'
        }}>
          ℹ️ O que acontece durante o treinamento?
        </summary>
        <div style={{ marginTop: 12, padding: 16, background: 'var(--bg)', borderRadius: 8, fontSize: 13, lineHeight: 1.7 }}>
          <p style={{ margin: '0 0 12px' }}>
            O sistema divide seus dados em <strong>80% para treino</strong> e <strong>20% para validação</strong>.
            A cada época, o modelo ajusta seus parâmetros para melhorar a detecção. As métricas mostradas durante o treino significam:
          </p>
          <ul style={{ margin: '0 0 12px', paddingLeft: 20 }}>
            <li><strong>mAP@50:</strong> precisão geral do modelo (quanto maior, melhor — ideal acima de 0.7)</li>
            <li><strong>Precisão:</strong> dos objetos detectados, quantos são corretos</li>
            <li><strong>Recall:</strong> dos objetos reais, quantos foram detectados</li>
          </ul>
          <p style={{ margin: 0 }}>
            O treinamento pode ser interrompido e retomado. O modelo é salvo automaticamente ao final.
          </p>
        </div>
      </details>

      <div style={{
        background: "var(--card)", borderRadius: 16, border: "1px solid var(--border)",
        padding: 24, marginBottom: 20, animation: "fadeSlideUp 0.5s ease both",
      }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, color: "var(--text)", margin: "0 0 16px" }}>Dataset</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 16 }}>
          <div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Frames Anotados</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--text)' }}>{datasetStats.total_frames}</div>
          </div>
          <div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Bounding Boxes</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--text)' }}>{datasetStats.total_boxes}</div>
          </div>
          <div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Classes</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--text)' }}>{Object.keys(datasetStats.class_distribution || {}).length}</div>
          </div>
          <div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Split</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--text)' }}>
              {datasetStats.train_split}/{datasetStats.val_split}
            </div>
          </div>
        </div>
        <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
          {!exportedDatasetPath ? (
            <button
              onClick={handleExport}
              disabled={exporting || datasetStats.total_frames === 0}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '10px 20px', borderRadius: 8,
                background: exporting ? 'var(--border)' : 'var(--accent)',
                color: '#fff', border: 'none', cursor: exporting ? 'not-allowed' : 'pointer',
                fontSize: 14, fontWeight: 600, opacity: datasetStats.total_frames === 0 ? 0.5 : 1
              }}
            >
              {exporting ? 'Exportando...' : 'Exportar Dataset'}
            </button>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 13, color: '#22c55e', fontWeight: 500 }}>
                ✓ Dataset exportado: {exportedDatasetPath.split('/').slice(-2).join('/')}
              </span>
              <button
                onClick={() => setExportedDatasetPath(null)}
                style={{ fontSize: 12, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}
              >
                Reexportar
              </button>
            </div>
          )}
        </div>
      </div>

      <div style={{
        background: "var(--card)", borderRadius: 16, border: "1px solid var(--border)",
        padding: 28, marginBottom: 24, animation: "fadeSlideUp 0.5s ease both",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20, flexWrap: "wrap", gap: 12 }}>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 600, color: "var(--text)", margin: 0 }}>
              {isTraining ? "Treinamento em andamento..." : progress >= 100 ? "Treinamento concluído!" : "Iniciar Treinamento"}
            </h2>
            <p style={{ fontSize: 13, color: "var(--text-muted)", margin: "4px 0 0" }}>
              {!activeJob && `Dataset: ${datasetStats.total_frames} frames · ${Object.keys(datasetStats.class_distribution || {}).length} classes`}
              {activeJob && `Epoch ${activeJob.current_epoch || 0}/${activeJob.epochs} · ${activeJob.preset}`}
            </p>
          </div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            {!isTraining && !activeJob && (
              <select
                value={selectedPreset}
                onChange={(e) => setSelectedPreset(e.target.value)}
                disabled={!exportedDatasetPath}
                style={{
                  padding: '10px 16px', borderRadius: 8,
                  background: 'var(--bg)', color: 'var(--text)',
                  border: '1px solid var(--border)', fontSize: 14,
                  cursor: !exportedDatasetPath ? 'not-allowed' : 'pointer'
                }}
              >
                <option value="fast">Rápido (YOLOv8n, 50 ep)</option>
                <option value="balanced">Equilibrado (YOLOv8s, 100 ep)</option>
                <option value="quality">Qualidade (YOLOv8m, 150 ep)</option>
              </select>
            )}
            <button
              onClick={isTraining ? handleStop : handleStart}
              disabled={!exportedDatasetPath && !isTraining}
              style={{
                display: "flex", alignItems: "center", gap: 8,
                padding: "10px 24px", borderRadius: 10,
                background: isTraining ? "#ef444420" : progress >= 100 ? "#22c55e" : !exportedDatasetPath ? "var(--border)" : "var(--accent)",
                color: isTraining ? "#ef4444" : "#fff",
                border: isTraining ? "1px solid #ef444440" : "none",
                fontSize: 14, fontWeight: 600, cursor: (!exportedDatasetPath && !isTraining) ? "not-allowed" : "pointer",
                opacity: (!exportedDatasetPath && !isTraining) ? 0.5 : 1
              }}
            >
              {starting ? 'Iniciando...' : isTraining ? Icons.x : Icons.play}
              {starting ? '' : isTraining ? "Parar" : progress >= 100 ? "Novo Treinamento" : "Iniciar"}
            </button>
          </div>
        </div>

        <div style={{ background: "var(--bg)", borderRadius: 8, height: 8, overflow: "hidden", marginBottom: 8 }}>
          <div style={{
            height: "100%", borderRadius: 8,
            background: progress >= 100 ? "#22c55e" : activeJob?.status === 'failed' ? "#ef4444" : "var(--accent)",
            width: `${progress}%`,
            transition: "width 0.3s ease",
          }} />
        </div>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span style={{ fontSize: 12, color: "var(--text-muted)", fontFamily: "'DM Mono', monospace" }}>
            {activeJob ? `Epoch ${activeJob.current_epoch || 0}/${activeJob.epochs}` : '-'}
          </span>
          <span style={{ fontSize: 12, color: "var(--text-muted)", fontFamily: "'DM Mono', monospace" }}>
            {progress.toFixed(1)}%
          </span>
        </div>
        {activeJob?.error_message && (
          <div style={{ marginTop: 12, padding: 12, background: '#ef444420', borderRadius: 8, fontSize: 13, color: '#ef4444' }}>
            ❌ {activeJob.error_message}
          </div>
        )}
      </div>

      {activeJob && Object.keys(jobMetrics).length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 14 }}>
          {[
            { label: "Precisão", value: jobMetrics.precision ? (jobMetrics.precision * 100).toFixed(1) + '%' : '-' },
            { label: "Recall", value: jobMetrics.recall ? (jobMetrics.recall * 100).toFixed(1) + '%' : '-' },
            { label: "mAP@50", value: jobMetrics.mAP50?.toFixed(3) || '-' },
            { label: "mAP@95", value: jobMetrics.mAP95?.toFixed(3) || '-' },
          ].map((m, i) => (
            <div key={i} style={{
              background: "var(--card)", borderRadius: 14, border: "1px solid var(--border)",
              padding: 20, animation: `fadeSlideUp 0.4s ease ${0.1 + i * 0.05}s both`,
            }}>
              <div style={{ fontSize: 12, color: "var(--text-muted)", fontWeight: 500, marginBottom: 6 }}>{m.label}</div>
              <div style={{ fontSize: 26, fontWeight: 700, color: "var(--text)", fontFamily: "'DM Sans', sans-serif" }}>{m.value}</div>
            </div>
          ))}
        </div>
      )}

      {error && datasetStats && (
        <div style={{
          marginTop: 20, padding: 16, background: '#ef444420', borderRadius: 10,
          border: '1px solid #ef444440', fontSize: 14, color: '#ef4444'
        }}>
          {error}
        </div>
      )}
    </div>
  );
};

// ══════════════════════════════════════════════════
// ── TRAINING HISTORY TAB (Histórico) ──
// ══════════════════════════════════════════════════
const TrainingHistoryTab = () => {
  const [jobs, setJobs] = useState([]);
  const [activeModel, setActiveModel] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedJob, setSelectedJob] = useState(null);

  const token = localStorage.getItem('token');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const historyRes = await fetch('/api/training/history', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const historyData = await historyRes.json();
        if (historyData.success) {
          setJobs(historyData.jobs);
        } else {
          setError(historyData.error || 'Failed to load training history');
        }

        const activeRes = await fetch('/api/training/models/active', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const activeData = await activeRes.json();
        if (activeData.success && activeData.model) {
          setActiveModel(activeData.model);
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [token]);

  const handleActivate = async (modelId) => {
    try {
      const res = await fetch(`/api/training/models/${modelId}/activate`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.success) {
        setActiveModel(data.model);
        const historyRes = await fetch('/api/training/history', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const historyData = await historyRes.json();
        if (historyData.success) {
          setJobs(historyData.jobs);
        }
      } else {
        setError(data.error || 'Failed to activate model');
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const getStatusBadge = (status) => {
    const colors = {
      'pending': '#f59e0b',
      'running': '#3b82f6',
      'completed': '#22c55e',
      'failed': '#ef4444',
      'stopped': '#6b7280'
    };
    const labels = {
      'pending': 'Pendente',
      'running': 'Em andamento',
      'completed': 'Concluído',
      'failed': 'Falhou',
      'stopped': 'Parado'
    };
    return {
      color: colors[status] || '#6b7280',
      label: labels[status] || status
    };
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString('pt-BR');
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 60 }}>
        <div style={{ fontSize: 14, color: 'var(--text-muted)' }}>Carregando histórico...</div>
      </div>
    );
  }

  if (error && jobs.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: 60 }}>
        <div style={{ color: '#ef4444', marginBottom: 12 }}>{error}</div>
        <button onClick={() => window.location.reload()} style={{
          padding: '10px 20px', borderRadius: 8, background: 'var(--accent)',
          color: '#fff', border: 'none', cursor: 'pointer'
        }}>
          Tentar Novamente
        </button>
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div>
        {/* Enhanced Empty State */}
        <div style={{ textAlign: 'center', padding: 80, maxWidth: 500, margin: '0 auto' }}>
          <div style={{ fontSize: 64, marginBottom: 16 }}>🤖</div>
          <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--text)", margin: "0 0 12px" }}>
            Nenhum modelo treinado ainda
          </h2>
          <p style={{ fontSize: 14, color: "var(--text-muted)", marginBottom: 24 }}>
            Para treinar seu primeiro modelo, siga estes passos:
          </p>
          <div style={{ textAlign: 'left', maxWidth: 350, margin: '0 auto 24px' }}>
            <div style={{ display: 'flex', gap: 12, marginBottom: 16, alignItems: 'flex-start' }}>
              <div style={{
                width: 28, height: 28, borderRadius: '50%', background: 'var(--accent)',
                color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 14, fontWeight: 600, flexShrink: 0
              }}>
                1
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-muted)', paddingTop: 4 }}>
                Vá para a aba <strong>"Vídeos & Dados"</strong> e envie vídeos da operação
              </div>
            </div>
            <div style={{ display: 'flex', gap: 12, marginBottom: 16, alignItems: 'flex-start' }}>
              <div style={{
                width: 28, height: 28, borderRadius: '50%', background: 'var(--accent)',
                color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 14, fontWeight: 600, flexShrink: 0
              }}>
                2
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-muted)', paddingTop: 4 }}>
                Extraia e anote os frames com os objetos de interesse
              </div>
            </div>
            <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
              <div style={{
                width: 28, height: 28, borderRadius: '50%', background: 'var(--accent)',
                color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 14, fontWeight: 600, flexShrink: 0
              }}>
                3
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-muted)', paddingTop: 4 }}>
                Volte para a aba <strong>"Treinar"</strong> e inicie o treinamento
              </div>
            </div>
          </div>
          <button
            onClick={() => document.querySelector('[onClick*="setTrainingTab"]')?.click()}
            style={{
              padding: '12px 24px', borderRadius: 8, background: 'var(--accent)',
              color: '#fff', border: 'none', fontSize: 14, fontWeight: 600, cursor: 'pointer'
            }}
          >
            Ir para Vídeos & Dados
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Tab 3 - Educational Banner */}
      <div style={{
        background: "linear-gradient(135deg, rgba(37,99,235,0.08) 0%, rgba(124,58,237,0.05) 100%)",
        borderRadius: 16, border: "1px solid rgba(37,99,235,0.2)",
        padding: 24, marginBottom: 28
      }}>
        <div style={{ marginBottom: 16 }}>
          <span style={{
            fontSize: 11, padding: "4px 10px", borderRadius: 6,
            background: "rgba(37,99,235,0.15)", color: "var(--accent)",
            fontWeight: 600, letterSpacing: 0.5, textTransform: "uppercase"
          }}>
            Passo 3 de 3
          </span>
        </div>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--text)", margin: "0 0 12px" }}>
          Gerencie e ative seus modelos
        </h2>
        <p style={{ fontSize: 14, color: "var(--text-muted)", lineHeight: 1.6, margin: 0 }}>
          Aqui ficam todos os modelos que você treinou. Apenas um modelo pode estar ativo por vez — é ele que será usado pelas câmeras para detectar objetos em tempo real. Você pode comparar modelos, ativar o melhor e fazer download para backup.
        </p>
      </div>

      {/* Educational Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16, marginBottom: 28 }}>
        {/* Card 1 - Métricas */}
        <div style={{
          background: "var(--card)", borderRadius: 12, border: "1px solid var(--border)",
          padding: 20
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
            <div style={{ fontSize: 28 }}>📊</div>
            <h3 style={{ fontSize: 15, fontWeight: 600, color: "var(--text)", margin: 0 }}>Entendendo as métricas</h3>
          </div>
          <ul style={{ fontSize: 13, color: "var(--text-muted)", margin: 0, paddingLeft: 20, lineHeight: 1.8 }}>
            <li><strong>mAP@50 &gt; 0.7:</strong> modelo bom para produção</li>
            <li><strong>mAP@50 &gt; 0.5:</strong> funcional, mais dados recomendados</li>
            <li><strong>mAP@50 &lt; 0.5:</strong> fraco, retreinar com mais dados</li>
            <li><strong>Mais epochs e dados</strong> = melhor resultado</li>
          </ul>
        </div>

        {/* Card 2 - Modelo Ativo */}
        <div style={{
          background: "var(--card)", borderRadius: 12, border: "1px solid var(--border)",
          padding: 20
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
            <div style={{ fontSize: 28 }}>🟢</div>
            <h3 style={{ fontSize: 15, fontWeight: 600, color: "var(--text)", margin: 0 }}>Modelo ativo</h3>
          </div>
          <ul style={{ fontSize: 13, color: "var(--text-muted)", margin: 0, paddingLeft: 20, lineHeight: 1.8 }}>
            <li>É o modelo usado pelas câmeras agora</li>
            <li>Só um modelo pode estar ativo por vez</li>
            <li>Ativar novo modelo substitui o anterior</li>
            <li>O anterior fica salvo no histórico</li>
          </ul>
        </div>

        {/* Card 3 - Boas Práticas */}
        <div style={{
          background: "var(--card)", borderRadius: 12, border: "1px solid var(--border)",
          padding: 20
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
            <div style={{ fontSize: 28 }}>💡</div>
            <h3 style={{ fontSize: 15, fontWeight: 600, color: "var(--text)", margin: 0 }}>Dicas</h3>
          </div>
          <ul style={{ fontSize: 13, color: "var(--text-muted)", margin: 0, paddingLeft: 20, lineHeight: 1.8 }}>
            <li>Treine novamente ao adicionar novas classes</li>
            <li>Compare mAP@50 antes de ativar novo modelo</li>
            <li>Faça download do melhor modelo como backup</li>
            <li>Datasets maiores geram modelos mais precisos</li>
          </ul>
        </div>
      </div>

      {activeModel && (
        <div style={{
          background: "rgba(34, 197, 94, 0.1)", borderRadius: 12, border: "1px solid rgba(34, 197, 94, 0.3)",
          padding: 16, marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center'
        }}>
          <div>
            <div style={{ fontSize: 13, color: '#22c55e', fontWeight: 600, marginBottom: 4 }}>🚀 Modelo Ativo</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text)' }}>{activeModel.name}</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
              {activeModel.model_size} · Criado em {formatDate(activeModel.created_at)}
            </div>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {jobs.map((job, index) => {
          const statusBadge = getStatusBadge(job.status);
          const isActive = activeModel?.id === job.model_id;
          const jobMetrics = job.metrics || {};

          return (
            <div
              key={job.id}
              style={{
                background: "var(--card)", borderRadius: 14, border: "1px solid var(--border)",
                padding: 20, cursor: 'pointer', transition: 'all 0.2s',
                ...(selectedJob === job.id ? { borderColor: 'var(--accent)', borderWidth: 2 } : {})
              }}
              onClick={() => setSelectedJob(selectedJob === job.id ? null : job.id)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--text)", margin: 0 }}>
                      {job.name}
                    </h3>
                    {isActive && (
                      <span style={{
                        fontSize: 11, padding: '2px 8px', borderRadius: 4,
                        background: '#22c55e', color: '#fff', fontWeight: 600
                      }}>
                        ATIVO
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text-muted)', fontFamily: "'DM Mono', monospace" }}>
                    {job.preset} · YOLOv8{job.model_size} · {job.epochs} epochs
                  </div>
                </div>
                <div style={{
                  padding: '4px 12px', borderRadius: 6,
                  background: `${statusBadge.color}20`, color: statusBadge.color,
                  fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap'
                }}>
                  {statusBadge.label}
                </div>
              </div>

              {job.status === 'running' && (
                <div style={{ marginBottom: 12 }}>
                  <div style={{ background: 'var(--bg)', borderRadius: 6, height: 6, overflow: 'hidden' }}>
                    <div style={{
                      height: '100%', borderRadius: 6,
                      background: 'var(--accent)', width: `${job.progress}%`,
                      transition: 'width 0.3s ease'
                    }} />
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4, fontFamily: "'DM Mono', monospace" }}>
                    Epoch {job.current_epoch || 0}/{job.epochs} · {job.progress.toFixed(1)}%
                  </div>
                </div>
              )}

              {selectedJob === job.id && (
                <div style={{
                  paddingTop: 12, marginTop: 12, borderTop: '1px solid var(--border)',
                  animation: 'fadeSlideUp 0.3s ease both'
                }}>
                  {Object.keys(jobMetrics).length > 0 && (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 12, marginBottom: 16 }}>
                      {[
                        { label: 'Precisão', value: jobMetrics.precision ? (jobMetrics.precision * 100).toFixed(1) + '%' : '-' },
                        { label: 'Recall', value: jobMetrics.recall ? (jobMetrics.recall * 100).toFixed(1) + '%' : '-' },
                        { label: 'mAP@50', value: jobMetrics.mAP50?.toFixed(3) || '-' },
                        { label: 'mAP@95', value: jobMetrics.mAP95?.toFixed(3) || '-' },
                      ].map((m, i) => (
                        <div key={i}>
                          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 2 }}>{m.label}</div>
                          <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)', fontFamily: "'DM Sans', sans-serif" }}>{m.value}</div>
                        </div>
                      ))}
                    </div>
                  )}

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12, fontSize: 12, color: 'var(--text-muted)' }}>
                    <div>
                      <span style={{ fontWeight: 500 }}>Criado em:</span> {formatDate(job.created_at)}
                    </div>
                    <div>
                      <span style={{ fontWeight: 500 }}>Iniciado:</span> {formatDate(job.started_at)}
                    </div>
                    <div>
                      <span style={{ fontWeight: 500 }}>Concluído:</span> {formatDate(job.completed_at)}
                    </div>
                  </div>

                  {job.error_message && (
                    <div style={{
                      marginTop: 12, padding: 10, background: '#ef444420',
                      borderRadius: 6, fontSize: 12, color: '#ef4444'
                    }}>
                      ❌ {job.error_message}
                    </div>
                  )}

                  <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
                    {job.status === 'completed' && job.model_id && !isActive && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleActivate(job.model_id);
                        }}
                        style={{
                          padding: '8px 16px', borderRadius: 6, background: '#22c55e',
                          color: '#fff', border: 'none', fontSize: 13, fontWeight: 600, cursor: 'pointer'
                        }}
                      >
                        Ativar Modelo
                      </button>
                    )}
                  </div>
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12, color: 'var(--text-muted)' }}>
                <span>Criado em {formatDate(job.created_at)}</span>
                {selectedJob !== job.id && (
                  <span style={{ color: 'var(--accent)', fontWeight: 500 }}>
                    Ver detalhes
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {error && jobs.length > 0 && (
        <div style={{
          marginTop: 20, padding: 16, background: '#ef444420', borderRadius: 10,
          border: '1px solid #ef444440', fontSize: 14, color: '#ef4444'
        }}>
          {error}
        </div>
      )}
    </div>
  );
};

// ══════════════════════════════════════════════════
// ── MONITORING PAGE — Drag & Drop + Seleção ──
// ══════════════════════════════════════════════════
const MonitoringPage = () => {
  const [selectedIds, setSelectedIds] = useState([1, 2, 4, 5, 6, 7]);
  const [orderedIds, setOrderedIds] = useState([1, 2, 4, 5, 6, 7]);
  const [grid, setGrid] = useState("3x3");
  const [panelOpen, setPanelOpen] = useState(false);
  const [time, setTime] = useState(new Date());
  const [fullscreenCam, setFullscreenCam] = useState(null);
  const [searchPanel, setSearchPanel] = useState("");
  const [isMobileView, setIsMobileView] = useState(false);
  const [dragIdx, setDragIdx] = useState(null);
  const [dragOverIdx, setDragOverIdx] = useState(null);
  const [slideshowIndex, setSlideshowIndex] = useState(0);

  // Initialize with online cameras from DEMO_CAMERAS
  useEffect(() => {
    const onlineCameras = DEMO_CAMERAS.filter(c => c.status === "online").map(c => c.id);
    setSelectedIds(onlineCameras.slice(0, 6));
    setOrderedIds(onlineCameras.slice(0, 6));
  }, []);

  useEffect(() => { const t = setInterval(() => setTime(new Date()), 1000); return () => clearInterval(t); }, []);
  useEffect(() => { const c = () => setIsMobileView(window.innerWidth < 640); c(); window.addEventListener("resize", c); return () => window.removeEventListener("resize", c); }, []);

  // Slideshow: troca frame a cada 5 segundos
  useEffect(() => {
    if (SLIDESHOW_FRAMES.length === 0) return;
    const interval = setInterval(() => {
      setSlideshowIndex(prev => (prev + 1) % SLIDESHOW_FRAMES.length);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const toggleCamera = (id) => {
    setSelectedIds(prev => {
      const next = prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id];
      setOrderedIds(ord => {
        if (next.includes(id) && !ord.includes(id)) return [...ord, id];
        if (!next.includes(id)) return ord.filter(x => x !== id);
        return ord;
      });
      return next;
    });
  };

  const handleDragStart = (idx) => setDragIdx(idx);
  const handleDragOver = (e, idx) => { e.preventDefault(); setDragOverIdx(idx); };
  const handleDrop = (idx) => {
    if (dragIdx === null || dragIdx === idx) { setDragIdx(null); setDragOverIdx(null); return; }
    setOrderedIds(prev => { const n = [...prev]; const [m] = n.splice(dragIdx, 1); n.splice(idx, 0, m); return n; });
    setDragIdx(null); setDragOverIdx(null);
  };
  const handleDragEnd = () => { setDragIdx(null); setDragOverIdx(null); };

  const cols = grid === "1x1" ? 1 : grid === "2x2" ? 2 : grid === "3x3" ? 3 : 4;
  const displayCameras = orderedIds.map(id => DEMO_CAMERAS.find(c => c.id === id)).filter(Boolean);
  const filteredPanel = DEMO_CAMERAS.filter(c => c.name.toLowerCase().includes(searchPanel.toLowerCase()) || (c.location && c.location.toLowerCase().includes(searchPanel.toLowerCase())));

  const CamCell = ({ cam }) => {
    const isOn = cam.status === "online";
    const detection = CAMERA_DETECTIONS[cam.id];

    // Frame para exibir (próprio ou slideshow com offset)
    const frameToShow = cam.frameId
      ? cam.frameId
      : SLIDESHOW_FRAMES.length > 0
        ? SLIDESHOW_FRAMES[(slideshowIndex + cam.id) % SLIDESHOW_FRAMES.length]
        : null;

    return (
      <div
        draggable
        onDragStart={() => handleDragStart(displayCameras.indexOf(cam))}
        onDragOver={(e) => handleDragOver(e, displayCameras.indexOf(cam))}
        onDrop={() => handleDrop(displayCameras.indexOf(cam))}
        onDragEnd={handleDragEnd}
        style={{
          borderRadius: 6, overflow: "hidden", background: "#0a0e1a",
          aspectRatio: cols <= 2 ? "16/9" : "16/10", position: "relative",
          border: "1px solid rgba(255,255,255,0.05)",
          cursor: "grab",
        }}
      >
        {/* ── BACKGROUND IMAGE ── */}
        {isOn && frameToShow ? (
          <div style={{ position: "absolute", inset: 0 }}>
            <img
              src={`/api/training/frames/${frameToShow}/image`}
              alt={cam.name}
              style={{
                width: "100%", height: "100%", objectFit: "cover",
                filter: "brightness(0.65) contrast(1.1) saturate(0.9)",
                pointerEvents: "none",
              }}
              onError={(e) => { e.target.style.display = "none"; }}
              draggable={false}
            />
            {/* Scanlines */}
            <div style={{ position: "absolute", inset: 0, background: "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.04) 2px, rgba(0,0,0,0.04) 4px)", pointerEvents: "none" }} />
            {/* Vignette */}
            <div style={{ position: "absolute", inset: 0, background: "radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,0.5) 100%)", pointerEvents: "none" }} />
          </div>
        ) : isOn ? (
          <div style={{ position: "absolute", inset: 0, background: "linear-gradient(135deg, #080c15, #0f1729)" }}>
            <div style={{ position: "absolute", inset: 0, background: "repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(255,255,255,0.006) 3px, rgba(255,255,255,0.006) 4px)" }} />
          </div>
        ) : (
          <div style={{ position: "absolute", inset: 0, background: "#0e0e0e", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <span style={{ fontSize: 10, color: "rgba(255,255,255,0.15)", fontFamily: "var(--mono)", letterSpacing: 2 }}>SEM SINAL</span>
          </div>
        )}

        {/* ── TOP BAR: Nome + REC ── */}
        <div style={{
          position: "absolute", top: 0, left: 0, right: 0, zIndex: 5,
          padding: "8px 10px 16px",
          background: "linear-gradient(180deg, rgba(0,0,0,0.7) 0%, transparent 100%)",
          display: "flex", justifyContent: "space-between", alignItems: "flex-start",
        }}>
          <span style={{ fontSize: 11, fontWeight: 600, color: "rgba(255,255,255,0.95)", textShadow: "0 1px 3px rgba(0,0,0,0.8)" }}>
            {cam.name}
          </span>
          {isOn && (
            <div style={{ display: "flex", alignItems: "center", gap: 3, background: "rgba(220,38,38,0.85)", padding: "1px 5px", borderRadius: 3, fontSize: 8, fontWeight: 700, color: "#fff", fontFamily: "var(--mono)" }}>
              <span style={{ width: 4, height: 4, borderRadius: "50%", background: "#fff", animation: "pulse 1.5s infinite" }} />
              REC
            </div>
          )}
        </div>

        {/* ── BOTTOM BAR: Dados YOLO + Info ── */}
        <div style={{
          position: "absolute", bottom: 0, left: 0, right: 0, zIndex: 5,
          background: "linear-gradient(0deg, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.4) 70%, transparent 100%)",
          padding: "20px 10px 6px",
        }}>
          {/* Linha 1: Status + Placa (se tem detecção) */}
          {isOn && detection && detection.status !== "idle" && (
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4, flexWrap: "wrap" }}>
              {/* Badge de status */}
              <span style={{
                display: "inline-flex", alignItems: "center", gap: 3,
                padding: "1px 6px", borderRadius: 3, fontSize: 8, fontWeight: 700,
                textTransform: "uppercase", letterSpacing: 0.5,
                fontFamily: "var(--mono)",
                background: detection.status === "counting" ? "rgba(34,197,94,0.25)"
                  : detection.status === "completed" ? "rgba(37,99,235,0.25)"
                  : detection.status === "validating" ? "rgba(245,158,11,0.25)"
                  : "rgba(107,114,128,0.25)",
                color: detection.status === "counting" ? "#4ade80"
                  : detection.status === "completed" ? "#60a5fa"
                  : detection.status === "validating" ? "#fbbf24"
                  : "#9ca3af",
                border: `1px solid ${
                  detection.status === "counting" ? "rgba(34,197,94,0.3)"
                  : detection.status === "completed" ? "rgba(37,99,235,0.3)"
                  : detection.status === "validating" ? "rgba(245,158,11,0.3)"
                  : "rgba(107,114,128,0.3)"
                }`,
              }}>
                <span style={{
                  width: 4, height: 4, borderRadius: "50%",
                  background: detection.status === "counting" ? "#4ade80" : detection.status === "completed" ? "#60a5fa" : detection.status === "validating" ? "#fbbf24" : "#9ca3af",
                  animation: detection.status === "counting" ? "pulse 1.5s infinite" : "none",
                }} />
                {detection.status === "counting" ? "Contando" : detection.status === "completed" ? "Concluído" : detection.status === "validating" ? "Validando" : "Idle"}
              </span>

              {/* Placa */}
              {detection.truck_plate && (
                <span style={{
                  fontSize: 10, fontWeight: 700, color: "#fff",
                  fontFamily: "var(--mono)", background: "rgba(255,255,255,0.15)",
                  padding: "1px 5px", borderRadius: 3, letterSpacing: 0.5,
                }}>
                  🚛 {detection.truck_plate}
                </span>
              )}

              {/* Link com outra câmera */}
              {detection.linked_camera && (
                <span style={{ fontSize: 7, color: "rgba(245,158,11,0.9)", fontFamily: "var(--mono)" }}>
                  = CAM{detection.linked_camera}
                </span>
              )}
            </div>
          )}

          {/* Linha 2: Horários em destaque */}
          {detection && detection.start_time && (
            <div style={{ display: "flex", gap: 12, marginBottom: 3, fontSize: 9, fontFamily: "var(--mono)" }}>
              <span style={{ color: "rgba(255,255,255,0.5)" }}>
                ⏱ Início <span style={{ color: "#fff", fontWeight: 600 }}>{detection.start_time}</span>
              </span>
              <span style={{ color: "rgba(255,255,255,0.5)" }}>
                Tempo <span style={{
                  color: detection.status === "completed" ? "#60a5fa" : "#fbbf24",
                  fontWeight: 700, fontSize: 10,
                }}>{detection.elapsed}</span>
              </span>
            </div>
          )}

          {/* Linha 3: Produtos + Confiança */}
          {detection && detection.products_counted > 0 && (
            <div style={{ display: "flex", gap: 8, marginBottom: 3, fontSize: 9, fontFamily: "var(--mono)" }}>
              <span style={{ color: "rgba(255,255,255,0.6)" }}>
                📦 <span style={{ color: "#4ade80", fontWeight: 700, fontSize: 10 }}>{detection.products_counted}</span> produtos
              </span>
              <span style={{ color: "rgba(255,255,255,0.3)" }}>·</span>
              <span style={{ color: detection.confidence > 90 ? "#4ade80" : detection.confidence > 70 ? "#fbbf24" : "#f87171" }}>
                {detection.confidence}%
              </span>
            </div>
          )}

          {/* Linha alternativa: AGUARDANDO (sem detecção) */}
          {isOn && (!detection || detection.status === "idle") && (
            <div style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: 3 }}>
              <span style={{ width: 4, height: 4, borderRadius: "50%", background: "#6b7280" }} />
              <span style={{ fontSize: 8, color: "rgba(255,255,255,0.3)", fontFamily: "var(--mono)" }}>AGUARDANDO</span>
            </div>
          )}

          {/* Linha 3: Info da câmera (sempre visível) */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 8, color: "rgba(255,255,255,0.3)", fontFamily: "var(--mono)" }}>
              {cam.location} · {cam.ip}
            </span>
            <span style={{ fontSize: 8, color: "rgba(255,255,255,0.3)", fontFamily: "var(--mono)" }}>
              {cam.resolution} {time.toLocaleTimeString("pt-BR")}
            </span>
          </div>
        </div>
      </div>
    );
  };

  // ── LAYOUT SEM MARGIN NEGATIVO ──
  return (
    <div style={{ display: "flex", height: "calc(100vh - 60px)", background: "#0d1117" }}>
      {/* Grid Area */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", background: "#0d1117" }}>
        {/* Toolbar */}
        <div style={{ padding: "10px 14px", display: "flex", justifyContent: "space-between", alignItems: "center", background: "#161b22", borderBottom: "1px solid rgba(255,255,255,0.05)", flexWrap: "wrap", gap: 8 }}>
          <div>
            <h1 style={{ fontSize: isMobileView ? 15 : 17, fontWeight: 700, color: "#fff", margin: 0 }}>Monitoramento</h1>
            <p style={{ fontSize: 11, color: "rgba(255,255,255,0.35)", margin: 0, fontFamily: "var(--mono)" }}>{time.toLocaleTimeString("pt-BR")} · {displayCameras.length} cam{displayCameras.length !== 1 ? "s" : ""}</p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
            {["1x1","2x2","3x3","4x4"].map(g => (
              <button key={g} onClick={() => { setGrid(g); setFullscreenCam(null); }} style={{
                padding: "4px 9px", borderRadius: 5,
                background: grid===g ? "rgba(37,99,235,0.8)" : "rgba(255,255,255,0.04)",
                color: grid===g ? "#fff" : "rgba(255,255,255,0.35)",
                border: grid===g ? "none" : "1px solid rgba(255,255,255,0.07)",
                fontSize: 11, fontWeight: 600, cursor: "pointer", fontFamily: "var(--mono)",
              }}>{g}</button>
            ))}
            <div style={{ width: 1, height: 20, background: "rgba(255,255,255,0.08)", margin: "0 4px" }} />
            <button onClick={() => setPanelOpen(!panelOpen)} style={{
              padding: "4px 10px", borderRadius: 5,
              background: panelOpen ? "rgba(37,99,235,0.8)" : "rgba(255,255,255,0.04)",
              color: panelOpen ? "#fff" : "rgba(255,255,255,0.35)",
              border: panelOpen ? "none" : "1px solid rgba(255,255,255,0.07)",
              fontSize: 11, fontWeight: 600, cursor: "pointer",
              display: "flex", alignItems: "center", gap: 4,
            }}>{Icons.panelRight}{!isMobileView && <span>Câmeras</span>}</button>
          </div>
        </div>

        {/* Grid */}
        <div style={{ flex: 1, padding: 4, overflow: "auto", display: fullscreenCam ? "flex" : "grid", gridTemplateColumns: `repeat(${isMobileView ? Math.min(cols, 2) : cols}, 1fr)`, gap: 3, alignContent: "start" }}>
          {fullscreenCam ? (
            (() => { const c = DEMO_CAMERAS.find(x => x.id === fullscreenCam); return c ? <CamCell cam={c} index={0} /> : null; })()
          ) : displayCameras.length === 0 ? (
            <div style={{ gridColumn: "1/-1", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 10, padding: 60, color: "rgba(255,255,255,0.25)" }}>
              <div style={{ opacity: 0.3, transform: "scale(2)", marginBottom: 8 }}>{Icons.camera}</div>
              <div style={{ fontSize: 15, fontWeight: 600 }}>Nenhuma câmera selecionada</div>
              <div style={{ fontSize: 12, color: "rgba(255,255,255,0.15)" }}>Abra o painel para adicionar câmeras</div>
              <button onClick={() => setPanelOpen(true)} style={{ marginTop: 8, padding: "7px 18px", borderRadius: 7, background: "rgba(37,99,235,0.8)", color: "#fff", border: "none", fontSize: 12, fontWeight: 600, cursor: "pointer" }}>Selecionar Câmeras</button>
            </div>
          ) : displayCameras.map((cam, i) => <CamCell key={cam.id} cam={cam} index={i} />)}
        </div>
      </div>

      {/* ── Selector Panel ── */}
      {panelOpen && (
        <>
          {isMobileView && <div onClick={() => setPanelOpen(false)} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", zIndex: 80 }} />}
          <div style={{
            width: isMobileView ? "82vw" : 280, maxWidth: 320,
            background: "#161b22", borderLeft: "1px solid rgba(255,255,255,0.05)",
            display: "flex", flexDirection: "column",
            position: isMobileView ? "fixed" : "relative",
            right: 0, top: 0, bottom: 0, zIndex: isMobileView ? 90 : 1,
            animation: "slideIn 0.2s ease both",
          }}>
            {/* Header */}
            <div style={{ padding: 14, borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <h2 style={{ fontSize: 14, fontWeight: 600, color: "#fff", margin: 0 }}>Câmeras</h2>
                <button onClick={() => setPanelOpen(false)} style={{ background: "none", border: "none", color: "rgba(255,255,255,0.35)", cursor: "pointer", padding: 2 }}>{Icons.x}</button>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 7, padding: "6px 10px", marginBottom: 8 }}>
                <span style={{ color: "rgba(255,255,255,0.2)", flexShrink: 0 }}>{Icons.search}</span>
                <input type="text" placeholder="Buscar..." value={searchPanel} onChange={e => setSearchPanel(e.target.value)} style={{ background: "none", border: "none", outline: "none", color: "#fff", fontSize: 12, width: "100%", fontFamily: "inherit" }} />
              </div>
              <div style={{ display: "flex", gap: 5 }}>
                <button onClick={() => { const a = DEMO_CAMERAS.map(c=>c.id); setSelectedIds(a); setOrderedIds(a); }} style={{ flex: 1, padding: 5, borderRadius: 5, background: "rgba(34,197,94,0.08)", border: "1px solid rgba(34,197,94,0.15)", color: "#22c55e", fontSize: 10, fontWeight: 600, cursor: "pointer" }}>Todas</button>
                <button onClick={() => { setSelectedIds([]); setOrderedIds([]); }} style={{ flex: 1, padding: 5, borderRadius: 5, background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.15)", color: "#ef4444", fontSize: 10, fontWeight: 600, cursor: "pointer" }}>Limpar</button>
              </div>
            </div>

            {/* List */}
            <div style={{ flex: 1, overflowY: "auto", padding: 6 }}>
              {filteredPanel.map(cam => {
                const sel = selectedIds.includes(cam.id);
                const on = cam.status === "online";
                return (
                  <div key={cam.id} onClick={() => toggleCamera(cam.id)}
                    style={{
                      display: "flex", alignItems: "center", gap: 8,
                      padding: "9px 10px", borderRadius: 7, marginBottom: 2,
                      background: sel ? "rgba(37,99,235,0.1)" : "transparent",
                      border: sel ? "1px solid rgba(37,99,235,0.2)" : "1px solid transparent",
                      cursor: "pointer", transition: "all 0.12s",
                    }}
                    onMouseEnter={e => { if (!sel) e.currentTarget.style.background = "rgba(255,255,255,0.03)"; }}
                    onMouseLeave={e => { if (!sel) e.currentTarget.style.background = "transparent"; }}>
                    <div style={{
                      width: 18, height: 18, borderRadius: 4, flexShrink: 0,
                      background: sel ? "#2563eb" : "transparent",
                      border: sel ? "none" : "2px solid rgba(255,255,255,0.12)",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      transition: "all 0.12s",
                    }}>{sel && <span style={{ color: "#fff" }}>{Icons.check}</span>}</div>
                    <span style={{ width: 7, height: 7, borderRadius: "50%", flexShrink: 0, background: on ? "#22c55e" : "#ef4444", boxShadow: on ? "0 0 5px rgba(34,197,94,0.35)" : "none" }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 12, fontWeight: sel ? 600 : 400, color: sel ? "#fff" : "rgba(255,255,255,0.6)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{cam.name}</div>
                      <div style={{ fontSize: 10, color: "rgba(255,255,255,0.25)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{cam.location || "Sem localização"} · {cam.resolution || "1080p"}</div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Footer */}
            <div style={{ padding: "10px 14px", borderTop: "1px solid rgba(255,255,255,0.05)", display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: 11, color: "rgba(255,255,255,0.3)" }}>{selectedIds.length}/{DEMO_CAMERAS.length}</span>
              <span style={{ fontSize: 10, color: "rgba(255,255,255,0.2)", fontFamily: "var(--mono)" }}>{DEMO_CAMERAS.filter(c=>c.status==="online").length} online</span>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

// ── Rules (FASE 3) ──
const RulesPage = () => {
  const [templates, setTemplates] = useState([]);
  const [customRules, setCustomRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { success, error: toastError } = useToast();

  // Polling para regras (30s com backoff)
  useEffect(() => {
    let mounted = true;
    let failCount = 0;
    let pollInterval = 30000; // 30s inicial

    const fetchRules = async () => {
      try {
        const res = await fetch("http://localhost:5001/api/rules");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();
        if (mounted && data.success) {
          // Separar templates de regras customizadas
          const temps = data.rules.filter(r => r.template_type !== null);
          const customs = data.rules.filter(r => r.template_type === null);

          setTemplates(temps);
          setCustomRules(customs);
          setError(null);
          failCount = 0; // Reset falhas
          pollInterval = 30000; // Reset intervalo
        }
      } catch (err) {
        if (mounted) {
          console.error("Erro ao buscar regras:", err);
          failCount++;
          // Exponential backoff até 60s max
          pollInterval = Math.min(30000 * Math.pow(2, failCount - 1), 60000);
        }
      } finally {
        if (mounted) setLoading(false);
      }
    };

    fetchRules();
    const interval = setInterval(fetchRules, pollInterval);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  // Toggle rule active/inactive
  const handleToggle = async (ruleId, currentState) => {
    try {
      const res = await fetch(`http://localhost:5001/api/rules/${ruleId}/toggle`, {
        method: "POST",
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      if (data.success) {
        // Atualizar estado local otimista
        const updateList = (list) =>
          list.map(r =>
            r.id === ruleId ? { ...r, is_active: !r.is_active } : r
          );

        setTemplates(updateList(templates));
        setCustomRules(updateList(customRules));

        success(`Regra ${currentState ? "desativada" : "ativada"} com sucesso!`);
      } else {
        throw new Error(data.error || "Erro ao alternar regra");
      }
    } catch (err) {
      console.error("Erro ao alternar regra:", err);
      toastError(err.message || "Erro ao alternar regra");
    }
  };

  // Template descriptions
  const getTemplateDescription = (template) => {
    const descriptions = {
      "bay_control": "Detecta caminhão e gerencia sessões automaticamente",
      "product_count": "Conta cada produto detectado com cooldown de 3s",
      "plate_capture": "Associa placa detectada à sessão ativa",
      "epi_compliance": "Alerta quando operador sem EPI",
    };
    return descriptions[template.template_type] || template.description || "";
  };

  // Get template label
  const getTemplateLabel = (template) => {
    const labels = {
      "Controle de Baia — Início": "Controle de Baia — Início",
      "Controle de Baia — Fim": "Controle de Baia — Fim",
      "Contagem de Produtos": "Contagem de Produtos",
      "Captura de Placa": "Captura de Placa",
    };
    return labels[template.name] || template.name;
  };

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, color: "var(--text)", margin: 0 }}>
          Regras
        </h1>
        <p style={{ color: "var(--muted)", margin: "4px 0 0", fontSize: 14 }}>
          Configure regras de negócio para processamento de detecções YOLO
        </p>
      </div>

      {loading ? (
        <div style={{ textAlign: "center", padding: 60 }}>
          <div style={{
            width: 40, height: 40, margin: "0 auto 16px",
            border: "3px solid var(--border)", borderTopColor: "var(--accent)",
            borderRadius: "50%", animation: "spin 1s linear infinite"
          }} />
          <p style={{ color: "var(--muted)", fontSize: 14 }}>Carregando regras...</p>
        </div>
      ) : error ? (
        <div style={{
          background: "#fef2f2", border: "1px solid #fecaca",
          borderRadius: 12, padding: 24, textAlign: "center"
        }}>
          <p style={{ color: "#dc2626", fontSize: 14, fontWeight: 500, margin: "0 0 8px" }}>
            Erro ao carregar regras
          </p>
          <p style={{ color: "#991b1b", fontSize: 13, margin: 0 }}>{error}</p>
        </div>
      ) : (
        <>
          {/* Templates Pré-configurados */}
          <div style={{
            background: "var(--card)", borderRadius: 16,
            border: "1px solid var(--border)", padding: 24, marginBottom: 24
          }}>
            <h2 style={{
              fontSize: 16, fontWeight: 600, color: "var(--text)",
              margin: "0 0 20px", display: "flex", alignItems: "center", gap: 8
            }}>
              {Icons.settings} Templates Pré-configurados
            </h2>

            {templates.length === 0 ? (
              <p style={{ color: "var(--muted)", fontSize: 14, margin: 0 }}>
                Nenhum template disponível.
              </p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {templates.map((template, index) => (
                  <div key={template.id} style={{
                    padding: 16, borderRadius: 12,
                    background: "var(--bg)", border: "1px solid var(--border)",
                    display: "flex", alignItems: "center", gap: 16,
                    transition: "transform 0.15s, box-shadow 0.15s",
                    animation: `fadeUp 0.4s ease ${0.1 + index * 0.05}s both`
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.transform = "translateY(-2px)";
                    e.currentTarget.style.boxShadow = "0 4px 12px rgba(0,0,0,0.08)";
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.transform = "";
                    e.currentTarget.style.boxShadow = "";
                  }}>
                    {/* Toggle Button */}
                    <button
                      onClick={() => handleToggle(template.id, template.is_active)}
                      style={{
                        width: 48, height: 28, flexShrink: 0,
                        background: template.is_active ? "#22c55e" : "rgba(0,0,0,0.08)",
                        borderRadius: 14, position: "relative", cursor: "pointer",
                        border: "none", transition: "background 0.2s"
                      }}
                    >
                      <span style={{
                        position: "absolute", top: 3,
                        left: template.is_active ? 25 : 4,
                        width: 22, height: 22, borderRadius: "50%",
                        background: "#fff", boxShadow: "0 2px 4px rgba(0,0,0,0.2)",
                        transition: "left 0.2s"
                      }} />
                    </button>

                    {/* Template Info */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{
                        display: "flex", alignItems: "center", gap: 8, marginBottom: 4
                      }}>
                        <span style={{
                          fontSize: 14, fontWeight: 600, color: "var(--text)"
                        }}>
                          {getTemplateLabel(template)}
                        </span>
                        {template.is_active && (
                          <span style={{
                            fontSize: 10, fontWeight: 600, color: "#22c55e",
                            padding: "2px 8px", borderRadius: 10,
                            background: "rgba(34,197,94,0.1)"
                          }}>
                            ATIVO
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: 13, color: "var(--muted)" }}>
                        {getTemplateDescription(template)}
                      </div>
                    </div>

                    {/* Action Type Badge */}
                    <span style={{
                      fontSize: 11, fontWeight: 500, color: "var(--muted)",
                      padding: "4px 10px", borderRadius: 6,
                      background: "var(--bg)", border: "1px solid var(--border)",
                      textTransform: "uppercase", letterSpacing: 0.5
                    }}>
                      {template.action_type === "start_session" && "Iniciar Sessão"}
                      {template.action_type === "end_session" && "Encerrar Sessão"}
                      {template.action_type === "count_product" && "Contar"}
                      {template.action_type === "associate_plate" && "Placa"}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Regras Customizadas */}
          <div style={{
            background: "var(--card)", borderRadius: 16,
            border: "1px solid var(--border)", padding: 24
          }}>
            <div style={{
              display: "flex", justifyContent: "space-between", alignItems: "center",
              marginBottom: 20
            }}>
              <h2 style={{
                fontSize: 16, fontWeight: 600, color: "var(--text)", margin: 0,
                display: "flex", alignItems: "center", gap: 8
              }}>
                {Icons.sliders} Regras Customizadas
              </h2>
              <button style={{
                display: "flex", alignItems: "center", gap: 6,
                padding: "8px 16px", borderRadius: 8,
                background: "var(--accent)", color: "#fff",
                border: "none", fontSize: 13, fontWeight: 500, cursor: "pointer",
                transition: "all 0.15s"
              }}
              onMouseEnter={e => e.currentTarget.style.opacity = "0.9"}
              onMouseLeave={e => e.currentTarget.style.opacity = "1"}>
                {Icons.plus} Adicionar
              </button>
            </div>

            {customRules.length === 0 ? (
              <div style={{
                padding: 40, textAlign: "center",
                background: "var(--bg)", borderRadius: 12
              }}>
                <p style={{ color: "var(--muted)", fontSize: 14, margin: 0 }}>
                  Nenhuma regra customizada criada ainda.
                </p>
                <p style={{ color: "var(--muted)", fontSize: 12, marginTop: 4 }}>
                  Clique em "Adicionar" para criar sua primeira regra customizada.
                </p>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {customRules.map((rule, index) => (
                  <div key={rule.id} style={{
                    padding: 16, borderRadius: 12,
                    background: "var(--bg)", border: "1px solid var(--border)",
                    display: "flex", alignItems: "center", gap: 16,
                    transition: "transform 0.15s, box-shadow 0.15s",
                    animation: `fadeUp 0.4s ease ${0.2 + index * 0.05}s both`
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.transform = "translateY(-2px)";
                    e.currentTarget.style.boxShadow = "0 4px 12px rgba(0,0,0,0.08)";
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.transform = "";
                    e.currentTarget.style.boxShadow = "";
                  }}>
                    {/* Toggle Button */}
                    <button
                      onClick={() => handleToggle(rule.id, rule.is_active)}
                      style={{
                        width: 48, height: 28, flexShrink: 0,
                        background: rule.is_active ? "#22c55e" : "rgba(0,0,0,0.08)",
                        borderRadius: 14, position: "relative", cursor: "pointer",
                        border: "none", transition: "background 0.2s"
                      }}
                    >
                      <span style={{
                        position: "absolute", top: 3,
                        left: rule.is_active ? 25 : 4,
                        width: 22, height: 22, borderRadius: "50%",
                        background: "#fff", boxShadow: "0 2px 4px rgba(0,0,0,0.2)",
                        transition: "left 0.2s"
                      }} />
                    </button>

                    {/* Rule Info */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{
                        display: "flex", alignItems: "center", gap: 8, marginBottom: 4
                      }}>
                        <span style={{
                          fontSize: 14, fontWeight: 600, color: "var(--text)"
                        }}>
                          {rule.name}
                        </span>
                        {rule.is_active && (
                          <span style={{
                            fontSize: 10, fontWeight: 600, color: "#22c55e",
                            padding: "2px 8px", borderRadius: 10,
                            background: "rgba(34,197,94,0.1)"
                          }}>
                            ATIVO
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: 13, color: "var(--muted)" }}>
                        {rule.description || "Sem descrição"}
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div style={{ display: "flex", gap: 8 }}>
                      <button style={{
                        padding: "6px 12px", borderRadius: 6,
                        background: "var(--bg)", color: "var(--text)",
                        border: "1px solid var(--border)", fontSize: 12,
                        fontWeight: 500, cursor: "pointer", display: "flex",
                        alignItems: "center", gap: 4, transition: "all 0.15s"
                      }}
                      onMouseEnter={e => e.currentTarget.style.borderColor = "var(--accent)"}
                      onMouseLeave={e => e.currentTarget.style.borderColor = "var(--border)"}>
                        {Icons.edit} Editar
                      </button>
                      <button style={{
                        padding: "6px 12px", borderRadius: 6,
                        background: "var(--bg)", color: "#ef4444",
                        border: "1px solid var(--border)", fontSize: 12,
                        fontWeight: 500, cursor: "pointer", display: "flex",
                        alignItems: "center", gap: 4, transition: "all 0.15s"
                      }}
                      onMouseEnter={e => {
                        e.currentTarget.style.borderColor = "#ef4444";
                        e.currentTarget.style.background = "#fef2f2";
                      }}
                      onMouseLeave={e => {
                        e.currentTarget.style.borderColor = "var(--border)";
                        e.currentTarget.style.background = "var(--bg)";
                      }}>
                        {Icons.trash} Excluir
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

// ── Validation (FASE 4) ──
const ValidationPage = () => {
  const [pendingSessions, setPendingSessions] = useState([]);
  const [validatedSessions, setValidatedSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editingSession, setEditingSession] = useState(null);
  const [operatorCount, setOperatorCount] = useState("");
  const [notes, setNotes] = useState("");
  const [rejectConfirm, setRejectConfirm] = useState(null);
  const { success, error: toastError } = useToast();

  // Polling para sessões pendentes (10s com backoff)
  useEffect(() => {
    let mounted = true;
    let failCount = 0;
    let pollInterval = 10000; // 10s inicial

    const fetchSessions = async () => {
      try {
        // Fetch pending sessions (com autenticação)
        const token = localStorage.getItem("token") || "";
        const headers = { "Authorization": `Bearer ${token}` };

        const [pendingRes, validatedRes] = await Promise.all([
          fetch("http://localhost:5001/api/sessions/pending", { headers }),
          fetch("http://localhost:5001/api/sessions/history?limit=20&status=validated", { headers }),
        ]);

        if (!pendingRes.ok || !validatedRes.ok) throw new Error("HTTP error");

        const pendingData = await pendingRes.json();
        const validatedData = await validatedRes.json();

        if (mounted) {
          if (pendingData.success) setPendingSessions(pendingData.sessions || []);
          if (validatedData.success) setValidatedSessions(validatedData.sessions || []);
          setError(null);
          failCount = 0;
          pollInterval = 10000;
        }
      } catch (err) {
        if (mounted) {
          console.error("Erro ao buscar sessões:", err);
          failCount++;
          pollInterval = Math.min(10000 * Math.pow(2, failCount - 1), 60000);
        }
      } finally {
        if (mounted) setLoading(false);
      }
    };

    fetchSessions();
    const interval = setInterval(fetchSessions, pollInterval);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  // Validate session
  const handleValidate = async (sessionId, count, notesText) => {
    try {
      const token = localStorage.getItem("token") || "";
      const res = await fetch(`http://localhost:5001/api/sessions/${sessionId}/validate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({
          validated_by: "operador",
          operator_count: count,
          notes: notesText,
        }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      if (data.success) {
        // Remover da lista de pendentes
        setPendingSessions(prev => prev.filter(s => s.id !== sessionId));
        // Adicionar ao histórico (local update otimista)
        const session = pendingSessions.find(s => s.id === sessionId);
        if (session) {
          setValidatedSessions(prev => [
            { ...session, operator_count: count, validation_notes: notesText, status: "validated", validated_at: new Date().toISOString() },
            ...prev,
          ]);
        }
        success("Sessão validada com sucesso!");
        setEditingSession(null);
        setOperatorCount("");
        setNotes("");
      } else {
        throw new Error(data.error || "Erro ao validar sessão");
      }
    } catch (err) {
      console.error("Erro ao validar sessão:", err);
      toastError(err.message || "Erro ao validar sessão");
    }
  };

  // Reject session
  const handleReject = async (sessionId, notesText) => {
    try {
      const token = localStorage.getItem("token") || "";
      const res = await fetch(`http://localhost:5001/api/sessions/${sessionId}/reject`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({
          validated_by: "operador",
          notes: notesText,
        }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      if (data.success) {
        setPendingSessions(prev => prev.filter(s => s.id !== sessionId));
        success("Sessão rejeitada.");
        setRejectConfirm(null);
        setNotes("");
      } else {
        throw new Error(data.error || "Erro ao rejeitar sessão");
      }
    } catch (err) {
      console.error("Erro ao rejeitar sessão:", err);
      toastError(err.message || "Erro ao rejeitar sessão");
    }
  };

  // Format duration
  const formatDuration = (seconds) => {
    if (!seconds) return "-";
    const mins = Math.floor(seconds / 60);
    return `${mins} min`;
  };

  // Format time range
  const formatTimeRange = (startedAt, endedAt) => {
    if (!startedAt) return "-";
    const start = new Date(startedAt);
    const end = endedAt ? new Date(endedAt) : new Date();
    const startFmt = start.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
    const endFmt = end.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
    return `${startFmt} → ${endFmt}`;
  };

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, color: "var(--text)", margin: 0 }}>
          Validações
        </h1>
        <p style={{ color: "var(--muted)", margin: "4px 0 0", fontSize: 14 }}>
          Valide ou corrija a contagem de produtos feita pela IA
        </p>
      </div>

      {loading ? (
        <div style={{ textAlign: "center", padding: 60 }}>
          <div style={{
            width: 40, height: 40, margin: "0 auto 16px",
            border: "3px solid var(--border)", borderTopColor: "var(--accent)",
            borderRadius: "50%", animation: "spin 1s linear infinite"
          }} />
          <p style={{ color: "var(--muted)", fontSize: 14 }}>Carregando sessões...</p>
        </div>
      ) : error ? (
        <div style={{
          background: "#fef2f2", border: "1px solid #fecaca",
          borderRadius: 12, padding: 24, textAlign: "center"
        }}>
          <p style={{ color: "#dc2626", fontSize: 14, fontWeight: 500, margin: "0 0 8px" }}>
            Erro ao carregar sessões
          </p>
          <p style={{ color: "#991b1b", fontSize: 13, margin: 0 }}>{error}</p>
        </div>
      ) : (
        <>
          {/* Pending Sessions */}
          <div style={{
            background: "var(--card)", borderRadius: 16,
            border: "1px solid var(--border)", padding: 24, marginBottom: 24
          }}>
            <div style={{
              display: "flex", justifyContent: "space-between", alignItems: "center",
              marginBottom: 20
            }}>
              <h2 style={{
                fontSize: 16, fontWeight: 600, color: "var(--text)", margin: 0,
                display: "flex", alignItems: "center", gap: 8
              }}>
                {Icons.activity} Validações Pendentes
                {pendingSessions.length > 0 && (
                  <span style={{
                    fontSize: 12, fontWeight: 600, color: "#fff",
                    padding: "2px 10px", borderRadius: 12,
                    background: "var(--accent)"
                  }}>
                    {pendingSessions.length} aguardando
                  </span>
                )}
              </h2>
            </div>

            {pendingSessions.length === 0 ? (
              <div style={{
                padding: 40, textAlign: "center",
                background: "var(--bg)", borderRadius: 12
              }}>
                <span style={{ fontSize: 40 }}>✅</span>
                <p style={{ color: "var(--muted)", fontSize: 14, margin: "8px 0 0" }}>
                  Nenhuma sessão pendente de validação
                </p>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                {pendingSessions.map((session, index) => {
                  const isEditing = editingSession === session.id;
                  const currentCount = operatorCount !== "" ? parseInt(operatorCount) : session.ai_count;

                  return (
                    <div key={session.id} style={{
                      padding: 20, borderRadius: 12,
                      background: "var(--bg)", border: "1px solid var(--border)",
                      animation: `fadeUp 0.4s ease ${0.1 + index * 0.05}s both`
                    }}>
                      {/* Session Header */}
                      <div style={{
                        display: "flex", alignItems: "center", gap: 12, marginBottom: 16
                      }}>
                        <span style={{ fontSize: 32 }}>🚛</span>
                        <div style={{ flex: 1 }}>
                          <div style={{
                            fontSize: 16, fontWeight: 600, color: "var(--text)", marginBottom: 4
                          }}>
                            {session.truck_plate || "Placa não identificada"}
                          </div>
                          <div style={{ fontSize: 13, color: "var(--muted)" }}>
                            Baia {session.bay_id || session.camera_id || "?"} ·{" "}
                            {formatTimeRange(session.started_at, session.ended_at)} ·{" "}
                            {formatDuration(session.duration_seconds)}
                          </div>
                        </div>
                        <div style={{ textAlign: "right" }}>
                          <div style={{ fontSize: 12, color: "var(--muted)" }}>IA contou:</div>
                          <div style={{
                            fontSize: 24, fontWeight: 700, color: "var(--text)"
                          }}>
                            {session.ai_count || 0}
                          </div>
                        </div>
                      </div>

                      {/* Camera Info */}
                      <div style={{
                        fontSize: 12, color: "var(--muted)",
                        marginBottom: 16, padding: "8px 12px",
                        background: "rgba(0,0,0,0.03)", borderRadius: 6
                      }}>
                        Câmera: {session.camera_id || "Não identificada"}
                      </div>

                      {/* Editing Mode */}
                      {isEditing ? (
                        <>
                          {/* Edit Count */}
                          <div style={{ marginBottom: 16 }}>
                            <label style={{
                              fontSize: 13, fontWeight: 500, color: "var(--text)",
                              display: "block", marginBottom: 8
                            }}>
                              Contagem correta:
                            </label>
                            <input
                              type="number"
                              value={operatorCount}
                              onChange={(e) => setOperatorCount(e.target.value)}
                              style={{
                                width: "100%", padding: "10px 14px", borderRadius: 8,
                                border: "1px solid var(--border)", fontSize: 14,
                                background: "var(--card)", color: "var(--text)"
                              }}
                              placeholder={session.ai_count.toString()}
                            />
                          </div>

                          {/* Notes */}
                          <div style={{ marginBottom: 16 }}>
                            <label style={{
                              fontSize: 13, fontWeight: 500, color: "var(--text)",
                              display: "block", marginBottom: 8
                            }}>
                              Observações (opcional):
                            </label>
                            <input
                              type="text"
                              value={notes}
                              onChange={(e) => setNotes(e.target.value)}
                              style={{
                                width: "100%", padding: "10px 14px", borderRadius: 8,
                                border: "1px solid var(--border)", fontSize: 14,
                                background: "var(--card)", color: "var(--text)"
                              }}
                              placeholder="Correção, motivo, etc."
                            />
                          </div>

                          {/* Action Buttons */}
                          <div style={{ display: "flex", gap: 12 }}>
                            <button
                              onClick={() => handleValidate(session.id, currentCount, notes)}
                              style={{
                                flex: 1, padding: "10px 16px", borderRadius: 8,
                                background: "#22c55e", color: "#fff",
                                border: "none", fontSize: 14, fontWeight: 600,
                                cursor: "pointer", transition: "opacity 0.15s"
                              }}
                              onMouseEnter={e => e.currentTarget.style.opacity = "0.9"}
                              onMouseLeave={e => e.currentTarget.style.opacity = "1"}
                            >
                              ✅ Salvar Correção
                            </button>
                            <button
                              onClick={() => {
                                setEditingSession(null);
                                setOperatorCount("");
                                setNotes("");
                              }}
                              style={{
                                padding: "10px 16px", borderRadius: 8,
                                background: "var(--bg)", color: "var(--text)",
                                border: "1px solid var(--border)", fontSize: 14,
                                fontWeight: 500, cursor: "pointer"
                              }}
                            >
                              Cancelar
                            </button>
                          </div>
                        </>
                      ) : (
                        <>
                          {/* Default View */}
                          <div style={{
                            display: "flex", gap: 12, alignItems: "stretch",
                            flexWrap: "wrap"
                          }}>
                            <button
                              onClick={() => handleValidate(session.id, session.ai_count, "")}
                              style={{
                                flex: 1, minWidth: 140, padding: "10px 16px", borderRadius: 8,
                                background: "#22c55e", color: "#fff",
                                border: "none", fontSize: 14, fontWeight: 600,
                                cursor: "pointer", transition: "opacity 0.15s",
                                display: "flex", alignItems: "center", justifyContent: "center", gap: 6
                              }}
                              onMouseEnter={e => e.currentTarget.style.opacity = "0.9"}
                              onMouseLeave={e => e.currentTarget.style.opacity = "1"}
                            >
                              {Icons.check} Validar
                            </button>
                            <button
                              onClick={() => {
                                setEditingSession(session.id);
                                setOperatorCount("");
                                setNotes("");
                              }}
                              style={{
                                flex: 1, minWidth: 160, padding: "10px 16px", borderRadius: 8,
                                background: "#f59e0b", color: "#fff",
                                border: "none", fontSize: 14, fontWeight: 600,
                                cursor: "pointer", transition: "opacity 0.15s",
                                display: "flex", alignItems: "center", justifyContent: "center", gap: 6
                              }}
                              onMouseEnter={e => e.currentTarget.style.opacity = "0.9"}
                              onMouseLeave={e => e.currentTarget.style.opacity = "1"}
                            >
                              {Icons.edit} Corrigir e Validar
                            </button>
                            <button
                              onClick={() => {
                                setRejectConfirm(session.id);
                                setNotes("");
                              }}
                              style={{
                                flex: 1, minWidth: 120, padding: "10px 16px", borderRadius: 8,
                                background: "#ef4444", color: "#fff",
                                border: "none", fontSize: 14, fontWeight: 600,
                                cursor: "pointer", transition: "opacity 0.15s",
                                display: "flex", alignItems: "center", justifyContent: "center", gap: 6
                              }}
                              onMouseEnter={e => e.currentTarget.style.opacity = "0.9"}
                              onMouseLeave={e => e.currentTarget.style.opacity = "1"}
                            >
                              {Icons.trash} Rejeitar
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Validated Sessions History */}
          {validatedSessions.length > 0 && (
            <div style={{
              background: "var(--card)", borderRadius: 16,
              border: "1px solid var(--border)", padding: 24
            }}>
              <h2 style={{
                fontSize: 16, fontWeight: 600, color: "var(--text)", margin: "0 0 20px",
                display: "flex", alignItems: "center", gap: 8
              }}>
                {Icons.shield} Histórico de Validações
                <span style={{
                  fontSize: 12, fontWeight: 400, color: "var(--muted)"
                }}>
                  (últimas {validatedSessions.length})
                </span>
              </h2>

              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {validatedSessions.map((session, index) => (
                  <div key={session.id} style={{
                    padding: 14, borderRadius: 10,
                    background: "var(--bg)", border: "1px solid var(--border)",
                    display: "flex", alignItems: "center", gap: 12,
                    animation: `fadeUp 0.3s ease ${0.2 + index * 0.03}s both`
                  }}>
                    <span style={{ fontSize: 24 }}>✅</span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{
                        fontSize: 14, fontWeight: 500, color: "var(--text)",
                        whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis"
                      }}>
                        {session.truck_plate || "Placa não identificada"}
                      </div>
                      <div style={{ fontSize: 12, color: "var(--muted)" }}>
                        Baia {session.bay_id || session.camera_id || "?"} ·{" "}
                        IA: {session.ai_count || 0}
                        {session.operator_count !== null && session.operator_count !== session.ai_count && (
                          <span style={{ color: "#f59e0b", fontWeight: 500 }}>
                            → Operador: {session.operator_count}
                          </span>
                        )}
                      </div>
                    </div>
                    <div style={{
                      fontSize: 12, color: "var(--muted)", textAlign: "right"
                    }}>
                      {session.validated_at
                        ? new Date(session.validated_at).toLocaleDateString("pt-BR")
                        : "-"}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Reject Confirmation Modal */}
          {rejectConfirm && (
            <div style={{
              position: "fixed", inset: 0, zIndex: 100,
              display: "flex", alignItems: "center", justifyContent: "center",
              background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)",
              animation: "fadeUp 0.2s ease both"
            }}>
              <div style={{
                background: "var(--card)", borderRadius: 16, border: "1px solid var(--border)",
                padding: 24, maxWidth: 420, width: "90%", boxShadow: "0 20px 60px rgba(0,0,0,0.3)"
              }}>
                <h3 style={{
                  fontSize: 18, fontWeight: 700, color: "var(--text)", margin: "0 0 12px"
                }}>
                  Rejeitar Validação
                </h3>
                <p style={{
                  fontSize: 14, color: "var(--muted)", lineHeight: 1.5, margin: "0 0 20px"
                }}>
                  Tem certeza que deseja rejeitar esta sessão? Esta ação não pode ser desfeita.
                </p>

                {/* Notes for rejection */}
                <div style={{ marginBottom: 20 }}>
                  <label style={{
                    fontSize: 13, fontWeight: 500, color: "var(--text)",
                    display: "block", marginBottom: 8
                  }}>
                    Motivo (opcional):
                  </label>
                  <input
                    type="text"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    style={{
                      width: "100%", padding: "10px 14px", borderRadius: 8,
                      border: "1px solid var(--border)", fontSize: 14,
                      background: "var(--bg)", color: "var(--text)"
                    }}
                    placeholder="Por que está rejeitando?"
                  />
                </div>

                <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
                  <button
                    onClick={() => {
                      setRejectConfirm(null);
                      setNotes("");
                    }}
                    style={{
                      padding: "10px 20px", borderRadius: 8,
                      background: "var(--bg)", color: "var(--text)",
                      border: "1px solid var(--border)", fontSize: 14, fontWeight: 500, cursor: "pointer"
                    }}
                  >
                    Cancelar
                  </button>
                  <button
                    onClick={() => handleReject(rejectConfirm, notes)}
                    style={{
                      padding: "10px 20px", borderRadius: 8,
                      background: "#ef4444", color: "#fff",
                      border: "none", fontSize: 14, fontWeight: 600, cursor: "pointer"
                    }}
                  >
                    Rejeitar Sessão
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

// ── Nav ──
const NAV = [
  { id: "dashboard", label: "Dashboard", icon: Icons.dashboard },
  { id: "cameras", label: "Câmeras", icon: Icons.camera },
  { id: "monitoring", label: "Monitoramento", icon: Icons.monitor },
  { id: "classes", label: "Classes", icon: Icons.classes },
  { id: "training", label: "Treinamento", icon: Icons.training },
  { id: "rules", label: "Regras", icon: Icons.sliders },
  { id: "validations", label: "Validações", icon: Icons.shield },
];

// ── App ──
export default function App() {
  const [page, setPage] = useState("monitoring");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // Camera management state
  const [cameraModalOpen, setCameraModalOpen] = useState(false);
  const [editingCamera, setEditingCamera] = useState(null);

  // Hooks
  const { cameras, loading, createCamera, updateCamera, deleteCamera } = useCameras();
  const { streams, startStream, stopStream } = useStreams();
  const { success, error } = useToast();

  useEffect(() => { const c = () => setIsMobile(window.innerWidth < 768); c(); window.addEventListener("resize", c); return () => window.removeEventListener("resize", c); }, []);

  const handleCreateCamera = () => {
    setEditingCamera(null);
    setCameraModalOpen(true);
  };

  const handleEditCamera = (camera) => {
    setEditingCamera(camera);
    setCameraModalOpen(true);
  };

  const handleSaveCamera = async (formData) => {
    try {
      if (editingCamera) {
        const result = await updateCamera(editingCamera.id, formData);
        if (!result.success) {
          throw new Error(result.error);
        }
      } else {
        const result = await createCamera(formData);
        if (!result.success) {
          throw new Error(result.error);
        }
      }
      setCameraModalOpen(false);
      setEditingCamera(null);
    } catch (err) {
      throw err;
    }
  };

  const handleDeleteCamera = async (cameraId) => {
    const result = await deleteCamera(cameraId);
    if (!result.success) {
      error(result.error || "Erro ao excluir câmera");
    } else {
      success("Câmera excluída com sucesso!");
    }
  };

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600;9..40,700&family=DM+Mono:wght@400;500&display=swap');
        :root { --bg:#f8f9fb; --card:#fff; --border:#e8ecf1; --text:#111827; --muted:#6b7280; --accent:#2563eb; --mono:'DM Mono',monospace; }
        * { box-sizing:border-box; margin:0; padding:0; }
        body { font-family:'DM Sans',-apple-system,sans-serif; }
        @keyframes fadeUp { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
        @keyframes slideIn { from{transform:translateX(100%);opacity:0} to{transform:translateX(0);opacity:1} }
        @keyframes spin { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
        ::-webkit-scrollbar{width:4px} ::-webkit-scrollbar-track{background:transparent} ::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.08);border-radius:2px}
      `}</style>

      <div style={{ display: "flex", minHeight: "100vh", background: "var(--bg)", fontFamily: "'DM Sans', sans-serif" }}>
        {isMobile && sidebarOpen && <div onClick={() => setSidebarOpen(false)} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", zIndex: 40, backdropFilter: "blur(4px)" }} />}

        {/* Sidebar */}
        <aside style={{
          width: isMobile ? 240 : 210, background: "#111827",
          position: isMobile ? "fixed" : "sticky", top: 0,
          left: isMobile ? (sidebarOpen ? 0 : -260) : 0,
          height: "100vh", zIndex: 50, display: "flex", flexDirection: "column",
          transition: "left 0.3s cubic-bezier(0.4,0,0.2,1)",
          borderRight: "1px solid rgba(255,255,255,0.06)", overflowY: "auto",
        }}>
          <div style={{ padding: "18px 14px 14px", display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ width: 32, height: 32, borderRadius: 8, background: "linear-gradient(135deg,#2563eb,#7c3aed)", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontWeight: 800, fontSize: 12 }}>EP</div>
            <div><div style={{ fontSize: 13, fontWeight: 700, color: "#fff", lineHeight: 1.2 }}>EPI Monitor</div><div style={{ fontSize: 10, color: "rgba(255,255,255,0.25)" }}>Detecção de EPI</div></div>
            {isMobile && <button onClick={() => setSidebarOpen(false)} style={{ marginLeft: "auto", background: "none", border: "none", color: "rgba(255,255,255,0.4)", cursor: "pointer" }}>{Icons.x}</button>}
          </div>
          <nav style={{ padding: "4px 8px", flex: 1 }}>
            <div style={{ fontSize: 9, fontWeight: 600, color: "rgba(255,255,255,0.18)", padding: "10px 10px 6px", letterSpacing: 1.2, textTransform: "uppercase" }}>Menu</div>
            {NAV.map(item => {
              const a = page === item.id;
              return (
                <button key={item.id} onClick={() => { setPage(item.id); setSidebarOpen(false); }} style={{
                  display: "flex", alignItems: "center", gap: 9, width: "100%", padding: "8px 10px", borderRadius: 7,
                  background: a ? "rgba(255,255,255,0.06)" : "transparent",
                  border: a ? "1px solid rgba(255,255,255,0.05)" : "1px solid transparent",
                  color: a ? "rgba(255,255,255,0.9)" : "rgba(255,255,255,0.45)",
                  fontSize: 13, fontWeight: a ? 600 : 400, cursor: "pointer", transition: "all 0.15s",
                  textAlign: "left", marginBottom: 1, fontFamily: "'DM Sans',sans-serif",
                }}
                onMouseEnter={e => { if (!a) { e.currentTarget.style.background = "rgba(255,255,255,0.05)"; e.currentTarget.style.color = "rgba(255,255,255,0.75)"; }}}
                onMouseLeave={e => { if (!a) { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = "rgba(255,255,255,0.45)"; }}}>
                  <span style={{ opacity: a ? 1 : 0.45 }}>{item.icon}</span>{item.label}
                  {a && <span style={{ marginLeft: "auto", width: 5, height: 5, borderRadius: "50%", background: "#2563eb" }} />}
                </button>
              );
            })}
          </nav>
          <div style={{ padding: "12px 12px 14px", borderTop: "1px solid rgba(255,255,255,0.05)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ width: 30, height: 30, borderRadius: 7, background: "rgba(255,255,255,0.05)", display: "flex", alignItems: "center", justifyContent: "center", color: "rgba(255,255,255,0.35)" }}>{Icons.user}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 11, fontWeight: 500, color: "rgba(255,255,255,0.7)" }}>Admin</div>
                <div style={{ fontSize: 9, color: "rgba(255,255,255,0.2)" }}>admin@empresa.com</div>
              </div>
              <button onClick={api.logout} style={{ background: "none", border: "none", color: "rgba(255,255,255,0.2)", cursor: "pointer" }} onMouseEnter={e=>e.currentTarget.style.color="#ef4444"} onMouseLeave={e=>e.currentTarget.style.color="rgba(255,255,255,0.2)"}>{Icons.logout}</button>
            </div>
          </div>
        </aside>

        {/* Main */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
          <header style={{ height: 60, padding: "0 18px", display: "flex", alignItems: "center", justifyContent: "space-between", background: "var(--card)", borderBottom: "1px solid var(--border)", position: "sticky", top: 0, zIndex: 30 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              {isMobile && <button onClick={() => setSidebarOpen(true)} style={{ background: "none", border: "none", color: "var(--text)", cursor: "pointer" }}>{Icons.menu}</button>}
              <div style={{ display: "flex", alignItems: "center", gap: 5, padding: "4px 10px", borderRadius: 20, background: "#22c55e15", color: "#22c55e", fontSize: 11, fontWeight: 600 }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#22c55e", animation: "pulse 2s infinite" }} />Operacional
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <button style={{ width: 34, height: 34, borderRadius: 8, background: "var(--bg)", border: "1px solid var(--border)", color: "var(--muted)", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", position: "relative" }}>
                {Icons.bell}<span style={{ position: "absolute", top: 5, right: 5, width: 7, height: 7, borderRadius: "50%", background: "#ef4444", border: "2px solid var(--card)" }} />
              </button>
              <button style={{ width: 34, height: 34, borderRadius: 8, background: "var(--bg)", border: "1px solid var(--border)", color: "var(--muted)", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}>{Icons.settings}</button>
            </div>
          </header>
          <main style={{ flex: 1, padding: page === "monitoring" ? 0 : (isMobile ? 16 : 28), overflowY: page === "monitoring" ? "hidden" : "auto" }}>
            {page === "dashboard" && <DashboardPage cameras={cameras} />}
            {page === "cameras" && <CamerasPage />}
            {page === "monitoring" && <MonitoringPage />}
            {page === "classes" && <ClassesPage />}
            {page === "training" && <TrainingPage />}
            {page === "rules" && <RulesPage />}
            {page === "validations" && <ValidationPage />}
          </main>
        </div>
      </div>

      {/* Camera Form Modal */}
      <CameraForm
        isOpen={cameraModalOpen}
        onClose={() => {
          setCameraModalOpen(false);
          setEditingCamera(null);
        }}
        camera={editingCamera}
        onSave={handleSaveCamera}
      />

      {/* Toast Notifications */}
      <ToastContainer />
    </>
  );
}
