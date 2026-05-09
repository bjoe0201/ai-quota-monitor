// Variant B — 大膽版 (Linear / Raycast inspired)
// Near-black bg, big metric typography, segmented progress bars,
// tighter type, prominent reset countdown rings.

const B_TOKENS = {
  bg: "#0a0a0c",
  cardBg: "#111114",
  cardBgHover: "#16161a",
  border: "#1f1f24",
  borderStrong: "#2a2a32",
  text: "#fafafa",
  textMuted: "#a1a1aa",
  textDim: "#71717a",
  textFaint: "#52525b",
  ok: "#34d399",
  warn: "#fbbf24",
  danger: "#f87171",
  info: "#60a5fa",
  violet: "#a78bfa",
};

const bStyles = {
  card: {
    background: B_TOKENS.cardBg,
    border: `1px solid ${B_TOKENS.border}`,
    borderRadius: 12,
    overflow: "hidden",
    fontFamily: "'Inter', -apple-system, sans-serif",
    color: B_TOKENS.text,
    transition: "all 200ms ease",
  },
  header: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "14px 16px 0",
  },
  glyph: (accent) => ({
    width: 22,
    height: 22,
    borderRadius: 6,
    display: "grid",
    placeItems: "center",
    background: accent,
    color: "#0a0a0c",
    fontSize: 10,
    fontWeight: 800,
    letterSpacing: 0,
    fontFamily: "'JetBrains Mono', ui-monospace, monospace",
  }),
  title: { fontSize: 13, fontWeight: 600, color: B_TOKENS.text, letterSpacing: -0.1 },
  badge: {
    fontSize: 10,
    color: B_TOKENS.textMuted,
    padding: "2px 7px",
    border: `1px solid ${B_TOKENS.border}`,
    borderRadius: 5,
    fontWeight: 500,
    letterSpacing: 0.2,
  },
  timestamp: {
    marginLeft: "auto",
    fontSize: 11,
    color: B_TOKENS.textFaint,
    fontFeatureSettings: '"tnum"',
    fontFamily: "'JetBrains Mono', ui-monospace, monospace",
  },
  // Hero metric block
  hero: { padding: "10px 16px 16px" },
  heroLabel: {
    fontSize: 10,
    color: B_TOKENS.textDim,
    textTransform: "uppercase",
    letterSpacing: 1.4,
    fontWeight: 600,
    marginBottom: 4,
  },
  heroValue: {
    fontSize: 36,
    fontWeight: 600,
    fontFamily: "'JetBrains Mono', ui-monospace, monospace",
    fontFeatureSettings: '"tnum"',
    letterSpacing: -1.2,
    lineHeight: 1,
    color: B_TOKENS.text,
  },
  heroValueSmall: {
    fontSize: 18,
    color: B_TOKENS.textMuted,
    fontWeight: 500,
    fontFamily: "'JetBrains Mono', ui-monospace, monospace",
    fontFeatureSettings: '"tnum"',
    letterSpacing: -0.5,
  },
  heroDelta: (tone) => ({
    fontSize: 12,
    color: { ok: B_TOKENS.ok, warn: B_TOKENS.warn, danger: B_TOKENS.danger }[tone] || B_TOKENS.textMuted,
    fontWeight: 500,
    marginLeft: 8,
  }),
  body: { padding: "0 16px 14px", display: "flex", flexDirection: "column", gap: 12 },
  // Segmented progress
  segBlock: { display: "flex", flexDirection: "column", gap: 7 },
  segTopRow: { display: "flex", justifyContent: "space-between", alignItems: "center" },
  segLabel: { fontSize: 11, color: B_TOKENS.textMuted, fontWeight: 500, letterSpacing: 0.1 },
  segPct: (tone) => ({
    fontSize: 11,
    fontWeight: 600,
    color: { ok: B_TOKENS.text, warn: B_TOKENS.warn, danger: B_TOKENS.danger }[tone] || B_TOKENS.text,
    fontFeatureSettings: '"tnum"',
    fontFamily: "'JetBrains Mono', ui-monospace, monospace",
  }),
  // Stat row (tabular)
  kvRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "6px 0",
    borderBottom: `1px solid ${B_TOKENS.border}`,
  },
  kvRowLast: {
    borderBottom: "none",
  },
  kvLabel: {
    fontSize: 11,
    color: B_TOKENS.textDim,
    fontWeight: 500,
  },
  kvValue: (color) => ({
    fontSize: 12,
    color: color || B_TOKENS.text,
    fontWeight: 600,
    fontFeatureSettings: '"tnum"',
    fontFamily: "'JetBrains Mono', ui-monospace, monospace",
  }),
  // Reset pill (prominent)
  resetPill: (urgent) => ({
    display: "inline-flex",
    alignItems: "center",
    gap: 5,
    padding: "3px 8px",
    borderRadius: 5,
    background: urgent ? `${B_TOKENS.warn}1a` : `${B_TOKENS.violet}14`,
    color: urgent ? B_TOKENS.warn : B_TOKENS.violet,
    fontSize: 10,
    fontWeight: 600,
    letterSpacing: 0.2,
    fontFeatureSettings: '"tnum"',
    border: `1px solid ${urgent ? B_TOKENS.warn + "33" : B_TOKENS.violet + "22"}`,
  }),
  sectionDivider: {
    fontSize: 9,
    color: B_TOKENS.textFaint,
    textTransform: "uppercase",
    letterSpacing: 1.5,
    fontWeight: 700,
    paddingTop: 4,
    borderTop: `1px solid ${B_TOKENS.border}`,
  },
};

// Segmented progress bar — 24 cells, like Linear
function BSegmentedBar({ percent, tone }) {
  const color = { ok: B_TOKENS.info, warn: B_TOKENS.warn, danger: B_TOKENS.danger }[tone];
  const cells = 28;
  const filled = Math.round((percent / 100) * cells);
  return (
    <div style={{ display: "flex", gap: 2, height: 8 }}>
      {Array.from({ length: cells }).map((_, i) => (
        <div
          key={i}
          style={{
            flex: 1,
            background: i < filled ? color : B_TOKENS.border,
            borderRadius: 1.5,
            opacity: i < filled ? 1 : 0.7,
            transition: "background 200ms",
          }}
        />
      ))}
    </div>
  );
}

function BBar({ label, percent, detail, tone, reset }) {
  return (
    <div style={bStyles.segBlock}>
      <div style={bStyles.segTopRow}>
        <span style={bStyles.segLabel}>{label}</span>
        <span style={bStyles.segPct(tone)}>{percent.toFixed(1)}%</span>
      </div>
      <BSegmentedBar percent={percent} tone={tone} />
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 2 }}>
        <span style={{ fontSize: 10, color: B_TOKENS.textFaint, fontFeatureSettings: '"tnum"', fontFamily: "'JetBrains Mono', ui-monospace, monospace" }}>
          {detail}
        </span>
        {reset && <span style={bStyles.resetPill(false)}>↻ {reset}</span>}
      </div>
    </div>
  );
}

function BKv({ label, value, color, last }) {
  return (
    <div style={{ ...bStyles.kvRow, ...(last ? bStyles.kvRowLast : {}) }}>
      <span style={bStyles.kvLabel}>{label}</span>
      <span style={bStyles.kvValue(color)}>{value}</span>
    </div>
  );
}

// Countdown ring for "資料已更新 X 秒前" with urgency
function BPulse({ tone = "ok" }) {
  const c = { ok: B_TOKENS.ok, warn: B_TOKENS.warn, danger: B_TOKENS.danger }[tone];
  return (
    <span style={{ position: "relative", width: 6, height: 6, display: "inline-block" }}>
      <span style={{ position: "absolute", inset: 0, borderRadius: "50%", background: c, animation: "bPulse 2s ease-in-out infinite" }} />
      <span style={{ position: "absolute", inset: 0, borderRadius: "50%", background: c }} />
    </span>
  );
}

function BCard({ svc, density = "comfortable" }) {
  const { name, short, accent, glyph, updated, data, id } = svc;
  return (
    <div style={bStyles.card}>
      <div style={bStyles.header}>
        <div style={bStyles.glyph(accent)}>{glyph}</div>
        <span style={bStyles.title}>{short}</span>
        <span style={bStyles.timestamp}>
          <BPulse /> &nbsp;{updated}
        </span>
      </div>
      {id === "openai" && <BOpenAI data={data} />}
      {id === "claude_web" && <BClaudeWeb data={data} />}
      {id === "claude_api" && <BClaudeApi data={data} />}
      {id === "copilot" && <BCopilot data={data} />}
      {id === "openrouter" && <BOpenRouter data={data} />}
    </div>
  );
}

function BOpenAI({ data }) {
  const creditsPct = (data.credits_used_usd / data.credits_total_usd) * 100;
  return (
    <>
      <div style={bStyles.hero}>
        <div style={bStyles.heroLabel}>帳戶餘額</div>
        <div>
          <span style={bStyles.heroValue}>${data.balance_usd.toFixed(2)}</span>
        </div>
      </div>
      <div style={bStyles.body}>
        <BBar label="Credits 用量" percent={creditsPct} detail={`$${data.credits_used_usd.toFixed(2)} / $${data.credits_total_usd.toFixed(2)}`} tone={pctTone(creditsPct)} />
        <div>
          <BKv label="本月用量" value={`$${data.month_usage_usd.toFixed(4)}`} />
          <BKv label="月上限" value={`$${data.hard_limit_usd.toFixed(0)}`} />
          <BKv label="用量等級" value={data.tier} />
          <BKv label="自動儲值" value={data.auto_recharge ? "已啟用" : "停用"} color={data.auto_recharge ? B_TOKENS.ok : B_TOKENS.textDim} last />
        </div>
      </div>
    </>
  );
}

function BClaudeWeb({ data }) {
  const wTone = pctTone(data.weekly_percent);
  const sTone = pctTone(data.session_percent);
  const extraPct = (data.extra_spent / data.extra_limit) * 100;
  const wColor = { ok: B_TOKENS.text, warn: B_TOKENS.warn, danger: B_TOKENS.danger }[wTone];
  return (
    <>
      <div style={bStyles.hero}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={bStyles.heroLabel}>每週限額剩餘</div>
          <span style={bStyles.badge}>{data.plan_type}</span>
        </div>
        <div>
          <span style={{ ...bStyles.heroValue, color: wColor }}>{(100 - data.weekly_percent).toFixed(0)}</span>
          <span style={bStyles.heroValueSmall}>%</span>
          <span style={bStyles.heroDelta(wTone)}>· 已用 {data.weekly_percent}%</span>
        </div>
      </div>
      <div style={bStyles.body}>
        <BBar label="本次工作階段" percent={data.session_percent} detail="" tone={sTone} reset={data.session_reset} />
        <BBar label="每週限額" percent={data.weekly_percent} detail="" tone={wTone} reset={data.weekly_reset} />
        {data.extra_enabled && (
          <>
            <div style={bStyles.sectionDivider}>額外用量</div>
            <BBar label="本月已花費" percent={extraPct} detail={`$${data.extra_spent.toFixed(2)} / $${data.extra_limit.toFixed(0)}`} tone={pctTone(extraPct)} reset={data.extra_resets} />
            <div>
              <BKv label="目前餘額" value={`$${data.extra_balance.toFixed(2)}`} color={B_TOKENS.ok} />
              <BKv label="自動儲值" value={data.auto_reload ? "已啟用" : "停用"} color={data.auto_reload ? B_TOKENS.ok : B_TOKENS.textDim} last />
            </div>
          </>
        )}
      </div>
    </>
  );
}

function BClaudeApi({ data }) {
  return (
    <>
      <div style={bStyles.hero}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={bStyles.heroLabel}>帳戶餘額</div>
          <span style={bStyles.badge}>{data.plan}</span>
        </div>
        <div>
          <span style={bStyles.heroValue}>${data.balance_usd.toFixed(2)}</span>
        </div>
      </div>
      <div style={bStyles.body}>
        <div>
          <BKv label="本月用量" value={`$${data.this_month_usd.toFixed(4)}`} />
          <BKv label="下次計費" value={data.next_billing} color={B_TOKENS.violet} />
          <BKv label="月費" value={`$${data.monthly_usd.toFixed(2)}`} />
          <BKv label="消費上限" value={`$${data.spend_limit_usd.toFixed(0)}`} last />
        </div>
      </div>
    </>
  );
}

function BCopilot({ data }) {
  const tone = pctTone(data.included_percent);
  const remaining = data.included_total - data.included_consumed;
  return (
    <>
      <div style={bStyles.hero}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={bStyles.heroLabel}>Premium Requests 剩餘</div>
          <span style={bStyles.badge}>{data.plan}</span>
        </div>
        <div>
          <span style={bStyles.heroValue}>{remaining.toLocaleString()}</span>
          <span style={bStyles.heroValueSmall}>/{data.included_total.toLocaleString()}</span>
          <span style={bStyles.heroDelta(tone)}>· 已用 {data.included_percent}%</span>
        </div>
      </div>
      <div style={bStyles.body}>
        <BBar label="使用率" percent={data.included_percent} detail={`${data.included_consumed} / ${data.included_total} 次`} tone={tone} />
        <div>
          <BKv label="已計費" value={`$${data.billed_usd.toFixed(2)}`} color={data.billed_usd > 0 ? B_TOKENS.warn : B_TOKENS.text} />
          <BKv label="重置倒數" value={`${data.resets_in_days} 天`} color={B_TOKENS.violet} />
          <BKv label="下次計費" value={data.next_billing} last />
        </div>
      </div>
    </>
  );
}

function BOpenRouter({ data }) {
  return (
    <>
      <div style={bStyles.hero}>
        <div style={bStyles.heroLabel}>帳戶餘額</div>
        <div>
          <span style={bStyles.heroValue}>${data.balance_usd.toFixed(2)}</span>
        </div>
      </div>
      <div style={bStyles.body}>
        <div>
          <BKv label="本月花費" value={`$${data.month_spend_usd.toFixed(4)}`} />
          <BKv label="請求數" value={data.month_requests.toLocaleString()} />
          <BKv label="Tokens" value={fmtTokens(data.month_tokens)} />
          <BKv label="主要模型" value={(data.top_model.split("/")[1] || data.top_model)} color={B_TOKENS.textMuted} last />
        </div>
      </div>
    </>
  );
}

Object.assign(window, { BCard, B_TOKENS });
