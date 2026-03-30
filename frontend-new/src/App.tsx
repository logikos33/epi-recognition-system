import { useState, useEffect, useRef, useCallback } from "react";
import { useCameras } from "./hooks/useCameras";
import { useStreams } from "./hooks/useStreams";
import { useToast } from "./hooks/useToast";
import CameraForm from "./components/CameraForm";
import Modal from "./components/Modal";
import ToastContainer from "./components/Toast";

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

// ── Dashboard ──
const DashboardPage = ({ cameras }) => (
  <div>
    <div style={{ marginBottom: 32 }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, color: "var(--text)", margin: 0 }}>Dashboard</h1>
      <p style={{ color: "var(--muted)", margin: "4px 0 0", fontSize: 14 }}>Visão geral do sistema de monitoramento</p>
    </div>
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16, marginBottom: 32 }}>
      <StatCard icon={Icons.camera} label="Câmeras" value={cameras.length} sub={`${cameras.filter(c=>c.status==="online").length} online`} color="#3b82f6" delay={0} />
      <StatCard icon={Icons.shield} label="Detecções Hoje" value="2.847" sub="+12% vs ontem" color="#22c55e" delay={0.05} />
      <StatCard icon={Icons.alertTriangle} label="Alertas" value="23" sub="7 críticos" color="#f59e0b" delay={0.1} />
      <StatCard icon={Icons.activity} label="Conformidade" value="94%" sub="Meta: 98%" color="#8b5cf6" delay={0.15} />
    </div>
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: 20 }}>
      <div style={{ background: "var(--card)", borderRadius: 16, border: "1px solid var(--border)", padding: 24, animation: "fadeUp 0.5s ease 0.2s both" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, color: "var(--text)", margin: 0 }}>Alertas Recentes</h2>
          <span style={{ fontSize: 12, color: "var(--accent)", cursor: "pointer", fontWeight: 500 }}>Ver todos</span>
        </div>
        {ALERTS.map((a, i) => (
          <div key={a.id} style={{ display: "flex", alignItems: "flex-start", gap: 12, padding: "11px 14px", borderRadius: 10, background: "var(--bg)", marginBottom: 8, animation: `fadeUp 0.4s ease ${0.25+i*0.05}s both` }}>
            <div style={{ width: 8, height: 8, borderRadius: "50%", marginTop: 6, flexShrink: 0, background: a.type==="critical"?"#ef4444":a.type==="warning"?"#f59e0b":"#22c55e" }} />
            <div><div style={{ fontSize: 13, color: "var(--text)", fontWeight: 500 }}>{a.message}</div><div style={{ fontSize: 12, color: "var(--muted)", marginTop: 2 }}>{a.camera} · {a.time}</div></div>
          </div>
        ))}
      </div>
      <div style={{ background: "var(--card)", borderRadius: 16, border: "1px solid var(--border)", padding: 24, animation: "fadeUp 0.5s ease 0.25s both" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, color: "var(--text)", margin: 0 }}>Classes YOLO</h2>
          <span style={{ fontSize: 12, color: "var(--accent)", cursor: "pointer", fontWeight: 500 }}>Gerenciar</span>
        </div>
        {CLASSES.map((c, i) => (
          <div key={c.id} style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10, animation: `fadeUp 0.4s ease ${0.3+i*0.04}s both` }}>
            <span style={{ fontSize: 18, width: 28, textAlign: "center" }}>{c.icon}</span>
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <span style={{ fontSize: 13, fontWeight: 500, color: "var(--text)" }}>{c.name}</span>
                <span style={{ fontSize: 12, color: "var(--muted)", fontFamily: "var(--mono)" }}>{c.count.toLocaleString()}</span>
              </div>
              <div style={{ height: 4, borderRadius: 2, background: "var(--bg)" }}><div style={{ height: "100%", borderRadius: 2, background: c.color, width: `${(c.count/1300)*100}%` }} /></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  </div>
);

// ── Cameras ──
const CamerasPage = ({ cameras, loading, onCreateCamera, onEditCamera, onDeleteCamera }) => {
  const [s, setS] = useState("");
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const f = cameras.filter(c => c.name.toLowerCase().includes(s.toLowerCase()) || (c.location && c.location.toLowerCase().includes(s.toLowerCase())));

  const handleDeleteClick = (camera) => {
    setDeleteConfirm(camera);
  };

  const confirmDelete = async () => {
    if (deleteConfirm) {
      await onDeleteCamera(deleteConfirm.id);
      setDeleteConfirm(null);
    }
  };

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "400px", flexDirection: "column", gap: 16 }}>
        <div style={{ width: 40, height: 40, border: "3px solid var(--border)", borderTopColor: "var(--accent)", borderRadius: "50%", animation: "spin 1s linear infinite" }} />
        <div style={{ fontSize: 14, color: "var(--muted)" }}>Carregando câmeras...</div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 28, flexWrap: "wrap", gap: 16 }}>
        <div><h1 style={{ fontSize: 28, fontWeight: 700, color: "var(--text)", margin: 0 }}>Câmeras</h1><p style={{ color: "var(--muted)", margin: "4px 0 0", fontSize: 14 }}>Gerencie suas câmeras IP</p></div>
        <button onClick={() => onCreateCamera()} style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 20px", borderRadius: 10, background: "var(--accent)", color: "#fff", border: "none", fontSize: 14, fontWeight: 600, cursor: "pointer" }}>{Icons.plus} Nova Câmera</button>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12, marginBottom: 24 }}>
        {[{ l: "Total", v: cameras.length, c: "var(--accent)" }, { l: "Online", v: cameras.filter(c=>c.status==="online").length, c: "#22c55e" }, { l: "Offline", v: cameras.filter(c=>c.status==="offline").length, c: "#ef4444" }].map((s,i) => (
          <div key={i} style={{ background: "var(--card)", borderRadius: 12, padding: "16px 20px", border: "1px solid var(--border)" }}><div style={{ fontSize: 12, color: "var(--muted)", fontWeight: 500, marginBottom: 4 }}>{s.l}</div><div style={{ fontSize: 24, fontWeight: 700, color: s.c }}>{s.v}</div></div>
        ))}
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 10, background: "var(--card)", border: "1px solid var(--border)", borderRadius: 10, padding: "10px 16px", marginBottom: 20 }}>
        <span style={{ color: "var(--muted)" }}>{Icons.search}</span>
        <input type="text" placeholder="Buscar câmera..." value={s} onChange={e=>setS(e.target.value)} style={{ background: "none", border: "none", outline: "none", color: "var(--text)", fontSize: 14, width: "100%", fontFamily: "inherit" }} />
      </div>
      {f.length === 0 ? (
        <div style={{ textAlign: "center", padding: "60px 20px", background: "var(--card)", borderRadius: 14, border: "1px dashed var(--border)" }}>
          <div style={{ fontSize: 48, marginBottom: 16, opacity: 0.3 }}>{Icons.camera}</div>
          <div style={{ fontSize: 16, fontWeight: 600, color: "var(--text)", marginBottom: 8 }}>Nenhuma câmera encontrada</div>
          <div style={{ fontSize: 14, color: "var(--muted)", marginBottom: 20 }}>Adicione sua primeira câmera para começar</div>
          <button onClick={() => onCreateCamera()} style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "10px 20px", borderRadius: 10, background: "var(--accent)", color: "#fff", border: "none", fontSize: 14, fontWeight: 600, cursor: "pointer" }}>{Icons.plus} Adicionar Câmera</button>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 16 }}>
          {f.map((cam,i) => (
            <div key={cam.id} style={{ background: "var(--card)", borderRadius: 14, border: "1px solid var(--border)", overflow: "hidden", animation: `fadeUp 0.4s ease ${0.05+i*0.04}s both`, transition: "transform 0.2s" }}
              onMouseEnter={e=>e.currentTarget.style.transform="translateY(-2px)"} onMouseLeave={e=>e.currentTarget.style.transform=""}>
              <div style={{ height: 130, background: cam.status==="online"?"linear-gradient(135deg,#1a1a2e,#16213e,#0f3460)":"linear-gradient(135deg,#1a1a1a,#2d2d2d)", display: "flex", alignItems: "center", justifyContent: "center", position: "relative" }}>
                <div style={{ position: "absolute", inset: 0, background: "repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(255,255,255,0.012) 2px,rgba(255,255,255,0.012) 4px)" }} />
                <div style={{ color: "rgba(255,255,255,0.2)", fontSize: 11, fontFamily: "var(--mono)" }}>{cam.status==="online"?"STREAM ATIVO":"SEM SINAL"}</div>
                {cam.status==="online" && <div style={{ position: "absolute", top: 8, left: 8, display: "flex", alignItems: "center", gap: 4, background: "rgba(239,68,68,0.85)", padding: "2px 7px", borderRadius: 4, fontSize: 10, fontWeight: 700, color: "#fff", fontFamily: "var(--mono)" }}><span style={{ width: 5, height: 5, borderRadius: "50%", background: "#fff", animation: "pulse 1.5s infinite" }} />REC</div>}
              </div>
              <div style={{ padding: "14px 18px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                  <div style={{ fontSize: 15, fontWeight: 600, color: "var(--text)" }}>{cam.name}</div>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 4, padding: "2px 8px", borderRadius: 20, fontSize: 10, fontWeight: 600, background: cam.status==="online"?"#22c55e18":"#ef444418", color: cam.status==="online"?"#22c55e":"#ef4444" }}>
                    <span style={{ width: 5, height: 5, borderRadius: "50%", background: cam.status==="online"?"#22c55e":"#ef4444" }} />{cam.status==="online"?"Online":"Offline"}
                  </span>
                </div>
                <div style={{ fontSize: 12, color: "var(--muted)" }}>{cam.location || "Sem localização"} · {cam.manufacturer || "Genérico"}</div>
                <div style={{ fontSize: 11, color: "var(--muted)", fontFamily: "var(--mono)", marginTop: 4 }}>IP: {cam.ip}</div>
                <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                  <button onClick={() => onEditCamera(cam)} style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 6, padding: "8px 12px", borderRadius: 8, background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)", fontSize: 12, fontWeight: 500, cursor: "pointer", transition: "all 0.15s" }} onMouseEnter={e => e.currentTarget.style.borderColor = "var(--accent)"} onMouseLeave={e => e.currentTarget.style.borderColor = "var(--border)"}>{Icons.edit} Editar</button>
                  <button onClick={() => handleDeleteClick(cam)} style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 6, padding: "8px 12px", borderRadius: 8, background: "var(--bg)", border: "1px solid var(--border)", color: "var(--muted)", fontSize: 12, fontWeight: 500, cursor: "pointer", transition: "all 0.15s" }} onMouseEnter={e => { e.currentTarget.style.borderColor = "#ef4444"; e.currentTarget.style.color = "#ef4444"; }} onMouseLeave={e => { e.currentTarget.style.borderColor = "var(--border)"; e.currentTarget.style.color = "var(--muted)"; }}>{Icons.trash} Excluir</button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <Modal isOpen={!!deleteConfirm} onClose={() => setDeleteConfirm(null)} title="Confirmar Exclusão" size="sm">
        <div>
          <p style={{ fontSize: 14, color: "var(--text)", marginBottom: 20 }}>
            Tem certeza que deseja excluir a câmera <strong>{deleteConfirm?.name}</strong>? Esta ação não pode ser desfeita.
          </p>
          <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
            <button onClick={() => setDeleteConfirm(null)} style={{ padding: "10px 20px", borderRadius: 8, background: "var(--bg)", color: "var(--text)", border: "1px solid var(--border)", fontSize: 14, fontWeight: 500, cursor: "pointer" }}>Cancelar</button>
            <button onClick={confirmDelete} style={{ padding: "10px 20px", borderRadius: 8, background: "#ef4444", color: "#fff", border: "none", fontSize: 14, fontWeight: 600, cursor: "pointer" }}>Excluir Câmera</button>
          </div>
        </div>
      </Modal>
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
  const [progress, setProgress] = useState(0);
  const [running, setRunning] = useState(false);
  useEffect(() => { if (running && progress < 100) { const t = setTimeout(() => setProgress(p => Math.min(p + Math.random()*3+0.5, 100)), 200); return () => clearTimeout(t); } if (progress >= 100) setRunning(false); }, [running, progress]);
  return (
    <div>
      <div style={{ marginBottom: 28 }}><h1 style={{ fontSize: 28, fontWeight: 700, color: "var(--text)", margin: 0 }}>Treinamento</h1><p style={{ color: "var(--muted)", margin: "4px 0 0", fontSize: 14 }}>Acompanhe o modelo YOLO</p></div>
      <div style={{ background: "var(--card)", borderRadius: 16, border: "1px solid var(--border)", padding: 28, marginBottom: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20, flexWrap: "wrap", gap: 12 }}>
          <div><h2 style={{ fontSize: 18, fontWeight: 600, color: "var(--text)", margin: 0 }}>{running?"Treinando...":progress>=100?"Concluído!":"Pronto"}</h2><p style={{ fontSize: 13, color: "var(--muted)", margin: "4px 0 0" }}>YOLOv8n · 4.860 imgs · 6 classes</p></div>
          <button onClick={() => { if (!running && progress < 100) setRunning(true); else { setProgress(0); setRunning(false); }}} style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 24px", borderRadius: 10, background: running?"#ef444420":"var(--accent)", color: running?"#ef4444":"#fff", border: running?"1px solid #ef444440":"none", fontSize: 14, fontWeight: 600, cursor: "pointer" }}>{running?Icons.x:Icons.play} {running?"Parar":progress>=100?"Reiniciar":"Iniciar"}</button>
        </div>
        <div style={{ background: "var(--bg)", borderRadius: 8, height: 8, overflow: "hidden", marginBottom: 8 }}><div style={{ height: "100%", borderRadius: 8, background: progress>=100?"#22c55e":"var(--accent)", width: `${progress}%`, transition: "width 0.3s" }} /></div>
        <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ fontSize: 12, color: "var(--muted)", fontFamily: "var(--mono)" }}>Epoch {Math.floor(progress/2)}/50</span><span style={{ fontSize: 12, color: "var(--muted)", fontFamily: "var(--mono)" }}>{progress.toFixed(1)}%</span></div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: 14 }}>
        {[{ l: "Precisão", v: "96.8%", t: "+2.1%" }, { l: "Recall", v: "94.2%", t: "+1.8%" }, { l: "mAP@50", v: "0.952", t: "+0.03" }, { l: "Loss", v: "0.041", t: "-0.008" }].map((m,i) => (
          <div key={i} style={{ background: "var(--card)", borderRadius: 14, border: "1px solid var(--border)", padding: 20 }}>
            <div style={{ fontSize: 12, color: "var(--muted)", fontWeight: 500, marginBottom: 6 }}>{m.l}</div>
            <div style={{ fontSize: 26, fontWeight: 700, color: "var(--text)" }}>{m.v}</div>
            <div style={{ fontSize: 12, color: "#22c55e", fontWeight: 500, marginTop: 4 }}>{m.t}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

// ══════════════════════════════════════════════════
// ── MONITORING PAGE — Drag & Drop + Seleção ──
// ══════════════════════════════════════════════════
const MonitoringPage = ({ cameras, streams, startStream, stopStream }) => {
  const [selectedIds, setSelectedIds] = useState([]);
  const [orderedIds, setOrderedIds] = useState([]);
  const [grid, setGrid] = useState("3x3");
  const [panelOpen, setPanelOpen] = useState(false);
  const [time, setTime] = useState(new Date());
  const [fullscreenCam, setFullscreenCam] = useState(null);
  const [searchPanel, setSearchPanel] = useState("");
  const [isMobileView, setIsMobileView] = useState(false);
  const [dragIdx, setDragIdx] = useState(null);
  const [dragOverIdx, setDragOverIdx] = useState(null);

  // Initialize selected cameras with all online cameras
  useEffect(() => {
    const onlineCameras = cameras.filter(c => c.status === "online").map(c => c.id);
    setSelectedIds(onlineCameras.slice(0, 6)); // Start with first 6 online cameras
    setOrderedIds(onlineCameras.slice(0, 6));
  }, [cameras]);

  useEffect(() => { const t = setInterval(() => setTime(new Date()), 1000); return () => clearInterval(t); }, []);
  useEffect(() => { const c = () => setIsMobileView(window.innerWidth < 640); c(); window.addEventListener("resize", c); return () => window.removeEventListener("resize", c); }, []);

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
  const displayCameras = orderedIds.map(id => cameras.find(c => c.id === id)).filter(Boolean);
  const filteredPanel = cameras.filter(c => c.name.toLowerCase().includes(searchPanel.toLowerCase()) || (c.location && c.location.toLowerCase().includes(searchPanel.toLowerCase())));

  const CamCell = ({ cam, index }) => {
    const isOn = cam.status === "online";
    const isOver = dragOverIdx === index;
    return (
      <div draggable onDragStart={() => handleDragStart(index)} onDragOver={(e) => handleDragOver(e, index)} onDrop={() => handleDrop(index)} onDragEnd={handleDragEnd}
        style={{
          borderRadius: 6, overflow: "hidden", background: "#0a0e1a",
          aspectRatio: cols <= 2 ? "16/9" : "16/10", position: "relative",
          border: isOver ? "2px solid #2563eb" : "1px solid rgba(255,255,255,0.05)",
          cursor: "grab", transition: "border-color 0.15s, opacity 0.15s, transform 0.15s",
          opacity: dragIdx === index ? 0.35 : 1,
          transform: isOver ? "scale(1.015)" : "scale(1)",
        }}>
        {/* BG */}
        {isOn ? (
          <div style={{ position: "absolute", inset: 0, background: "linear-gradient(135deg, #080c15 0%, #0f1729 40%, #0c1220 100%)" }}>
            <div style={{ position: "absolute", inset: 0, background: "repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(255,255,255,0.006) 3px, rgba(255,255,255,0.006) 4px)" }} />
            <div style={{ position: "absolute", inset: 0, opacity: 0.03, backgroundImage: "radial-gradient(circle, #fff 0.5px, transparent 0.5px)", backgroundSize: "16px 16px" }} />
          </div>
        ) : (
          <div style={{ position: "absolute", inset: 0, background: "#0e0e0e", display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 4 }}>
            <div style={{ color: "rgba(255,255,255,0.12)" }}>{Icons.wifiOff}</div>
            <span style={{ fontSize: 9, color: "rgba(255,255,255,0.15)", fontFamily: "var(--mono)", letterSpacing: 2 }}>OFFLINE</span>
          </div>
        )}
        {/* Grip */}
        <div style={{ position: "absolute", top: 6, left: 6, zIndex: 5, color: "rgba(255,255,255,0.2)", cursor: "grab", padding: "3px 2px", borderRadius: 3, background: "rgba(0,0,0,0.35)", backdropFilter: "blur(4px)" }}>{Icons.grip}</div>
        {/* REC */}
        {isOn && <div style={{ position: "absolute", top: 6, right: 6, zIndex: 5, display: "flex", alignItems: "center", gap: 4, background: "rgba(220,38,38,0.8)", padding: "1px 6px", borderRadius: 3, fontSize: 9, fontWeight: 700, color: "#fff", fontFamily: "var(--mono)" }}><span style={{ width: 4, height: 4, borderRadius: "50%", background: "#fff", animation: "pulse 1.5s infinite" }} />REC</div>}
        {/* Top name */}
        <div style={{ position: "absolute", top: 0, left: 0, right: 0, zIndex: 3, padding: "24px 12px 6px 28px", background: "linear-gradient(180deg, rgba(0,0,0,0.45) 0%, transparent 100%)" }}>
          <span style={{ fontSize: 11, fontWeight: 600, color: "rgba(255,255,255,0.8)" }}>{cam.name}</span>
        </div>
        {/* Bottom */}
        <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, zIndex: 3, padding: "12px 10px 6px", background: "linear-gradient(0deg, rgba(0,0,0,0.55) 0%, transparent 100%)", display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
          <div style={{ fontSize: 9, color: "rgba(255,255,255,0.35)", fontFamily: "var(--mono)", lineHeight: 1.4 }}>{cam.location || "Sem localização"}<br/>{cam.ip}</div>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ fontSize: 9, color: "rgba(255,255,255,0.3)", fontFamily: "var(--mono)" }}>{cam.resolution || "1080p"}</span>
            <span style={{ fontSize: 9, color: "rgba(255,255,255,0.35)", fontFamily: "var(--mono)" }}>{time.toLocaleTimeString("pt-BR")}</span>
          </div>
        </div>
        {/* Fullscreen btn */}
        <button onClick={(e) => { e.stopPropagation(); setFullscreenCam(fullscreenCam === cam.id ? null : cam.id); }}
          style={{ position: "absolute", bottom: 6, right: 6, zIndex: 5, width: 24, height: 24, borderRadius: 4, background: "rgba(0,0,0,0.4)", backdropFilter: "blur(4px)", border: "none", color: "rgba(255,255,255,0.35)", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", transition: "all 0.15s" }}
          onMouseEnter={e => { e.currentTarget.style.color = "#fff"; e.currentTarget.style.background = "rgba(37,99,235,0.7)"; }}
          onMouseLeave={e => { e.currentTarget.style.color = "rgba(255,255,255,0.35)"; e.currentTarget.style.background = "rgba(0,0,0,0.4)"; }}>
          {fullscreenCam === cam.id ? Icons.minimize : Icons.maximize}
        </button>
      </div>
    );
  };

  return (
    <div style={{ display: "flex", height: "calc(100vh - 60px)", margin: isMobileView ? "-16px" : "-28px", position: "relative" }}>
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
            (() => { const c = cameras.find(x => x.id === fullscreenCam); return c ? <CamCell cam={c} index={0} /> : null; })()
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
                <button onClick={() => { const a = cameras.map(c=>c.id); setSelectedIds(a); setOrderedIds(a); }} style={{ flex: 1, padding: 5, borderRadius: 5, background: "rgba(34,197,94,0.08)", border: "1px solid rgba(34,197,94,0.15)", color: "#22c55e", fontSize: 10, fontWeight: 600, cursor: "pointer" }}>Todas</button>
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
              <span style={{ fontSize: 11, color: "rgba(255,255,255,0.3)" }}>{selectedIds.length}/{cameras.length}</span>
              <span style={{ fontSize: 10, color: "rgba(255,255,255,0.2)", fontFamily: "var(--mono)" }}>{cameras.filter(c=>c.status==="online").length} online</span>
            </div>
          </div>
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
              <button style={{ background: "none", border: "none", color: "rgba(255,255,255,0.2)", cursor: "pointer" }} onMouseEnter={e=>e.currentTarget.style.color="#ef4444"} onMouseLeave={e=>e.currentTarget.style.color="rgba(255,255,255,0.2)"}>{Icons.logout}</button>
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
            {page === "cameras" && <CamerasPage cameras={cameras} loading={loading} onCreateCamera={handleCreateCamera} onEditCamera={handleEditCamera} onDeleteCamera={handleDeleteCamera} />}
            {page === "monitoring" && <MonitoringPage cameras={cameras} streams={streams} startStream={startStream} stopStream={stopStream} />}
            {page === "classes" && <ClassesPage />}
            {page === "training" && <TrainingPage />}
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
