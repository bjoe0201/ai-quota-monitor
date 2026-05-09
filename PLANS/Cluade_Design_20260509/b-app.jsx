// B-only preview — Variant B widget + main window + states, full screen

function App() {
  const [density, setDensity] = React.useState("comfortable");
  const [collapsed, setCollapsed] = React.useState({});
  const [order, setOrder] = React.useState(SERVICES.map((s) => s.id));
  const [view, setView] = React.useState("widget"); // widget | main | states

  const reorder = (from, to) => {
    setOrder((arr) => {
      const next = [...arr];
      const [m] = next.splice(from, 1);
      next.splice(to, 0, m);
      return next;
    });
  };
  const ordered = order.map((id) => SERVICES.find((s) => s.id === id));
  const toggle = (id) => setCollapsed((p) => ({ ...p, [id]: !p[id] }));

  return (
    <div style={{
      minHeight: "100vh",
      background: "#050507",
      display: "flex",
      flexDirection: "column",
      fontFamily: "'Inter', sans-serif",
    }}>
      {/* Top bar */}
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 16,
        padding: "16px 24px",
        borderBottom: `1px solid ${B_TOKENS.border}`,
        background: "#0a0a0c",
      }}>
        <div style={{
          width: 28, height: 28, borderRadius: 7,
          background: "linear-gradient(135deg,#60a5fa,#a78bfa)",
          display: "grid", placeItems: "center",
          color: "#0a0a0c", fontWeight: 800, fontSize: 12,
          fontFamily: "'JetBrains Mono', monospace",
        }}>AI</div>
        <div>
          <div style={{ fontSize: 14, color: B_TOKENS.text, fontWeight: 600 }}>Variant B · Linear / Raycast</div>
          <div style={{ fontSize: 11, color: B_TOKENS.textDim, marginTop: 2 }}>AI 額度監控 · UI 優化最終版</div>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 4, padding: 3, background: B_TOKENS.cardBg, border: `1px solid ${B_TOKENS.border}`, borderRadius: 8 }}>
          {[
            ["widget", "桌面小工具"],
            ["main", "主視窗"],
            ["states", "狀態"],
          ].map(([k, label]) => (
            <button key={k} onClick={() => setView(k)} style={{
              border: "none",
              background: view === k ? B_TOKENS.borderStrong : "transparent",
              color: view === k ? B_TOKENS.text : B_TOKENS.textDim,
              padding: "6px 14px",
              borderRadius: 5,
              fontSize: 12,
              fontWeight: 600,
              cursor: "pointer",
              fontFamily: "inherit",
            }}>{label}</button>
          ))}
        </div>
      </div>

      {/* Stage */}
      <div style={{
        flex: 1,
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "center",
        padding: 32,
        overflow: "auto",
      }} className="mock-scroll">
        {view === "widget" && (
          <div>
            <div style={{ fontSize: 11, color: B_TOKENS.textDim, textTransform: "uppercase", letterSpacing: 1.5, fontWeight: 700, marginBottom: 12 }}>桌面小工具 · 440 px</div>
            <BWidgetShell density={density} setDensity={setDensity} services={ordered} collapsed={collapsed} onToggle={toggle} onReorder={reorder} />
          </div>
        )}
        {view === "main" && (
          <div style={{ width: "100%", maxWidth: 980, height: "calc(100vh - 160px)", border: `1px solid ${B_TOKENS.border}`, borderRadius: 12, overflow: "hidden", boxShadow: "0 30px 80px -30px rgba(0,0,0,0.85)" }}>
            <MainShellB services={ordered} density={density} setDensity={setDensity} collapsed={collapsed} onToggle={toggle} onReorder={reorder} />
          </div>
        )}
        {view === "states" && (
          <div style={{ width: 480 }}>
            <div style={{ fontSize: 11, color: B_TOKENS.textDim, textTransform: "uppercase", letterSpacing: 1.5, fontWeight: 700, marginBottom: 12 }}>狀態一覽 · 載入 / 錯誤 / 警示</div>
            <StatesB />
          </div>
        )}
      </div>

      {/* Footnote */}
      <div style={{
        padding: "12px 24px",
        borderTop: `1px solid ${B_TOKENS.border}`,
        fontSize: 11,
        color: B_TOKENS.textDim,
        background: "#0a0a0c",
      }}>
        對應實作規格：<code style={{ background: B_TOKENS.cardBg, padding: "2px 6px", borderRadius: 3, color: B_TOKENS.text }}>HANDOFF-Variant-B.md</code>
        &nbsp;· 提供給 AI agent 修改 <code style={{ background: B_TOKENS.cardBg, padding: "2px 6px", borderRadius: 3, color: B_TOKENS.text }}>bjoe0201/ai-quota-monitor</code> Python tkinter 程式碼
      </div>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
