import { useState, useEffect, useRef } from "react";
import { useRouter } from 'next/navigation';
import VideoUploadZone from './components/VideoUploadZone'
import { decodeJWT, isTokenExpired, validateToken, formatTTL } from './lib/jwt-utils'

// Limpa todos os tokens e dados relacionados quando token está inválido/expirado
const clearInvalidToken = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('access_token')
  localStorage.removeItem('user')
  localStorage.removeItem('userRole')
  localStorage.removeItem('userName')
  console.log('🧹 Tokens inválidos limpos (clearInvalidToken)')
}

// Global token validation function - returns valid token or null
// Components must check for null and handle redirect themselves
const getValidToken = () => {
  const token = localStorage.getItem('token')
  if (!token) {
    return null
  }

  const tokenValidation = validateToken(token)
  if (tokenValidation === 'expired' || tokenValidation === 'invalid') {
    console.warn(`🔒 Token ${tokenValidation === 'expired' ? 'expirado' : 'inválido'} - limpando e retornando null`)
    clearInvalidToken()
    return null
  }

  if (tokenValidation === 'expiring-soon') {
    const payload = decodeJWT(token)
    const ttl = payload ? payload.exp - Math.floor(Date.now() / 1000) : 0
    console.log(`⏰ Token expirando em breve (${formatTTL(ttl)})`)
  }

  return token
}

// Icons as inline SVGs for zero dependencies
const Icons = {
  menu: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M3 12h18M3 6h18M3 18h18"/></svg>
  ),
  x: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
  ),
  dashboard: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
  ),
  camera: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z"/><circle cx="12" cy="13" r="4"/></svg>
  ),
  monitor: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>
  ),
  classes: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 002 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0022 16z"/><path d="M3.27 6.96L12 12.01l8.73-5.05M12 22.08V12"/></svg>
  ),
  training: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
  ),
  bell: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 01-3.46 0"/></svg>
  ),
  user: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
  ),
  plus: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M12 5v14M5 12h14"/></svg>
  ),
  search: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
  ),
  chevronRight: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M9 18l6-6-6-6"/></svg>
  ),
  wifi: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12.55a11 11 0 0114.08 0M1.42 9a16 16 0 0121.16 0M8.53 16.11a6 6 0 016.95 0M12 20h.01"/></svg>
  ),
  wifiOff: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 1l22 22M16.72 11.06A10.94 10.94 0 0119 12.55M5 12.55a10.94 10.94 0 015.17-2.39M10.71 5.05A16 16 0 0122.56 9M1.42 9a15.91 15.91 0 014.7-2.88M8.53 16.11a6 6 0 016.95 0M12 20h.01"/></svg>
  ),
  activity: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
  ),
  shield: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
  ),
  alertTriangle: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0zM12 9v4M12 17h.01"/></svg>
  ),
  check: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
  ),
  settings: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.32 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
  ),
  logout: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9"/></svg>
  ),
  eye: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
  ),
  edit: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
  ),
  trash: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
  ),
  play: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>
  ),
  grid: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
  ),
};

const CAMERAS = [
  { id: 1, name: "Entrada Principal", ip: "192.168.1.101", status: "online", location: "Portaria", model: "Intelbras VIP 3230", resolution: "1080p", active: true },
  { id: 2, name: "Área de Produção", ip: "192.168.1.102", status: "online", location: "Galpão A", model: "Hikvision DS-2CD", resolution: "4K", active: true },
  { id: 3, name: "Estacionamento", ip: "192.168.1.103", status: "offline", location: "Externo", model: "Intelbras VIP 1230", resolution: "720p", active: false },
  { id: 4, name: "Depósito", ip: "192.168.1.104", status: "online", location: "Galpão B", model: "Intelbras VIP 3230", resolution: "1080p", active: true },
  { id: 5, name: "Refeitório", ip: "192.168.1.105", status: "online", location: "Bloco C", model: "Hikvision DS-2CD", resolution: "1080p", active: true },
  { id: 6, name: "Saída Emergência", ip: "192.168.1.106", status: "online", location: "Lateral", model: "Intelbras VIP 1230", resolution: "720p", active: true },
];

const CLASSES = [
  { id: 1, name: "Capacete", color: "#22c55e", count: 1247, icon: "🪖", active: true },
  { id: 2, name: "Colete", color: "#f59e0b", count: 1089, icon: "🦺", active: true },
  { id: 3, name: "Óculos", color: "#3b82f6", count: 856, icon: "🥽", active: true },
  { id: 4, name: "Luvas", color: "#8b5cf6", count: 723, icon: "🧤", active: true },
  { id: 5, name: "Bota", color: "#ec4899", count: 945, icon: "👢", active: true },
  { id: 6, name: "Sem EPI", color: "#ef4444", count: 156, icon: "⚠️", active: true },
];

const ALERTS = [
  { id: 1, time: "14:32", camera: "Entrada Principal", type: "warning", message: "Operador sem capacete detectado" },
  { id: 2, time: "14:28", camera: "Área de Produção", type: "critical", message: "Múltiplas violações de EPI" },
  { id: 3, time: "14:15", camera: "Depósito", type: "info", message: "Todos os EPIs conformes" },
  { id: 4, time: "13:58", camera: "Refeitório", type: "warning", message: "Sem colete na área restrita" },
  { id: 5, time: "13:42", camera: "Entrada Principal", type: "info", message: "Detecção calibrada com sucesso" },
];

// Stat Card
const StatCard = ({ icon, label, value, sub, color, delay }) => (
  <div style={{
    background: "var(--card)",
    borderRadius: 16,
    padding: "20px 24px",
    display: "flex",
    alignItems: "center",
    gap: 16,
    animation: `fadeSlideUp 0.5s ease ${delay}s both`,
    border: "1px solid var(--border)",
    transition: "transform 0.2s, box-shadow 0.2s",
    cursor: "default",
  }}
  onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.boxShadow = "0 8px 32px rgba(0,0,0,0.12)"; }}
  onMouseLeave={e => { e.currentTarget.style.transform = ""; e.currentTarget.style.boxShadow = ""; }}
  >
    <div style={{
      width: 48, height: 48, borderRadius: 12,
      background: `${color}18`, color: color,
      display: "flex", alignItems: "center", justifyContent: "center",
      flexShrink: 0,
    }}>
      {icon}
    </div>
    <div style={{ minWidth: 0 }}>
      <div style={{ fontSize: 13, color: "var(--text-muted)", fontWeight: 500, marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color: "var(--text)", lineHeight: 1.1, fontFamily: "'DM Sans', sans-serif" }}>{value}</div>
      {sub && <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>{sub}</div>}
    </div>
  </div>
);

// Status badge
const StatusBadge = ({ status }) => {
  const isOnline = status === "online";
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 6,
      padding: "4px 10px", borderRadius: 20,
      fontSize: 12, fontWeight: 600,
      background: isOnline ? "#22c55e18" : "#ef444418",
      color: isOnline ? "#22c55e" : "#ef4444",
    }}>
      <span style={{
        width: 7, height: 7, borderRadius: "50%",
        background: isOnline ? "#22c55e" : "#ef4444",
        animation: isOnline ? "pulse 2s infinite" : "none",
      }} />
      {isOnline ? "Online" : "Offline"}
    </span>
  );
};

// Dashboard Page
const DashboardPage = () => {
  const onlineCount = CAMERAS.filter(c => c.status === "online").length;
  return (
    <div>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, color: "var(--text)", margin: 0, fontFamily: "'DM Sans', sans-serif" }}>Dashboard</h1>
        <p style={{ color: "var(--text-muted)", margin: "4px 0 0", fontSize: 14 }}>Visão geral do sistema de monitoramento</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16, marginBottom: 32 }}>
        <StatCard icon={Icons.camera} label="Câmeras" value={CAMERAS.length} sub={`${onlineCount} online`} color="#3b82f6" delay={0} />
        <StatCard icon={Icons.shield} label="Detecções Hoje" value="2.847" sub="+12% vs ontem" color="#22c55e" delay={0.05} />
        <StatCard icon={Icons.alertTriangle} label="Alertas" value="23" sub="7 críticos" color="#f59e0b" delay={0.1} />
        <StatCard icon={Icons.activity} label="Conformidade" value="94%" sub="Meta: 98%" color="#8b5cf6" delay={0.15} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        {/* Alerts */}
        <div style={{
          background: "var(--card)", borderRadius: 16, border: "1px solid var(--border)",
          padding: 24, animation: "fadeSlideUp 0.5s ease 0.2s both",
          gridColumn: "span 1",
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
            <h2 style={{ fontSize: 16, fontWeight: 600, color: "var(--text)", margin: 0 }}>Alertas Recentes</h2>
            <span style={{ fontSize: 12, color: "var(--accent)", cursor: "pointer", fontWeight: 500 }}>Ver todos</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {ALERTS.map((a, i) => (
              <div key={a.id} style={{
                display: "flex", alignItems: "flex-start", gap: 12,
                padding: "12px 14px", borderRadius: 10,
                background: "var(--bg)",
                animation: `fadeSlideUp 0.4s ease ${0.25 + i * 0.05}s both`,
              }}>
                <div style={{
                  width: 8, height: 8, borderRadius: "50%", marginTop: 6, flexShrink: 0,
                  background: a.type === "critical" ? "#ef4444" : a.type === "warning" ? "#f59e0b" : "#22c55e",
                }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, color: "var(--text)", fontWeight: 500 }}>{a.message}</div>
                  <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>
                    {a.camera} · {a.time}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Classes summary */}
        <div style={{
          background: "var(--card)", borderRadius: 16, border: "1px solid var(--border)",
          padding: 24, animation: "fadeSlideUp 0.5s ease 0.25s both",
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
            <h2 style={{ fontSize: 16, fontWeight: 600, color: "var(--text)", margin: 0 }}>Classes YOLO</h2>
            <span style={{ fontSize: 12, color: "var(--accent)", cursor: "pointer", fontWeight: 500 }}>Gerenciar</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {CLASSES.map((c, i) => (
              <div key={c.id} style={{
                display: "flex", alignItems: "center", gap: 12,
                animation: `fadeSlideUp 0.4s ease ${0.3 + i * 0.04}s both`,
              }}>
                <span style={{ fontSize: 18, width: 28, textAlign: "center" }}>{c.icon}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                    <span style={{ fontSize: 13, fontWeight: 500, color: "var(--text)" }}>{c.name}</span>
                    <span style={{ fontSize: 12, color: "var(--text-muted)", fontFamily: "'DM Mono', monospace" }}>{c.count.toLocaleString()}</span>
                  </div>
                  <div style={{ height: 4, borderRadius: 2, background: "var(--bg)" }}>
                    <div style={{
                      height: "100%", borderRadius: 2, background: c.color,
                      width: `${(c.count / 1300) * 100}%`,
                      transition: "width 0.8s ease",
                    }} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

// Cameras Page
const CamerasPage = () => {
  const [searchTerm, setSearchTerm] = useState("");
  const filtered = CAMERAS.filter(c =>
    c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.location.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 28, flexWrap: "wrap", gap: 16 }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 700, color: "var(--text)", margin: 0, fontFamily: "'DM Sans', sans-serif" }}>Câmeras</h1>
          <p style={{ color: "var(--text-muted)", margin: "4px 0 0", fontSize: 14 }}>Gerencie suas câmeras IP para detecção de EPI</p>
        </div>
        <button style={{
          display: "flex", alignItems: "center", gap: 8,
          padding: "10px 20px", borderRadius: 10,
          background: "var(--accent)", color: "#fff",
          border: "none", fontSize: 14, fontWeight: 600,
          cursor: "pointer", transition: "opacity 0.2s",
        }}
        onMouseEnter={e => e.currentTarget.style.opacity = 0.85}
        onMouseLeave={e => e.currentTarget.style.opacity = 1}
        >
          {Icons.plus} Nova Câmera
        </button>
      </div>

      {/* Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginBottom: 24 }}>
        {[
          { label: "Total", value: CAMERAS.length, color: "var(--accent)" },
          { label: "Online", value: CAMERAS.filter(c => c.status === "online").length, color: "#22c55e" },
          { label: "Offline", value: CAMERAS.filter(c => c.status === "offline").length, color: "#ef4444" },
          { label: "Ativas", value: CAMERAS.filter(c => c.active).length, color: "#f59e0b" },
        ].map((s, i) => (
          <div key={i} style={{
            background: "var(--card)", borderRadius: 12, padding: "16px 20px",
            border: "1px solid var(--border)",
            animation: `fadeSlideUp 0.4s ease ${i * 0.05}s both`,
          }}>
            <div style={{ fontSize: 12, color: "var(--text-muted)", fontWeight: 500, marginBottom: 4 }}>{s.label}</div>
            <div style={{ fontSize: 24, fontWeight: 700, color: s.color, fontFamily: "'DM Sans', sans-serif" }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Search */}
      <div style={{
        display: "flex", alignItems: "center", gap: 10,
        background: "var(--card)", border: "1px solid var(--border)",
        borderRadius: 10, padding: "10px 16px", marginBottom: 20,
      }}>
        <span style={{ color: "var(--text-muted)" }}>{Icons.search}</span>
        <input
          type="text"
          placeholder="Buscar câmera por nome ou local..."
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
          style={{
            background: "none", border: "none", outline: "none",
            color: "var(--text)", fontSize: 14, width: "100%",
            fontFamily: "inherit",
          }}
        />
      </div>

      {/* Camera Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: 16 }}>
        {filtered.map((cam, i) => (
          <div key={cam.id} style={{
            background: "var(--card)", borderRadius: 14, border: "1px solid var(--border)",
            overflow: "hidden",
            animation: `fadeSlideUp 0.4s ease ${0.1 + i * 0.05}s both`,
            transition: "transform 0.2s, box-shadow 0.2s",
          }}
          onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.boxShadow = "0 8px 32px rgba(0,0,0,0.1)"; }}
          onMouseLeave={e => { e.currentTarget.style.transform = ""; e.currentTarget.style.boxShadow = ""; }}
          >
            {/* Preview area */}
            <div style={{
              height: 160, background: cam.status === "online"
                ? "linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)"
                : "linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%)",
              display: "flex", alignItems: "center", justifyContent: "center",
              position: "relative", overflow: "hidden",
            }}>
              {cam.status === "online" ? (
                <>
                  <div style={{
                    position: "absolute", top: 0, left: 0, right: 0, bottom: 0,
                    background: "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(255,255,255,0.015) 2px, rgba(255,255,255,0.015) 4px)",
                  }} />
                  <div style={{ color: "rgba(255,255,255,0.3)", fontSize: 13, fontFamily: "'DM Mono', monospace", textAlign: "center" }}>
                    <div style={{ marginBottom: 4 }}>{Icons.camera}</div>
                    STREAM ATIVO
                  </div>
                  <div style={{
                    position: "absolute", top: 10, left: 10,
                    display: "flex", alignItems: "center", gap: 5,
                    background: "rgba(239,68,68,0.9)", padding: "3px 8px",
                    borderRadius: 4, fontSize: 11, fontWeight: 700, color: "#fff",
                    fontFamily: "'DM Mono', monospace",
                  }}>
                    <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#fff", animation: "pulse 1.5s infinite" }} />
                    REC
                  </div>
                  <div style={{
                    position: "absolute", bottom: 10, right: 10,
                    fontSize: 11, color: "rgba(255,255,255,0.5)", fontFamily: "'DM Mono', monospace",
                  }}>
                    {cam.resolution}
                  </div>
                </>
              ) : (
                <div style={{ color: "rgba(255,255,255,0.25)", fontSize: 13, textAlign: "center" }}>
                  <div style={{ marginBottom: 4, opacity: 0.5 }}>{Icons.wifiOff}</div>
                  SEM SINAL
                </div>
              )}
            </div>

            {/* Info */}
            <div style={{ padding: "16px 20px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 600, color: "var(--text)" }}>{cam.name}</div>
                  <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>{cam.location} · {cam.model}</div>
                </div>
                <StatusBadge status={cam.status} />
              </div>
              <div style={{ fontSize: 12, color: "var(--text-muted)", fontFamily: "'DM Mono', monospace", marginBottom: 14 }}>
                IP: {cam.ip}
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                {[
                  { icon: Icons.eye, label: "Ver" },
                  { icon: Icons.edit, label: "Editar" },
                  { icon: Icons.trash, label: "Remover" },
                ].map((action, j) => (
                  <button key={j} style={{
                    display: "flex", alignItems: "center", gap: 5,
                    padding: "6px 12px", borderRadius: 7,
                    background: "var(--bg)", border: "1px solid var(--border)",
                    color: j === 2 ? "#ef4444" : "var(--text-muted)",
                    fontSize: 12, cursor: "pointer",
                    transition: "all 0.15s",
                    fontFamily: "inherit",
                  }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = j === 2 ? "#ef4444" : "var(--accent)"; e.currentTarget.style.color = j === 2 ? "#ef4444" : "var(--accent)"; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = "var(--border)"; e.currentTarget.style.color = j === 2 ? "#ef4444" : "var(--text-muted)"; }}
                  >
                    {action.icon} {action.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Classes Page
const ClassesPage = () => (
  <div>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 28, flexWrap: "wrap", gap: 16 }}>
      <div>
        <h1 style={{ fontSize: 28, fontWeight: 700, color: "var(--text)", margin: 0, fontFamily: "'DM Sans', sans-serif" }}>Classes YOLO</h1>
        <p style={{ color: "var(--text-muted)", margin: "4px 0 0", fontSize: 14 }}>Configure as classes para detecção de EPI</p>
      </div>
      <button style={{
        display: "flex", alignItems: "center", gap: 8,
        padding: "10px 20px", borderRadius: 10,
        background: "var(--accent)", color: "#fff",
        border: "none", fontSize: 14, fontWeight: 600, cursor: "pointer",
      }}>
        {Icons.plus} Nova Classe
      </button>
    </div>

    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
      {CLASSES.map((cls, i) => (
        <div key={cls.id} style={{
          background: "var(--card)", borderRadius: 14, border: "1px solid var(--border)",
          padding: 24, animation: `fadeSlideUp 0.4s ease ${i * 0.06}s both`,
          transition: "transform 0.2s",
        }}
        onMouseEnter={e => e.currentTarget.style.transform = "translateY(-2px)"}
        onMouseLeave={e => e.currentTarget.style.transform = ""}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{
                fontSize: 28, width: 48, height: 48, borderRadius: 12,
                background: `${cls.color}15`, display: "flex", alignItems: "center", justifyContent: "center",
              }}>{cls.icon}</span>
              <div>
                <div style={{ fontSize: 16, fontWeight: 600, color: "var(--text)" }}>{cls.name}</div>
                <div style={{ fontSize: 12, color: "var(--text-muted)" }}>ID: class_{cls.id}</div>
              </div>
            </div>
            <div style={{
              width: 10, height: 10, borderRadius: "50%", background: cls.color,
              boxShadow: `0 0 8px ${cls.color}60`,
            }} />
          </div>
          <div style={{
            display: "flex", justifyContent: "space-between", alignItems: "center",
            padding: "12px 16px", background: "var(--bg)", borderRadius: 10,
          }}>
            <div>
              <div style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 500 }}>DETECÇÕES</div>
              <div style={{ fontSize: 22, fontWeight: 700, color: cls.color, fontFamily: "'DM Sans', sans-serif" }}>
                {cls.count.toLocaleString()}
              </div>
            </div>
            <div style={{ display: "flex", gap: 6 }}>
              <button style={{
                width: 32, height: 32, borderRadius: 8,
                background: "var(--card)", border: "1px solid var(--border)",
                color: "var(--text-muted)", display: "flex", alignItems: "center", justifyContent: "center",
                cursor: "pointer", transition: "all 0.15s",
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = "var(--accent)"; e.currentTarget.style.color = "var(--accent)"; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = "var(--border)"; e.currentTarget.style.color = "var(--text-muted)"; }}
              >{Icons.edit}</button>
              <button style={{
                width: 32, height: 32, borderRadius: 8,
                background: "var(--card)", border: "1px solid var(--border)",
                color: "var(--text-muted)", display: "flex", alignItems: "center", justifyContent: "center",
                cursor: "pointer", transition: "all 0.15s",
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = "#ef4444"; e.currentTarget.style.color = "#ef4444"; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = "var(--border)"; e.currentTarget.style.color = "var(--text-muted)"; }}
              >{Icons.trash}</button>
            </div>
          </div>
        </div>
      ))}
    </div>
  </div>
);

// Training Page
// Training Page with Tabs

const TrainingPage = () => {
  const [trainingTab, setTrainingTab] = useState('videos');
  const [annotatingVideoId, setAnnotatingVideoId] = useState(null);

  const renderTrainingTab = () => {
    switch(trainingTab) {
      case 'videos':
        return <TrainingVideosTab onAnnotate={(videoId) => {
          setAnnotatingVideoId(videoId);
          setTrainingTab('annotate');
        }} />;
      case 'annotate':
        return <TrainingAnnotateTab
          videoId={annotatingVideoId}
          onBack={() => {
            setAnnotatingVideoId(null);
            setTrainingTab('videos');
          }}
        />;
      case 'train':
        return <TrainingTrainTab />;
      case 'history':
        return <TrainingHistoryTab />;
      default:
        return <TrainingVideosTab onAnnotate={() => {}} />;
    }
  }

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Tab Navigation */}
      <div style={{
        display: 'flex',
        gap: '8px',
        marginBottom: '24px',
        borderBottom: '1px solid var(--border)',
        paddingBottom: '16px'
      }}>
        {[
          { id: 'videos', label: 'Vídeos & Dados' },
          { id: 'annotate', label: 'Anotar' },
          { id: 'train', label: 'Treinar' },
          { id: 'history', label: 'Histórico' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setTrainingTab(tab.id)}
            style={{
              padding: '10px 20px',
              background: trainingTab === tab.id ? 'rgba(37,99,235,0.8)' : 'transparent',
              color: trainingTab === tab.id ? '#fff' : 'var(--text)',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: trainingTab === tab.id ? '600' : '400',
              transition: 'all 0.15s'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {renderTrainingTab()}
    </div>
  )
}

// Helper function to format duration in seconds to MM:SS
const formatDuration = (seconds) => {
  if (!seconds) return '0:00'
  const secs = Math.floor(Number(seconds))  // Convert to number first
  const mins = Math.floor(secs / 60)
  const remainingSecs = secs % 60
  return `${mins}:${remainingSecs.toString().padStart(2, '0')}`
}

const TrainingVideosTab = ({ onAnnotate }) => {
  const router = useRouter()
  const [videos, setVideos] = useState([])
  const [timeSelectionModal, setTimeSelectionModal] = useState({
    open: false,
    videoId: null,
    videoDuration: 0,
    startSeconds: 0,
    endSeconds: 600
  })

  useEffect(() => {
    loadVideos()
  }, [])

  const loadVideos = async () => {
    try {
      const token = localStorage.getItem('token')

      // Verificar se token existe e não está expirado
      if (!token) {
        console.warn('⚠️ Nenhum token encontrado - redirecionando para login')
        router.push('/login')
        return
      }

      const tokenValidation = validateToken(token)
      if (tokenValidation === 'expired' || tokenValidation === 'invalid') {
        console.warn(`⚠️ Token ${tokenValidation === 'expired' ? 'expirado' : 'inválido'} - redirecionando para login`)
        clearInvalidToken()
        router.push('/login')
        return
      }

      if (tokenValidation === 'expiring-soon') {
        const payload = decodeJWT(token)
        const ttl = payload ? payload.exp - Math.floor(Date.now() / 1000) : 0
        console.log(`⏰ Token expirando em breve (${formatTTL(ttl)})`)
      }

      console.log('✅ Carregando vídeos (token válido)')

      const response = await fetch('/api/training/videos', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      // Tratar erro 401 especificamente
      if (response.status === 401) {
        console.warn('🔒 401 Unauthorized - limpando token expirado/inválido')
        clearInvalidToken()
        router.push('/login')
        return
      }

      const result = await response.json()
      if (result.success) {
        setVideos(result.videos)
      } else if (result.error) {
        console.error('❌ Erro ao carregar vídeos:', result.error)
        if (result.error.includes('token') || result.error.includes('401')) {
          clearInvalidToken()
          router.push('/login')
        }
      }
    } catch (error) {
      console.error('❌ Erro ao carregar vídeos:', error)
    }
  }

  const handleUploadComplete = (result) => {
    console.log('Upload complete:', result)
    loadVideos()
  }

  const handleExtractFrames = async (videoId, duration) => {
    // For videos > 10 minutes, show time selection modal
    if (duration > 600) {
      setTimeSelectionModal({
        open: true,
        videoId,
        videoDuration: duration,
        startSeconds: 0,
        endSeconds: Math.min(600, duration)
      })
      return
    }

    // For shorter videos, extract full video
    await extractFrames(videoId, {})
  }

  const extractFrames = async (videoId, body) => {
    try {
      const token = getValidToken()
      if (!token) {
        router.push('/login')
        return
      }

      const response = await fetch(`/api/training/videos/${videoId}/extract`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
      })

      if (response.status === 401) {
        clearInvalidToken()
        router.push('/login')
        return
      }

      const result = await response.json()
      if (result.success) {
        // Start polling for progress
        pollVideoProgress(videoId)
        // Close modal if open
        setTimeSelectionModal(prev => ({ ...prev, open: false }))
      } else {
        alert('Erro ao extrair frames: ' + result.error)
      }
    } catch (error) {
      console.error('Error extracting frames:', error)
      alert('Erro ao extrair frames')
    }
  }

  const handleTimeSelectionConfirm = () => {
    const { videoId, startSeconds, endSeconds } = timeSelectionModal
    extractFrames(videoId, {
      start_seconds: startSeconds,
      end_seconds: endSeconds
    })
  }

  const handleTimeSelectionChange = (field, value) => {
    const { videoDuration, startSeconds, endSeconds } = timeSelectionModal

    if (field === 'start') {
      // Ensure start doesn't exceed end - 600
      const maxStart = Math.min(videoDuration - 600, endSeconds - 600)
      const newStart = Math.min(Math.max(0, value), maxStart)
      setTimeSelectionModal(prev => ({
        ...prev,
        startSeconds: newStart,
        // Adjust end if needed to maintain max 600s gap
        endSeconds: Math.min(endSeconds, newStart + 600, videoDuration)
      }))
    } else if (field === 'end') {
      // Ensure end doesn't exceed start + 600
      const minEnd = startSeconds + 600
      const maxEnd = Math.min(videoDuration, startSeconds + 600)
      const newEnd = Math.max(minEnd, Math.min(value, maxEnd))
      setTimeSelectionModal(prev => ({
        ...prev,
        endSeconds: newEnd
      }))
    }
  }

  const pollVideoProgress = async (videoId) => {
    const token = getValidToken()
    if (!token) {
      router.push('/login')
      return
    }

    const poll = async () => {
      try {
        const response = await fetch(`/api/training/videos/${videoId}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })

        // Tratar erro 401 durante o polling
        if (response.status === 401) {
          console.warn('🔒 401 durante polling - token expirou')
          clearInvalidToken()
          router.push('/login')
          return
        }

        const result = await response.json()
        if (result.success) {
          const updatedVideo = result.video
          // Update video in list
          setVideos(prev => prev.map(v =>
            v.id === videoId ? { ...v, ...updatedVideo } : v
          ))

          // Stop polling if completed or error
          if (updatedVideo.status === 'completed' || updatedVideo.status === 'error') {
            return
          }

          // Continue polling if still extracting
          if (updatedVideo.status === 'extracting') {
            setTimeout(poll, 3000)
          }
        }
      } catch (error) {
        console.error('Error polling video progress:', error)
      }
    }

    poll()
  }

  const handleDeleteVideo = async (videoId) => {
    if (!confirm('Tem certeza que deseja excluir este vídeo?')) {
      return
    }

    try {
      const token = getValidToken()
      if (!token) {
        router.push('/login')
        return
      }

      const response = await fetch(`/api/training/videos/${videoId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (response.status === 401) {
        clearInvalidToken()
        router.push('/login')
        return
      }

      const result = await response.json()
      if (result.success) {
        setVideos(prev => prev.filter(v => v.id !== videoId))
      } else {
        alert('Erro ao excluir vídeo: ' + result.error)
      }
    } catch (error) {
      console.error('Error deleting video:', error)
      alert('Erro ao excluir vídeo')
    }
  }

  const getStatusBadge = (status) => {
    const statusConfig = {
      'uploaded': {
        label: 'Enviado',
        background: 'rgba(245, 158, 11, 0.1)',
        color: '#f59e0b'
      },
      'extracting': {
        label: 'Extraindo...',
        background: 'rgba(37, 99, 235, 0.1)',
        color: '#2563eb'
      },
      'completed': {
        label: 'Pronto',
        background: 'rgba(34, 197, 94, 0.1)',
        color: '#22c55e'
      },
      'error': {
        label: 'Erro',
        background: 'rgba(239, 68, 68, 0.1)',
        color: '#ef4444'
      }
    }

    const config = statusConfig[status] || statusConfig['uploaded']
    return (
      <div style={{
        display: 'inline-block',
        padding: '4px 12px',
        borderRadius: '12px',
        fontSize: '11px',
        fontWeight: '500',
        background: config.background,
        color: config.color
      }}>
        {config.label}
      </div>
    )
  }

  const renderVideoActions = (video) => {
    if (video.status === 'uploaded') {
      return (
        <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
          <button
            onClick={() => handleExtractFrames(video.id, video.duration)}
            style={{
              flex: 1,
              padding: '8px 16px',
              background: 'rgba(37, 99, 235, 0.8)',
              color: '#fff',
              border: 'none',
              borderRadius: '8px',
              fontSize: '13px',
              fontWeight: '500',
              cursor: 'pointer',
              transition: 'all 0.15s'
            }}
            onMouseEnter={(e) => e.target.style.background = 'rgba(37, 99, 235, 1)'}
            onMouseLeave={(e) => e.target.style.background = 'rgba(37, 99, 235, 0.8)'}
          >
            Extrair Frames
          </button>
          <button
            onClick={() => handleDeleteVideo(video.id)}
            style={{
              padding: '8px 16px',
              background: 'transparent',
              color: '#ef4444',
              border: '1px solid #ef4444',
              borderRadius: '8px',
              fontSize: '13px',
              fontWeight: '500',
              cursor: 'pointer',
              transition: 'all 0.15s'
            }}
          >
            Excluir
          </button>
        </div>
      )
    }

    if (video.status === 'extracting') {
      const progress = video.total_chunks > 0
        ? Math.round((video.processed_chunks / video.total_chunks) * 100)
        : 0

      return (
        <div style={{ marginTop: '12px' }}>
          <div style={{
            width: '100%',
            height: '6px',
            background: 'var(--border)',
            borderRadius: '3px',
            overflow: 'hidden',
            marginBottom: '8px'
          }}>
            <div style={{
              width: `${progress}%`,
              height: '100%',
              background: 'var(--accent)',
              transition: 'width 0.3s ease',
              borderRadius: '3px'
            }} />
          </div>
          <div style={{ fontSize: '12px', color: 'var(--muted)' }}>
            Processando chunk {video.processed_chunks} de {video.total_chunks} — {progress}%
          </div>
        </div>
      )
    }

    if (video.status === 'completed') {
      return (
        <div style={{ marginTop: '12px' }}>
          <div style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '8px' }}>
            Extração concluída — {video.frame_count || 0} frames extraídos
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => onAnnotate(video.id)}
              style={{
                flex: 1,
                padding: '8px 16px',
                background: 'rgba(37, 99, 235, 0.8)',
                color: '#fff',
                border: 'none',
                borderRadius: '8px',
                fontSize: '13px',
                fontWeight: '500',
                cursor: 'pointer',
                transition: 'all 0.15s'
              }}
              onMouseEnter={(e) => e.target.style.background = 'rgba(37, 99, 235, 1)'}
              onMouseLeave={(e) => e.target.style.background = 'rgba(37, 99, 235, 0.8)'}
            >
              Anotar Frames
            </button>
            <button
              onClick={() => handleDeleteVideo(video.id)}
              style={{
                padding: '8px 16px',
                background: 'transparent',
                color: '#ef4444',
                border: '1px solid #ef4444',
                borderRadius: '8px',
                fontSize: '13px',
                fontWeight: '500',
                cursor: 'pointer',
                transition: 'all 0.15s'
              }}
            >
              Excluir
            </button>
          </div>
        </div>
      )
    }

    return null
  }

  return (
    <div>
      <VideoUploadZone onUploadComplete={handleUploadComplete} />

      {videos.length > 0 && (
        <div style={{ marginTop: '32px' }}>
          <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '16px' }}>
            Vídeos ({videos.length})
          </h3>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
            gap: '16px'
          }}>
            {videos.map(video => (
              <div key={video.id} style={{
                background: 'var(--card)',
                border: '1px solid var(--border)',
                borderRadius: '14px',
                padding: '16px',
                transition: 'all 0.15s'
              }}>
                <div style={{ fontSize: '13px', color: 'var(--muted)', marginBottom: '6px', fontWeight: '500' }}>
                  {video.filename.length > 35 ? video.filename.substring(0, 35) + '...' : video.filename}
                </div>
                <div style={{ fontSize: '28px', fontWeight: '700', marginBottom: '6px', color: 'var(--text)' }}>
                  {formatDuration(video.duration)}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '10px' }}>
                  {video.total_chunks} chunks • {video.frame_count || 0} frames
                </div>
                {getStatusBadge(video.status)}
                {renderVideoActions(video)}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Time Selection Modal */}
      {timeSelectionModal.open && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.7)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            background: 'var(--card)',
            border: '1px solid var(--border)',
            borderRadius: '16px',
            padding: '32px',
            maxWidth: '600px',
            width: '90%',
            boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
            animation: 'fadeSlideUp 0.3s ease both'
          }}>
            <h2 style={{
              fontSize: '20px',
              fontWeight: '700',
              marginBottom: '8px',
              color: 'var(--text)'
            }}>
              Selecionar trecho para extração
            </h2>
            <p style={{
              fontSize: '14px',
              color: 'var(--muted)',
              marginBottom: '24px'
            }}>
              Duração total: {formatDuration(timeSelectionModal.videoDuration)} — Máximo: 10 minutos
            </p>

            {/* Time Range Slider */}
            <div style={{ marginBottom: '24px' }}>
              <label style={{
                fontSize: '13px',
                fontWeight: '500',
                marginBottom: '12px',
                display: 'block',
                color: 'var(--text)'
              }}>
                Início do trecho
              </label>
              <input
                type="range"
                min="0"
                max={Math.max(0, timeSelectionModal.videoDuration - 600)}
                value={timeSelectionModal.startSeconds}
                onChange={(e) => handleTimeSelectionChange('start', Number(e.target.value))}
                style={{
                  width: '100%',
                  marginBottom: '16px'
                }}
              />
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: '12px',
                color: 'var(--muted)',
                marginBottom: '20px'
              }}>
                <span>0:00</span>
                <span style={{ color: 'var(--text)', fontWeight: '600' }}>
                  {formatDuration(timeSelectionModal.startSeconds)}
                </span>
              </div>

              <label style={{
                fontSize: '13px',
                fontWeight: '500',
                marginBottom: '12px',
                display: 'block',
                color: 'var(--text)'
              }}>
                Fim do trecho
              </label>
              <input
                type="range"
                min={timeSelectionModal.startSeconds + 600}
                max={timeSelectionModal.videoDuration}
                value={timeSelectionModal.endSeconds}
                onChange={(e) => handleTimeSelectionChange('end', Number(e.target.value))}
                style={{
                  width: '100%',
                  marginBottom: '16px'
                }}
              />
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: '12px',
                color: 'var(--muted)',
                marginBottom: '20px'
              }}>
                <span>{formatDuration(timeSelectionModal.startSeconds + 600)}</span>
                <span style={{ color: 'var(--text)', fontWeight: '600' }}>
                  {formatDuration(timeSelectionModal.endSeconds)}
                </span>
              </div>
            </div>

            {/* Selection Summary */}
            <div style={{
              background: 'var(--bg)',
              borderRadius: '8px',
              padding: '16px',
              marginBottom: '24px'
            }}>
              <div style={{
                fontSize: '14px',
                color: 'var(--text)',
                textAlign: 'center',
                fontWeight: '500'
              }}>
                {formatDuration(timeSelectionModal.startSeconds)} → {formatDuration(timeSelectionModal.endSeconds)}
              </div>
              <div style={{
                fontSize: '12px',
                color: 'var(--muted)',
                textAlign: 'center',
                marginTop: '4px'
              }}>
                ({formatDuration(timeSelectionModal.endSeconds - timeSelectionModal.startSeconds)} selecionados)
              </div>
            </div>

            {/* Action Buttons */}
            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                onClick={() => setTimeSelectionModal(prev => ({ ...prev, open: false }))}
                style={{
                  flex: 1,
                  padding: '12px 24px',
                  background: 'transparent',
                  color: 'var(--text)',
                  border: '1px solid var(--border)',
                  borderRadius: '10px',
                  fontSize: '14px',
                  fontWeight: '500',
                  cursor: 'pointer',
                  transition: 'all 0.15s'
                }}
              >
                Cancelar
              </button>
              <button
                onClick={handleTimeSelectionConfirm}
                style={{
                  flex: 1,
                  padding: '12px 24px',
                  background: 'rgba(37, 99, 235, 0.8)',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '10px',
                  fontSize: '14px',
                  fontWeight: '600',
                  cursor: 'pointer',
                  transition: 'all 0.15s'
                }}
                onMouseEnter={(e) => e.target.style.background = 'rgba(37, 99, 235, 1)'}
                onMouseLeave={(e) => e.target.style.background = 'rgba(37, 99, 235, 0.8)'}
              >
                Confirmar e Extrair
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}


const TrainingAnnotateTab = ({ videoId, onBack }) => {
  const [frames, setFrames] = useState([])
  const [selectedFrame, setSelectedFrame] = useState(null)
  const [loading, setLoading] = useState(false)
  const timelineRef = useRef(null)

  useEffect(() => {
    if (videoId) {
      loadFrames()
    }
  }, [videoId])

  // Scroll selected frame into view in timeline
  useEffect(() => {
    if (selectedFrame && timelineRef.current) {
      const timeline = timelineRef.current
      const selectedElement = timeline.querySelector(`[data-frame-id="${selectedFrame.id}"]`)
      if (selectedElement) {
        const timelineRect = timeline.getBoundingClientRect()
        const elementRect = selectedElement.getBoundingClientRect()
        const scrollLeft = timeline.scrollLeft + (elementRect.left - timelineRect.left) - (timelineRect.width / 2) + (elementRect.width / 2)
        timeline.scrollTo({ left: scrollLeft, behavior: 'smooth' })
      }
    }
  }, [selectedFrame])

  const loadFrames = async () => {
    if (!videoId) return

    const token = getValidToken()
    if (!token) {
      router.push('/login')
      return
    }

    setLoading(true)
    try {
      const response = await fetch(`/api/training/videos/${videoId}/frames`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      // Tratar erro 401
      if (response.status === 401) {
        console.warn('🔒 401 ao carregar frames - token expirou')
        clearInvalidToken()
        router.push('/login')
        return
      }

      const result = await response.json()
      if (result.success && result.frames) {
        setFrames(result.frames)
        if (result.frames.length > 0) {
          setSelectedFrame(result.frames[0])
        }
      } else {
        console.error('Failed to load frames:', result.error)
      }
    } catch (error) {
      console.error('Error loading frames:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleFrameSelect = (frame) => {
    setSelectedFrame(frame)
  }

  const handlePrevFrame = () => {
    if (!selectedFrame) return
    const currentIndex = frames.findIndex(f => f.id === selectedFrame.id)
    if (currentIndex > 0) {
      setSelectedFrame(frames[currentIndex - 1])
    }
  }

  const handleNextFrame = () => {
    if (!selectedFrame) return
    const currentIndex = frames.findIndex(f => f.id === selectedFrame.id)
    if (currentIndex < frames.length - 1) {
      setSelectedFrame(frames[currentIndex + 1])
    }
  }

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'ArrowLeft') {
        handlePrevFrame()
      } else if (e.key === 'ArrowRight') {
        handleNextFrame()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedFrame, frames])

  return (
    <div style={{
      background: '#0d1117',
      minHeight: 'calc(100vh - 100px)',
      padding: '0'
    }}>
      {/* Header */}
      <div style={{
        background: '#161b22',
        borderBottom: '1px solid var(--border)',
        padding: '16px 24px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <button
          onClick={onBack}
          style={{
            padding: '8px 16px',
            background: 'transparent',
            color: 'var(--text)',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            fontSize: '13px',
            fontWeight: '500',
            cursor: 'pointer',
            transition: 'all 0.15s'
          }}
        >
          ← Voltar
        </button>
        <h2 style={{
          fontSize: '18px',
          fontWeight: '600',
          color: 'var(--text)',
          margin: 0
        }}>
          Anotação de Frames
        </h2>
        <div style={{ width: '89px' }} /> {/* Spacer for alignment */}
      </div>

      {!videoId ? (
        <div style={{
          textAlign: 'center',
          padding: '80px 20px',
          color: 'var(--muted)'
        }}>
          <p style={{ fontSize: '16px', marginBottom: '16px' }}>
            Nenhum vídeo selecionado
          </p>
          <button
            onClick={onBack}
            style={{
              padding: '10px 24px',
              background: 'rgba(37, 99, 235, 0.8)',
              color: '#fff',
              border: 'none',
              borderRadius: '8px',
              fontSize: '14px',
              fontWeight: '500',
              cursor: 'pointer'
            }}
          >
            Selecionar um vídeo
          </button>
        </div>
      ) : loading ? (
        <div style={{
          textAlign: 'center',
          padding: '80px 20px',
          color: 'var(--muted)'
        }}>
          <p>Carregando frames...</p>
        </div>
      ) : frames.length === 0 ? (
        <div style={{
          textAlign: 'center',
          padding: '80px 20px',
          color: 'var(--muted)'
        }}>
          <p>Nenhum frame encontrado</p>
          <p style={{ fontSize: '13px', marginTop: '8px' }}>
            Extraia os frames primeiro
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 80px)' }}>
          {/* Main Frame Display Area */}
          <div style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            background: '#0d1117',
            minHeight: 0
          }}>
            {/* Toolbar */}
            <div style={{
              background: '#161b22',
              borderBottom: '1px solid var(--border)',
              padding: '12px 24px',
              display: 'flex',
              gap: '8px'
            }}>
              <button style={{
                padding: '8px 16px',
                background: 'rgba(37, 99, 235, 0.8)',
                color: '#fff',
                border: 'none',
                borderRadius: '6px',
                fontSize: '13px',
                fontWeight: '500',
                cursor: 'pointer'
              }}>
                Desenhar
              </button>
              <button style={{
                padding: '8px 16px',
                background: 'transparent',
                color: 'var(--text)',
                border: '1px solid var(--border)',
                borderRadius: '6px',
                fontSize: '13px',
                fontWeight: '500',
                cursor: 'pointer'
              }}>
                Selecionar
              </button>
              <button style={{
                padding: '8px 16px',
                background: 'transparent',
                color: 'var(--text)',
                border: '1px solid var(--border)',
                borderRadius: '6px',
                fontSize: '13px',
                fontWeight: '500',
                cursor: 'pointer'
              }}>
                Apagar
              </button>
              <button style={{
                padding: '8px 16px',
                background: 'transparent',
                color: 'var(--text)',
                border: '1px solid var(--border)',
                borderRadius: '6px',
                fontSize: '13px',
                fontWeight: '500',
                cursor: 'pointer'
              }}>
                Auto-Detect
              </button>
            </div>

            {/* Frame Display */}
            <div style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '24px',
              overflow: 'auto',
              minHeight: 0
            }}>
              {selectedFrame ? (
                <img
                  src={`/api/training/frames/${selectedFrame.id}/image`}
                  alt={`Frame ${selectedFrame.frame_number}`}
                  style={{
                    maxWidth: '100%',
                    maxHeight: '100%',
                    display: 'block',
                    objectFit: 'contain'
                  }}
                />
              ) : (
                <div style={{
                  textAlign: 'center',
                  color: 'var(--muted)'
                }}>
                  <p>Selecione um frame na timeline</p>
                </div>
              )}
            </div>

            {/* Progress Bar */}
            <div style={{
              background: '#161b22',
              borderTop: '1px solid var(--border)',
              borderBottom: '1px solid var(--border)',
              padding: '8px 24px',
              fontFamily: "'DM Mono', monospace",
              fontSize: '12px',
              color: 'rgba(255, 255, 255, 0.6)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <span>
                {selectedFrame
                  ? `Frame ${frames.findIndex(f => f.id === selectedFrame.id) + 1}/${frames.length}`
                  : 'Frame -/-'
                }
              </span>
              <div style={{
                display: 'flex',
                gap: '16px',
                alignItems: 'center'
              }}>
                <button
                  onClick={handlePrevFrame}
                  disabled={!selectedFrame || frames.findIndex(f => f.id === selectedFrame.id) === 0}
                  style={{
                    padding: '4px 8px',
                    background: 'transparent',
                    color: selectedFrame && frames.findIndex(f => f.id === selectedFrame.id) > 0 ? 'var(--text)' : 'var(--muted)',
                    border: '1px solid var(--border)',
                    borderRadius: '4px',
                    fontSize: '14px',
                    cursor: 'pointer',
                    opacity: selectedFrame && frames.findIndex(f => f.id === selectedFrame.id) > 0 ? 1 : 0.5
                  }}
                >
                  ←
                </button>
                <span>Boxes: 0</span>
                <button
                  onClick={handleNextFrame}
                  disabled={!selectedFrame || frames.findIndex(f => f.id === selectedFrame.id) === frames.length - 1}
                  style={{
                    padding: '4px 8px',
                    background: 'transparent',
                    color: selectedFrame && frames.findIndex(f => f.id === selectedFrame.id) < frames.length - 1 ? 'var(--text)' : 'var(--muted)',
                    border: '1px solid var(--border)',
                    borderRadius: '4px',
                    fontSize: '14px',
                    cursor: 'pointer',
                    opacity: selectedFrame && frames.findIndex(f => f.id === selectedFrame.id) < frames.length - 1 ? 1 : 0.5
                  }}
                >
                  →
                </button>
              </div>
            </div>
          </div>

          {/* Timeline Bar */}
          <div style={{
            height: '120px',
            background: '#0d1117',
            borderTop: '1px solid var(--border)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden'
          }}>
            {/* Thumbnails Scroll */}
            <div
              ref={timelineRef}
              style={{
                flex: 1,
                display: 'flex',
                gap: '4px',
                padding: '12px',
                overflowX: 'auto',
                overflowY: 'hidden',
                alignItems: 'center',
                // Custom scrollbar
                scrollbarWidth: 'thin',
                scrollbarColor: 'rgba(255, 255, 255, 0.1) transparent',
              }}>
              {frames.map((frame, index) => {
                const isSelected = selectedFrame?.id === frame.id
                return (
                  <div
                    key={frame.id}
                    data-frame-id={frame.id}
                    onClick={() => handleFrameSelect(frame)}
                    style={{
                      position: 'relative',
                      flex: '0 0 auto',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                      transform: isSelected ? 'scale(1.05)' : 'scale(1)',
                      transformOrigin: 'center bottom'
                    }}
                  >
                    {/* Thumbnail */}
                    <div style={{
                      width: '80px',
                      height: '50px',
                      borderRadius: '4px',
                      overflow: 'hidden',
                      border: isSelected
                        ? '2px solid #2563eb'
                        : '1px solid rgba(255, 255, 255, 0.1)',
                      background: '#161b22',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}>
                      <img
                        src={`/api/training/frames/${frame.id}/image`}
                        alt={`Frame ${frame.frame_number}`}
                        style={{
                          width: '100%',
                          height: '100%',
                          objectFit: 'cover',
                          display: 'block'
                        }}
                        loading="lazy"
                      />
                      {/* Annotated indicator */}
                      {frame.is_annotated && (
                        <div style={{
                          position: 'absolute',
                          top: '4px',
                          right: '4px',
                          width: '8px',
                          height: '8px',
                          borderRadius: '50%',
                          background: '#2563eb',
                          border: '1px solid rgba(0, 0, 0, 0.3)'
                        }} />
                      )}
                    </div>
                    {/* Timestamp */}
                    <div style={{
                      fontFamily: "'DM Mono', monospace",
                      fontSize: '10px',
                      color: 'rgba(255, 255, 255, 0.3)',
                      textAlign: 'center',
                      marginTop: '4px',
                      whiteSpace: 'nowrap'
                    }}>
                      {Math.floor(frame.frame_number / 2)}s
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const TrainingTrainTab = () => {
  const [isTraining, setIsTraining] = useState(false);
  const [progress, setProgress] = useState(0);

  const metrics = [
    { label: "Precisão", value: "96.8%", trend: "+2.1%" },
    { label: "Recall", value: "94.2%", trend: "+1.8%" },
    { label: "mAP@50", value: "0.952", trend: "+0.03" },
    { label: "Loss", value: "0.041", trend: "-0.008" },
  ];

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, color: "var(--text)", margin: 0, fontFamily: "'DM Sans', sans-serif" }}>Treinamento</h1>
        <p style={{ color: "var(--text-muted)", margin: "4px 0 0", fontSize: 14 }}>Acompanhe e gerencie o treinamento do modelo YOLO</p>
      </div>

      {/* Training control */}
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
              Modelo: YOLOv8n · Dataset: 4.860 imagens · 6 classes
            </p>
          </div>
          <button
            onClick={() => { if (!isTraining && progress < 100) { setIsTraining(true); } else { setProgress(0); setIsTraining(false); } }}
            style={{
              display: "flex", alignItems: "center", gap: 8,
              padding: "10px 24px", borderRadius: 10,
              background: isTraining ? "#ef444420" : progress >= 100 ? "var(--accent)" : "var(--accent)",
              color: isTraining ? "#ef4444" : "#fff",
              border: isTraining ? "1px solid #ef444440" : "none",
              fontSize: 14, fontWeight: 600, cursor: "pointer",
            }}
          >
            {isTraining ? Icons.x : Icons.play}
            {isTraining ? "Parar" : progress >= 100 ? "Novo Treinamento" : "Iniciar"}
          </button>
        </div>

        {/* Progress bar */}
        <div style={{ background: "var(--bg)", borderRadius: 8, height: 8, overflow: "hidden", marginBottom: 8 }}>
          <div style={{
            height: "100%", borderRadius: 8,
            background: progress >= 100 ? "#22c55e" : "var(--accent)",
            width: `${progress}%`,
            transition: "width 0.3s ease",
          }} />
        </div>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span style={{ fontSize: 12, color: "var(--text-muted)", fontFamily: "'DM Mono', monospace" }}>
            Epoch {Math.floor(progress / 2)}/50
          </span>
          <span style={{ fontSize: 12, color: "var(--text-muted)", fontFamily: "'DM Mono', monospace" }}>
            {progress.toFixed(1)}%
          </span>
        </div>
      </div>

      {/* Metrics */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 14 }}>
        {metrics.map((m, i) => (
          <div key={i} style={{
            background: "var(--card)", borderRadius: 14, border: "1px solid var(--border)",
            padding: 20, animation: `fadeSlideUp 0.4s ease ${0.1 + i * 0.05}s both`,
          }}>
            <div style={{ fontSize: 12, color: "var(--text-muted)", fontWeight: 500, marginBottom: 6 }}>{m.label}</div>
            <div style={{ fontSize: 26, fontWeight: 700, color: "var(--text)", fontFamily: "'DM Sans', sans-serif" }}>{m.value}</div>
            <div style={{ fontSize: 12, color: m.trend.startsWith("+") || m.trend.startsWith("-0") ? "#22c55e" : "#ef4444", fontWeight: 500, marginTop: 4 }}>
              {m.trend}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const TrainingHistoryTab = () => (
  <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--muted)' }}>
    <p>Histórico - Lista de treinamentos anteriores</p>
  </div>
)


// Monitoring Page
const MonitoringPage = () => {
  const [grid, setGrid] = useState("2x2");
  const [time, setTime] = useState(new Date());
  const onlineCameras = CAMERAS.filter(c => c.status === "online");

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const cols = grid === "1x1" ? 1 : grid === "2x2" ? 2 : 3;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20, flexWrap: "wrap", gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 700, color: "var(--text)", margin: 0, fontFamily: "'DM Sans', sans-serif" }}>Monitoramento</h1>
          <p style={{ color: "var(--text-muted)", margin: "4px 0 0", fontSize: 14 }}>
            {time.toLocaleTimeString("pt-BR")} · {onlineCameras.length} câmeras ativas
          </p>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          {["1x1", "2x2", "3x3"].map(g => (
            <button key={g} onClick={() => setGrid(g)} style={{
              padding: "7px 14px", borderRadius: 8,
              background: grid === g ? "var(--accent)" : "var(--card)",
              color: grid === g ? "#fff" : "var(--text-muted)",
              border: grid === g ? "none" : "1px solid var(--border)",
              fontSize: 13, fontWeight: 600, cursor: "pointer",
              fontFamily: "'DM Mono', monospace",
            }}>
              {g}
            </button>
          ))}
        </div>
      </div>

      <div style={{
        display: "grid",
        gridTemplateColumns: `repeat(${cols}, 1fr)`,
        gap: 8,
      }}>
        {onlineCameras.slice(0, cols * cols).map((cam, i) => (
          <div key={cam.id} style={{
            borderRadius: 10, overflow: "hidden",
            background: "linear-gradient(135deg, #0a0e1a 0%, #111827 50%, #0f172a 100%)",
            aspectRatio: "16/10",
            position: "relative",
            border: "1px solid rgba(255,255,255,0.06)",
            animation: `fadeSlideUp 0.4s ease ${i * 0.05}s both`,
          }}>
            {/* Scanlines */}
            <div style={{
              position: "absolute", inset: 0, zIndex: 1,
              background: "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(255,255,255,0.01) 2px, rgba(255,255,255,0.01) 4px)",
              pointerEvents: "none",
            }} />

            {/* Center cam icon */}
            <div style={{
              position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
              color: "rgba(255,255,255,0.1)",
            }}>
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                <path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z"/>
                <circle cx="12" cy="13" r="4"/>
              </svg>
            </div>

            {/* Top overlay */}
            <div style={{
              position: "absolute", top: 0, left: 0, right: 0, zIndex: 2,
              padding: "10px 14px",
              display: "flex", justifyContent: "space-between", alignItems: "center",
              background: "linear-gradient(180deg, rgba(0,0,0,0.6) 0%, transparent 100%)",
            }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: "#fff", fontFamily: "'DM Sans', sans-serif" }}>{cam.name}</span>
              <div style={{
                display: "flex", alignItems: "center", gap: 5,
                background: "rgba(239,68,68,0.85)", padding: "2px 7px",
                borderRadius: 4, fontSize: 10, fontWeight: 700, color: "#fff",
                fontFamily: "'DM Mono', monospace",
              }}>
                <span style={{ width: 5, height: 5, borderRadius: "50%", background: "#fff", animation: "pulse 1.5s infinite" }} />
                REC
              </div>
            </div>

            {/* Bottom overlay */}
            <div style={{
              position: "absolute", bottom: 0, left: 0, right: 0, zIndex: 2,
              padding: "10px 14px",
              background: "linear-gradient(0deg, rgba(0,0,0,0.7) 0%, transparent 100%)",
              display: "flex", justifyContent: "space-between", alignItems: "flex-end",
            }}>
              <div style={{ fontSize: 11, color: "rgba(255,255,255,0.6)", fontFamily: "'DM Mono', monospace" }}>
                {cam.location} · {cam.ip}
              </div>
              <div style={{ fontSize: 11, color: "rgba(255,255,255,0.6)", fontFamily: "'DM Mono', monospace" }}>
                {time.toLocaleTimeString("pt-BR")}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Navigation items
const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: Icons.dashboard },
  { id: "cameras", label: "Câmeras", icon: Icons.camera },
  { id: "monitoring", label: "Monitoramento", icon: Icons.monitor },
  { id: "classes", label: "Classes", icon: Icons.classes },
  { id: "training", label: "Treinamento", icon: Icons.training },
];

// Main App
function App() {
  const [page, setPage] = useState("dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  const renderPage = () => {
    switch (page) {
      case "cameras": return <CamerasPage />;
      case "monitoring": return <MonitoringPage />;
      case "classes": return <ClassesPage />;
      case "training": return <TrainingPage />;
      default: return <DashboardPage />;
    }
  };

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=DM+Mono:wght@400;500&display=swap');

        :root {
          --bg: #f8f9fb;
          --card: #ffffff;
          --border: #e8ecf1;
          --text: #111827;
          --text-muted: #6b7280;
          --accent: #2563eb;
          --accent-hover: #1d4ed8;
          --sidebar-bg: #111827;
          --sidebar-text: rgba(255,255,255,0.55);
          --sidebar-active: rgba(255,255,255,0.95);
          --sidebar-hover: rgba(255,255,255,0.08);
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'DM Sans', -apple-system, sans-serif; }

        @keyframes fadeSlideUp {
          from { opacity: 0; transform: translateY(12px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }

        /* Custom scrollbar */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

        /* Responsive grid override */
        @media (max-width: 768px) {
          .dashboard-grid-2col { grid-template-columns: 1fr !important; }
        }
      `}</style>

      <div style={{ display: "flex", minHeight: "100vh", background: "var(--bg)", fontFamily: "'DM Sans', sans-serif" }}>
        {/* Mobile Overlay */}
        {isMobile && sidebarOpen && (
          <div
            onClick={() => setSidebarOpen(false)}
            style={{
              position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
              zIndex: 40, backdropFilter: "blur(4px)",
            }}
          />
        )}

        {/* Sidebar */}
        <aside style={{
          width: isMobile ? 260 : 240,
          background: "var(--sidebar-bg)",
          position: isMobile ? "fixed" : "sticky",
          top: 0,
          left: isMobile ? (sidebarOpen ? 0 : -280) : 0,
          height: "100vh",
          zIndex: 50,
          display: "flex",
          flexDirection: "column",
          transition: "left 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
          borderRight: "1px solid rgba(255,255,255,0.06)",
          overflowY: "auto",
        }}>
          {/* Logo */}
          <div style={{
            padding: "24px 20px 20px",
            display: "flex", alignItems: "center", justifyContent: "space-between",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{
                width: 36, height: 36, borderRadius: 10,
                background: "linear-gradient(135deg, #2563eb, #7c3aed)",
                display: "flex", alignItems: "center", justifyContent: "center",
                color: "#fff", fontWeight: 800, fontSize: 15,
                fontFamily: "'DM Sans', sans-serif",
              }}>EP</div>
              <div>
                <div style={{ fontSize: 15, fontWeight: 700, color: "#fff", lineHeight: 1.2 }}>EPI Monitor</div>
                <div style={{ fontSize: 11, color: "rgba(255,255,255,0.35)", fontWeight: 400 }}>Sistema de Detecção</div>
              </div>
            </div>
            {isMobile && (
              <button onClick={() => setSidebarOpen(false)} style={{
                background: "none", border: "none", color: "rgba(255,255,255,0.5)", cursor: "pointer",
              }}>{Icons.x}</button>
            )}
          </div>

          {/* Nav */}
          <nav style={{ padding: "8px 12px", flex: 1 }}>
            <div style={{ fontSize: 10, fontWeight: 600, color: "rgba(255,255,255,0.25)", padding: "12px 12px 8px", letterSpacing: 1, textTransform: "uppercase" }}>
              Menu
            </div>
            {NAV_ITEMS.map(item => {
              const active = page === item.id;
              return (
                <button key={item.id} onClick={() => { setPage(item.id); setSidebarOpen(false); }} style={{
                  display: "flex", alignItems: "center", gap: 12,
                  width: "100%", padding: "10px 12px", borderRadius: 10,
                  background: active ? "var(--sidebar-hover)" : "transparent",
                  border: active ? "1px solid rgba(255,255,255,0.06)" : "1px solid transparent",
                  color: active ? "var(--sidebar-active)" : "var(--sidebar-text)",
                  fontSize: 14, fontWeight: active ? 600 : 400,
                  cursor: "pointer", transition: "all 0.15s",
                  textAlign: "left", marginBottom: 2,
                  fontFamily: "'DM Sans', sans-serif",
                }}
                onMouseEnter={e => { if (!active) { e.currentTarget.style.background = "var(--sidebar-hover)"; e.currentTarget.style.color = "rgba(255,255,255,0.8)"; }}}
                onMouseLeave={e => { if (!active) { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = "var(--sidebar-text)"; }}}
                >
                  <span style={{ opacity: active ? 1 : 0.6 }}>{item.icon}</span>
                  {item.label}
                  {active && <span style={{ marginLeft: "auto", width: 6, height: 6, borderRadius: "50%", background: "#2563eb" }} />}
                </button>
              );
            })}
          </nav>

          {/* User */}
          <div style={{
            padding: "16px 16px 20px",
            borderTop: "1px solid rgba(255,255,255,0.06)",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{
                width: 34, height: 34, borderRadius: 10,
                background: "rgba(255,255,255,0.08)",
                display: "flex", alignItems: "center", justifyContent: "center",
                color: "rgba(255,255,255,0.5)",
              }}>{Icons.user}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 500, color: "rgba(255,255,255,0.8)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>Admin</div>
                <div style={{ fontSize: 11, color: "rgba(255,255,255,0.3)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>admin@empresa.com</div>
              </div>
              <button style={{
                background: "none", border: "none", color: "rgba(255,255,255,0.3)",
                cursor: "pointer", padding: 4, borderRadius: 6,
                transition: "color 0.15s",
              }}
              onMouseEnter={e => e.currentTarget.style.color = "#ef4444"}
              onMouseLeave={e => e.currentTarget.style.color = "rgba(255,255,255,0.3)"}
              >{Icons.logout}</button>
            </div>
          </div>
        </aside>

        {/* Main */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
          {/* Top bar */}
          <header style={{
            height: 60, padding: "0 24px",
            display: "flex", alignItems: "center", justifyContent: "space-between",
            background: "var(--card)",
            borderBottom: "1px solid var(--border)",
            position: "sticky", top: 0, zIndex: 30,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              {isMobile && (
                <button onClick={() => setSidebarOpen(true)} style={{
                  background: "none", border: "none", color: "var(--text)",
                  cursor: "pointer", padding: 4,
                }}>{Icons.menu}</button>
              )}
              <div style={{
                display: "flex", alignItems: "center", gap: 6,
                padding: "6px 12px", borderRadius: 20,
                background: "#22c55e15", color: "#22c55e",
                fontSize: 12, fontWeight: 600,
              }}>
                <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#22c55e", animation: "pulse 2s infinite" }} />
                Sistema Operacional
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <button style={{
                width: 38, height: 38, borderRadius: 10,
                background: "var(--bg)", border: "1px solid var(--border)",
                color: "var(--text-muted)", display: "flex", alignItems: "center", justifyContent: "center",
                cursor: "pointer", position: "relative",
              }}>
                {Icons.bell}
                <span style={{
                  position: "absolute", top: 6, right: 7,
                  width: 8, height: 8, borderRadius: "50%",
                  background: "#ef4444", border: "2px solid var(--card)",
                }} />
              </button>
              <button style={{
                width: 38, height: 38, borderRadius: 10,
                background: "var(--bg)", border: "1px solid var(--border)",
                color: "var(--text-muted)", display: "flex", alignItems: "center", justifyContent: "center",
                cursor: "pointer",
              }}>
                {Icons.settings}
              </button>
            </div>
          </header>

          {/* Content */}
          <main className="dashboard-grid-2col" style={{ flex: 1, padding: isMobile ? 16 : 28, overflowY: "auto" }}>
            {renderPage()}
          </main>
        </div>
      </div>
    </>
  );
}

export default App;
