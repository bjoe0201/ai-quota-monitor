// Main app — composes design canvas with both variants

const FlipClock = ({ time }) => {
  return (
    <div style={{ display: "flex", gap: 4, justifyContent: "center", padding: "10px 0" }}>
      {time.split("").map((ch, i) => (
        <div
          key={i}
          style={{
            width: ch === ":" ? 14 : 36,
            height: 56,
            borderRadius: 6,
            background: ch === ":" ? "transparent" : "linear-gradient(180deg,#e8e8f0 0%,#e8e8f0 49%,#d6d6e0 51%,#d6d6e0 100%)",
            display: "grid",
            placeItems: "center",
            color: ch === ":" ? "#a8b0d0" : "#1e1e2e",
            fontFamily: "'JetBrains Mono', ui-monospace, monospace",
            fontWeight: 700,
            fontSize: ch === ":" ? 32 : 36,
            boxShadow: ch === ":" ? "none" : "0 1px 0 rgba(255,255,255,0.6) inset, 0 0 0 1px rgba(0,0,0,0.1) inset",
            position: "relative",
          }}
        >
          {ch}
          {ch !== ":" && (
            <div style={{ position: "absolute", left: 2, right: 2, top: "50%", height: 1, background: "rgba(0,0,0,0.15)" }} />
          )}
        </div>
      ))}
    </div>
  );
};

// ── Variant A widget shell ───────────────────────────────────────────────
function AWidgetShell({ density, setDensity, services, collapsed, onToggle, onReorder }) {
  return (
    <div style={{
      width: 440,
      background: A_TOKENS.bg,
      borderRadius: 16,
      border: `1px solid ${A_TOKENS.border}`,
      overflow: "hidden",
      boxShadow: "0 30px 80px -30px rgba(0,0,0,0.7)",
    }}>
      {/* Title bar */}
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "10px 14px",
        background: "#181826",
        borderBottom: `1px solid ${A_TOKENS.border}`,
      }}>
        <div style={{ display: "flex", gap: 6 }}>
          <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#f38ba8" }} />
          <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#f9e2af" }} />
          <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#a6e3a1" }} />
        </div>
        <span style={{ fontSize: 12, color: A_TOKENS.textMuted, fontWeight: 600, marginLeft: 4 }}>AI 額度監控</span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 6, alignItems: "center" }}>
          <DensityPill density={density} setDensity={setDensity} tokens={A_TOKENS} />
          <button style={iconBtn(A_TOKENS)} title="重新整理">⟳</button>
        </div>
      </div>
      {/* Flip clock */}
      <div style={{ background: "#181826", padding: "0 14px 14px", textAlign: "center" }}>
        <FlipClock time="13:42" />
        <div style={{ fontSize: 11, color: A_TOKENS.textDim, fontFeatureSettings: '"tnum"', marginTop: -4 }}>
          2026 年 5 月 9 日 · 週六
        </div>
      </div>
      {/* Cards */}
      <div style={{ padding: density === "compact" ? 10 : 14, display: "flex", flexDirection: "column", gap: density === "compact" ? 8 : 12 }}>
        {services.map((svc, idx) => (
          <DraggableRow key={svc.id} id={svc.id} idx={idx} onReorder={onReorder}>
            <CollapsibleCard collapsed={collapsed[svc.id]} onToggle={() => onToggle(svc.id)} svc={svc} variant="A">
              <ACard svc={svc} density={density} />
            </CollapsibleCard>
          </DraggableRow>
        ))}
      </div>
    </div>
  );
}

// ── Variant B widget shell ───────────────────────────────────────────────
function BWidgetShell({ density, setDensity, services, collapsed, onToggle, onReorder }) {
  return (
    <div style={{
      width: 440,
      background: B_TOKENS.bg,
      borderRadius: 14,
      border: `1px solid ${B_TOKENS.border}`,
      overflow: "hidden",
      boxShadow: "0 30px 80px -30px rgba(0,0,0,0.85)",
      fontFamily: "'Inter', -apple-system, sans-serif",
    }}>
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "12px 16px",
        borderBottom: `1px solid ${B_TOKENS.border}`,
      }}>
        <div style={{
          width: 22, height: 22, borderRadius: 6,
          background: "linear-gradient(135deg,#60a5fa,#a78bfa)",
          display: "grid", placeItems: "center",
          fontSize: 11, fontWeight: 800, color: "#0a0a0c",
          fontFamily: "'JetBrains Mono', monospace",
        }}>AI</div>
        <span style={{ fontSize: 13, color: B_TOKENS.text, fontWeight: 600 }}>Quota Monitor</span>
        <span style={{ fontSize: 10, color: B_TOKENS.textFaint, marginLeft: 4, padding: "2px 6px", border: `1px solid ${B_TOKENS.border}`, borderRadius: 4 }}>v4.2</span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 6, alignItems: "center" }}>
          <DensityPill density={density} setDensity={setDensity} tokens={B_TOKENS} />
          <button style={iconBtn(B_TOKENS)} title="重新整理">⟳</button>
        </div>
      </div>
      {/* Summary KPI strip */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr 1fr",
        borderBottom: `1px solid ${B_TOKENS.border}`,
      }}>
        <SummaryStat tokens={B_TOKENS} label="總餘額" value="$154.08" tone="ok" />
        <SummaryStat tokens={B_TOKENS} label="本月花費" value="$23.29" tone="text" border />
        <SummaryStat tokens={B_TOKENS} label="即將重置" value="3 天" tone="violet" border />
      </div>
      {/* Clock */}
      <div style={{
        display: "flex",
        alignItems: "baseline",
        justifyContent: "space-between",
        padding: "14px 16px 12px",
        borderBottom: `1px solid ${B_TOKENS.border}`,
      }}>
        <div>
          <div style={{
            fontFamily: "'JetBrains Mono', ui-monospace, monospace",
            fontSize: 36,
            fontWeight: 600,
            color: B_TOKENS.text,
            letterSpacing: -1.5,
            lineHeight: 1,
            fontFeatureSettings: '"tnum"',
          }}>13:42<span style={{ color: B_TOKENS.textFaint, fontSize: 24 }}>:08</span></div>
          <div style={{ fontSize: 11, color: B_TOKENS.textDim, marginTop: 4 }}>2026/05/09 · 週六</div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 10, color: B_TOKENS.textFaint, textTransform: "uppercase", letterSpacing: 1.4, fontWeight: 600 }}>Active</div>
          <div style={{ fontSize: 12, color: B_TOKENS.ok, fontWeight: 600, marginTop: 4, display: "inline-flex", alignItems: "center", gap: 6 }}>
            <BPulse /> 5 / 5 服務已連線
          </div>
        </div>
      </div>
      <div style={{ padding: density === "compact" ? 10 : 14, display: "flex", flexDirection: "column", gap: density === "compact" ? 6 : 10 }}>
        {services.map((svc, idx) => (
          <DraggableRow key={svc.id} id={svc.id} idx={idx} onReorder={onReorder}>
            <CollapsibleCard collapsed={collapsed[svc.id]} onToggle={() => onToggle(svc.id)} svc={svc} variant="B">
              <BCard svc={svc} density={density} />
            </CollapsibleCard>
          </DraggableRow>
        ))}
      </div>
    </div>
  );
}

function SummaryStat({ tokens, label, value, tone, border }) {
  const colorMap = { ok: tokens.ok, violet: tokens.violet, text: tokens.text };
  return (
    <div style={{
      padding: "10px 14px",
      borderLeft: border ? `1px solid ${tokens.border}` : "none",
    }}>
      <div style={{ fontSize: 9, color: tokens.textFaint, textTransform: "uppercase", letterSpacing: 1.5, fontWeight: 700 }}>{label}</div>
      <div style={{
        fontSize: 17,
        color: colorMap[tone] || tokens.text,
        fontWeight: 600,
        fontFamily: "'JetBrains Mono', ui-monospace, monospace",
        fontFeatureSettings: '"tnum"',
        marginTop: 3,
        letterSpacing: -0.5,
      }}>{value}</div>
    </div>
  );
}

function DensityPill({ density, setDensity, tokens }) {
  return (
    <div style={{
      display: "inline-flex",
      background: tokens.cardBg || tokens.bg,
      border: `1px solid ${tokens.border}`,
      borderRadius: 6,
      padding: 2,
      gap: 2,
    }}>
      {["compact", "comfortable"].map((d) => (
        <button
          key={d}
          onClick={() => setDensity(d)}
          style={{
            border: "none",
            background: density === d ? (tokens.borderStrong || tokens.border) : "transparent",
            color: density === d ? tokens.text : tokens.textDim,
            padding: "3px 8px",
            borderRadius: 4,
            fontSize: 10,
            fontWeight: 600,
            cursor: "pointer",
            fontFamily: "inherit",
          }}
        >
          {d === "compact" ? "緊湊" : "舒適"}
        </button>
      ))}
    </div>
  );
}

function iconBtn(tokens) {
  return {
    border: `1px solid ${tokens.border}`,
    background: "transparent",
    color: tokens.textMuted,
    width: 26,
    height: 26,
    borderRadius: 6,
    cursor: "pointer",
    fontSize: 14,
    display: "grid",
    placeItems: "center",
  };
}

// Drag-and-drop wrapper (HTML5 DnD)
function DraggableRow({ id, idx, onReorder, children }) {
  const [drag, setDrag] = React.useState(false);
  const [hoverTop, setHoverTop] = React.useState(false);
  return (
    <div
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData("text/plain", String(idx));
        e.dataTransfer.effectAllowed = "move";
        setDrag(true);
      }}
      onDragEnd={() => { setDrag(false); setHoverTop(false); }}
      onDragOver={(e) => {
        e.preventDefault();
        const rect = e.currentTarget.getBoundingClientRect();
        setHoverTop(e.clientY - rect.top < rect.height / 2);
      }}
      onDragLeave={() => setHoverTop(false)}
      onDrop={(e) => {
        e.preventDefault();
        const fromIdx = Number(e.dataTransfer.getData("text/plain"));
        if (!Number.isNaN(fromIdx) && fromIdx !== idx) onReorder(fromIdx, idx);
        setHoverTop(false);
      }}
      style={{
        opacity: drag ? 0.45 : 1,
        transition: "opacity 150ms",
        position: "relative",
        cursor: "grab",
      }}
    >
      {hoverTop && <div style={{ position: "absolute", left: 0, right: 0, top: -4, height: 2, background: "#60a5fa", borderRadius: 2, zIndex: 10 }} />}
      {children}
    </div>
  );
}

function CollapsibleCard({ collapsed, onToggle, svc, variant, children }) {
  return (
    <div style={{ position: "relative" }}>
      <button
        onClick={onToggle}
        title={collapsed ? "展開" : "摺疊"}
        style={{
          position: "absolute",
          top: variant === "A" ? 14 : 16,
          right: variant === "A" ? 38 : 80,
          background: "transparent",
          border: "none",
          color: variant === "A" ? A_TOKENS.textDim : B_TOKENS.textDim,
          cursor: "pointer",
          fontSize: 11,
          fontFamily: "monospace",
          zIndex: 2,
          padding: 4,
        }}
      >
        {collapsed ? "▸" : "▾"}
      </button>
      {collapsed ? (
        <div style={{
          background: variant === "A" ? A_TOKENS.cardBg : B_TOKENS.cardBg,
          border: `1px solid ${variant === "A" ? A_TOKENS.borderSoft : B_TOKENS.border}`,
          borderRadius: variant === "A" ? 14 : 12,
          padding: "10px 16px",
          display: "flex",
          alignItems: "center",
          gap: 10,
        }}>
          <div style={variant === "A" ? aStyles.glyph(svc.accent) : bStyles.glyph(svc.accent)}>{svc.glyph}</div>
          <span style={{ fontSize: 13, fontWeight: 600, color: variant === "A" ? A_TOKENS.text : B_TOKENS.text }}>{svc.short}</span>
          <span style={{ marginLeft: "auto", fontSize: 12, color: variant === "A" ? A_TOKENS.textMuted : B_TOKENS.textMuted, fontFamily: "'JetBrains Mono', monospace", fontFeatureSettings: '"tnum"' }}>
            {summaryFor(svc)}
          </span>
        </div>
      ) : (
        children
      )}
    </div>
  );
}

function summaryFor(svc) {
  const d = svc.data;
  if (svc.id === "openai" || svc.id === "claude_api" || svc.id === "openrouter") return `$${d.balance_usd.toFixed(2)}`;
  if (svc.id === "claude_web") return `週 ${d.weekly_percent}%`;
  if (svc.id === "copilot") return `${d.included_percent}%`;
  return "";
}

// ── Main App ─────────────────────────────────────────────────────────────
function App() {
  const [densityA, setDensityA] = React.useState("comfortable");
  const [densityB, setDensityB] = React.useState("comfortable");
  const [collapsedA, setCollapsedA] = React.useState({});
  const [collapsedB, setCollapsedB] = React.useState({});
  const [orderA, setOrderA] = React.useState(SERVICES.map((s) => s.id));
  const [orderB, setOrderB] = React.useState(SERVICES.map((s) => s.id));

  const reorderFactory = (setter) => (from, to) => {
    setter((arr) => {
      const next = [...arr];
      const [m] = next.splice(from, 1);
      next.splice(to, 0, m);
      return next;
    });
  };

  const orderedA = orderA.map((id) => SERVICES.find((s) => s.id === id));
  const orderedB = orderB.map((id) => SERVICES.find((s) => s.id === id));

  const toggleA = (id) => setCollapsedA((p) => ({ ...p, [id]: !p[id] }));
  const toggleB = (id) => setCollapsedB((p) => ({ ...p, [id]: !p[id] }));

  return (
    <DesignCanvas>
      <DCSection id="widget" title="桌面小工具 (Widget)" subtitle="常駐桌面 · 預設啟動畫面 · 寬度 440px">
        <DCArtboard id="a-widget" label="A · 保守優化版（Refined Catppuccin）" width={480} height={1380}>
          <div style={{ padding: 20, background: "#0d0d14", height: "100%" }}>
            <AWidgetShell density={densityA} setDensity={setDensityA} services={orderedA} collapsed={collapsedA} onToggle={toggleA} onReorder={reorderFactory(setOrderA)} />
          </div>
        </DCArtboard>
        <DCArtboard id="b-widget" label="B · 大膽版（Linear / Raycast）" width={480} height={1480}>
          <div style={{ padding: 20, background: "#050507", height: "100%" }}>
            <BWidgetShell density={densityB} setDensity={setDensityB} services={orderedB} collapsed={collapsedB} onToggle={toggleB} onReorder={reorderFactory(setOrderB)} />
          </div>
        </DCArtboard>
      </DCSection>

      <DCSection id="mainwindow" title="主視窗 (Main Window)" subtitle="完整檢視 · 監控面板 · 760px">
        <DCArtboard id="a-main" label="A · 保守優化版" width={800} height={900}>
          <MainShellA services={orderedA} density={densityA} setDensity={setDensityA} collapsed={collapsedA} onToggle={toggleA} onReorder={reorderFactory(setOrderA)} />
        </DCArtboard>
        <DCArtboard id="b-main" label="B · 大膽版" width={800} height={900}>
          <MainShellB services={orderedB} density={densityB} setDensity={setDensityB} collapsed={collapsedB} onToggle={toggleB} onReorder={reorderFactory(setOrderB)} />
        </DCArtboard>
      </DCSection>

      <DCSection id="states" title="狀態與細節" subtitle="錯誤、載入、警示等次要狀態的處理">
        <DCArtboard id="a-states" label="A · 狀態一覽" width={480} height={520}>
          <StatesA />
        </DCArtboard>
        <DCArtboard id="b-states" label="B · 狀態一覽" width={480} height={520}>
          <StatesB />
        </DCArtboard>
      </DCSection>
    </DesignCanvas>
  );
}

function MainShellA({ services, density, setDensity, collapsed, onToggle, onReorder }) {
  return (
    <div style={{ background: A_TOKENS.bg, height: "100%", display: "flex", flexDirection: "column" }}>
      <div style={{
        display: "flex", alignItems: "center", gap: 12, padding: "12px 18px",
        background: "#181826", borderBottom: `1px solid ${A_TOKENS.border}`,
      }}>
        <span style={{ fontSize: 14, color: A_TOKENS.text, fontWeight: 700 }}>AI 額度監控</span>
        <span style={{ fontSize: 11, color: A_TOKENS.textDim, padding: "2px 6px", border: `1px solid ${A_TOKENS.borderSoft}`, borderRadius: 4 }}>v4.2.0</span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          <DensityPill density={density} setDensity={setDensity} tokens={A_TOKENS} />
          <button style={{ ...iconBtn(A_TOKENS), width: "auto", padding: "0 12px", fontSize: 12 }}>⟳ 重新整理</button>
          <button style={{ ...iconBtn(A_TOKENS), width: "auto", padding: "0 12px", fontSize: 12 }}>⚙ 設定</button>
        </div>
      </div>
      {/* KPI strip */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", padding: "14px 18px", gap: 12, borderBottom: `1px solid ${A_TOKENS.borderSoft}` }}>
        {[
          { l: "總餘額", v: "$154.08", c: A_TOKENS.ok },
          { l: "本月花費", v: "$23.29", c: A_TOKENS.text },
          { l: "活躍服務", v: "5 / 5", c: A_TOKENS.info },
          { l: "下個重置", v: "3 天", c: A_TOKENS.mauve },
        ].map((k) => (
          <div key={k.l} style={{ background: A_TOKENS.cardBg, border: `1px solid ${A_TOKENS.borderSoft}`, borderRadius: 10, padding: "10px 14px" }}>
            <div style={{ fontSize: 10, color: A_TOKENS.textDim, textTransform: "uppercase", letterSpacing: 1, fontWeight: 600 }}>{k.l}</div>
            <div style={{ fontSize: 22, color: k.c, fontWeight: 600, fontFamily: "'JetBrains Mono', monospace", fontFeatureSettings: '"tnum"', letterSpacing: -0.5, marginTop: 4 }}>{k.v}</div>
          </div>
        ))}
      </div>
      <div style={{ flex: 1, overflow: "auto", padding: 18, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, alignContent: "start" }}>
        {services.map((svc, idx) => (
          <DraggableRow key={svc.id} id={svc.id} idx={idx} onReorder={onReorder}>
            <CollapsibleCard collapsed={collapsed[svc.id]} onToggle={() => onToggle(svc.id)} svc={svc} variant="A">
              <ACard svc={svc} density={density} />
            </CollapsibleCard>
          </DraggableRow>
        ))}
      </div>
    </div>
  );
}

function MainShellB({ services, density, setDensity, collapsed, onToggle, onReorder }) {
  return (
    <div style={{ background: B_TOKENS.bg, height: "100%", display: "flex", flexDirection: "column", fontFamily: "'Inter', sans-serif" }}>
      <div style={{
        display: "flex", alignItems: "center", gap: 12, padding: "14px 20px",
        borderBottom: `1px solid ${B_TOKENS.border}`,
      }}>
        <div style={{ width: 24, height: 24, borderRadius: 6, background: "linear-gradient(135deg,#60a5fa,#a78bfa)", display: "grid", placeItems: "center", color: "#0a0a0c", fontWeight: 800, fontSize: 11, fontFamily: "monospace" }}>AI</div>
        <span style={{ fontSize: 14, color: B_TOKENS.text, fontWeight: 600 }}>Quota Monitor</span>
        <span style={{ fontSize: 10, color: B_TOKENS.textFaint, padding: "2px 6px", border: `1px solid ${B_TOKENS.border}`, borderRadius: 4 }}>v4.2</span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
          <DensityPill density={density} setDensity={setDensity} tokens={B_TOKENS} />
          <button style={{ ...iconBtn(B_TOKENS), width: "auto", padding: "0 12px", fontSize: 11 }}>⟳ 重新整理</button>
          <button style={{ ...iconBtn(B_TOKENS), width: "auto", padding: "0 12px", fontSize: 11 }}>⚙</button>
        </div>
      </div>
      {/* KPI strip */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", borderBottom: `1px solid ${B_TOKENS.border}` }}>
        {[
          { l: "總餘額 (USD)", v: "$154.08", c: B_TOKENS.ok, sub: "+ $20.80 額外" },
          { l: "本月花費", v: "$23.29", c: B_TOKENS.text, sub: "5 個服務" },
          { l: "活躍服務", v: "5 / 5", c: B_TOKENS.info, sub: "全部已連線" },
          { l: "下個重置", v: "3 天", c: B_TOKENS.violet, sub: "Claude 工作階段" },
        ].map((k, i) => (
          <div key={k.l} style={{ padding: "14px 18px", borderLeft: i > 0 ? `1px solid ${B_TOKENS.border}` : "none" }}>
            <div style={{ fontSize: 10, color: B_TOKENS.textFaint, textTransform: "uppercase", letterSpacing: 1.4, fontWeight: 700 }}>{k.l}</div>
            <div style={{ fontSize: 24, color: k.c, fontWeight: 600, fontFamily: "'JetBrains Mono', monospace", fontFeatureSettings: '"tnum"', letterSpacing: -1, marginTop: 4 }}>{k.v}</div>
            <div style={{ fontSize: 11, color: B_TOKENS.textDim, marginTop: 2 }}>{k.sub}</div>
          </div>
        ))}
      </div>
      <div style={{ flex: 1, overflow: "auto", padding: 18, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, alignContent: "start" }}>
        {services.map((svc, idx) => (
          <DraggableRow key={svc.id} id={svc.id} idx={idx} onReorder={onReorder}>
            <CollapsibleCard collapsed={collapsed[svc.id]} onToggle={() => onToggle(svc.id)} svc={svc} variant="B">
              <BCard svc={svc} density={density} />
            </CollapsibleCard>
          </DraggableRow>
        ))}
      </div>
    </div>
  );
}

function StatesA() {
  return (
    <div style={{ padding: 20, background: A_TOKENS.bg, height: "100%", display: "flex", flexDirection: "column", gap: 12 }}>
      {/* Loading */}
      <div style={aStyles.card("#74c7ec")}>
        <div style={aStyles.accentBar("#74c7ec")} />
        <div style={aStyles.header}>
          <div style={{ ...aStyles.glyph("#74c7ec"), animation: "pulse 1.5s ease-in-out infinite" }}>OA</div>
          <div style={aStyles.titleStack}>
            <span style={aStyles.title}>OpenAI · 載入中</span>
            <span style={aStyles.subtitle}>等待瀏覽器資料...</span>
          </div>
          <div style={aStyles.statusDot("warn")} />
        </div>
        <div style={{ padding: "0 16px 14px", display: "flex", flexDirection: "column", gap: 8 }}>
          {[80, 50, 70].map((w, i) => <div key={i} style={{ height: 10, width: `${w}%`, background: A_TOKENS.borderSoft, borderRadius: 4, animation: "shimmer 1.5s ease-in-out infinite" }} />)}
        </div>
      </div>
      {/* Error */}
      <div style={aStyles.card("#f38ba8")}>
        <div style={aStyles.accentBar("#f38ba8")} />
        <div style={aStyles.header}>
          <div style={{ ...aStyles.glyph("#f38ba8"), background: "#f38ba822", color: "#f38ba8" }}>!</div>
          <div style={aStyles.titleStack}>
            <span style={aStyles.title}>Claude API · 連線失敗</span>
            <span style={aStyles.subtitle}>Tampermonkey 腳本未回應</span>
          </div>
          <div style={aStyles.statusDot("danger")} />
        </div>
        <div style={{ padding: "0 16px 14px" }}>
          <div style={{ fontSize: 12, color: A_TOKENS.danger, marginBottom: 10 }}>
            連線逾時：localhost:7890 無回應
          </div>
          <button style={{ ...iconBtn(A_TOKENS), width: "100%", padding: "8px", color: A_TOKENS.text, fontSize: 12, background: A_TOKENS.cardBgAlt }}>重試連線</button>
        </div>
      </div>
      {/* Warning - high usage */}
      <div style={{ ...aStyles.card("#f9e2af") }}>
        <div style={aStyles.accentBar("#f9e2af")} />
        <div style={aStyles.header}>
          <div style={aStyles.glyph("#c6a0f6")}>C</div>
          <div style={aStyles.titleStack}>
            <span style={aStyles.title}>Claude.ai · 即將達到上限</span>
            <span style={aStyles.subtitle}>重置：6 小時 23 分後</span>
          </div>
          <div style={aStyles.statusDot("warn")} />
        </div>
        <div style={{ padding: "0 16px 14px" }}>
          <ABar label="每週限額" percent={91} detail="" tone="danger" reset="週一 09:00" />
        </div>
      </div>
    </div>
  );
}

function StatesB() {
  return (
    <div style={{ padding: 20, background: B_TOKENS.bg, height: "100%", display: "flex", flexDirection: "column", gap: 10 }}>
      {/* Loading */}
      <div style={bStyles.card}>
        <div style={bStyles.header}>
          <div style={{ ...bStyles.glyph("#3a3a45"), color: B_TOKENS.textMuted, animation: "pulse 1.5s ease-in-out infinite" }}>OA</div>
          <span style={bStyles.title}>OpenAI</span>
          <span style={bStyles.timestamp}>載入中…</span>
        </div>
        <div style={{ padding: "12px 16px 16px", display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ height: 28, width: "60%", background: B_TOKENS.border, borderRadius: 4, animation: "shimmer 1.5s ease-in-out infinite" }} />
          <div style={{ height: 8, width: "100%", background: B_TOKENS.border, borderRadius: 2 }} />
          {[70, 80, 50].map((w, i) => <div key={i} style={{ height: 10, width: `${w}%`, background: B_TOKENS.border, borderRadius: 2, opacity: 0.6 }} />)}
        </div>
      </div>
      {/* Error */}
      <div style={{ ...bStyles.card, borderColor: B_TOKENS.danger + "55", background: B_TOKENS.danger + "08" }}>
        <div style={bStyles.header}>
          <div style={{ ...bStyles.glyph(B_TOKENS.danger) }}>!</div>
          <span style={bStyles.title}>Claude API</span>
          <span style={{ ...bStyles.badge, color: B_TOKENS.danger, borderColor: B_TOKENS.danger + "55" }}>離線</span>
          <span style={bStyles.timestamp}>5m 前</span>
        </div>
        <div style={{ padding: "12px 16px 16px" }}>
          <div style={{ fontSize: 12, color: B_TOKENS.danger, fontWeight: 600, marginBottom: 6 }}>
            連線逾時 · localhost:7890
          </div>
          <div style={{ fontSize: 11, color: B_TOKENS.textDim, marginBottom: 12, lineHeight: 1.5 }}>
            Tampermonkey 腳本未回應，請確認瀏覽器頁面已開啟。
          </div>
          <button style={{
            border: `1px solid ${B_TOKENS.danger}55`,
            background: B_TOKENS.danger + "11",
            color: B_TOKENS.danger,
            padding: "6px 12px",
            borderRadius: 5,
            fontSize: 11,
            fontWeight: 600,
            cursor: "pointer",
            fontFamily: "inherit",
          }}>重試連線 →</button>
        </div>
      </div>
      {/* High usage - warning */}
      <div style={{ ...bStyles.card, borderColor: B_TOKENS.warn + "55" }}>
        <div style={bStyles.header}>
          <div style={bStyles.glyph("#c6a0f6")}>C</div>
          <span style={bStyles.title}>Claude.ai</span>
          <span style={{ ...bStyles.badge, color: B_TOKENS.warn, borderColor: B_TOKENS.warn + "55" }}>⚠ 即將達到上限</span>
          <span style={bStyles.timestamp}>now</span>
        </div>
        <div style={bStyles.hero}>
          <div style={bStyles.heroLabel}>每週限額</div>
          <div>
            <span style={{ ...bStyles.heroValue, color: B_TOKENS.danger }}>91</span>
            <span style={bStyles.heroValueSmall}>%</span>
            <span style={bStyles.heroDelta("danger")}>· 6h 23m 後重置</span>
          </div>
        </div>
        <div style={bStyles.body}>
          <BBar label="每週限額" percent={91} detail="近一週使用量" tone="danger" reset="週一 09:00" />
        </div>
      </div>
    </div>
  );
}

// Expose shells; only auto-render the canvas if no override flag set.
Object.assign(window, { App, MainShellA, MainShellB, AWidgetShell, BWidgetShell, StatesA, StatesB, DraggableRow, CollapsibleCard, DensityPill, iconBtn, BPulse, summaryFor, FlipClock, SummaryStat });
if (!window.__SKIP_CANVAS_RENDER__) {
  const root = ReactDOM.createRoot(document.getElementById("root"));
  root.render(<App />);
}
