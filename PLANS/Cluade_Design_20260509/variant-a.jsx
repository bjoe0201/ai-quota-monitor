// Variant A — 保守優化 (Refined Catppuccin)
// Sticks to the original palette but: brighter text, hero metric typography,
// tabular numerals, clearer reset chips, generous card spacing.

const A_TOKENS = {
  bg: "#11111a",
  cardBg: "#1e1e2e",
  cardBgAlt: "#1a1a26",
  border: "#363a4f",
  borderSoft: "#2a2d3f",
  text: "#e6e9f5",
  textMuted: "#a8b0d0",
  textDim: "#7d83a0",
  ok: "#a6e3a1",
  warn: "#f9e2af",
  danger: "#f38ba8",
  info: "#89b4fa",
  peach: "#f5a97f",
  mauve: "#c6a0f6",
};

const aStyles = {
  card: (accent) => ({
    background: A_TOKENS.cardBg,
    border: `1px solid ${A_TOKENS.borderSoft}`,
    borderRadius: 14,
    overflow: "hidden",
    fontFamily: "'Inter', 'Segoe UI', -apple-system, sans-serif",
    color: A_TOKENS.text,
    boxShadow: `0 1px 0 rgba(255,255,255,0.04) inset, 0 8px 24px -16px rgba(0,0,0,0.6)`,
    position: "relative",
  }),
  accentBar: (accent) => ({
    height: 3,
    background: `linear-gradient(90deg, ${accent}, ${accent}55)`,
  }),
  header: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "12px 16px 10px",
  },
  glyph: (accent) => ({
    width: 26,
    height: 26,
    borderRadius: 7,
    display: "grid",
    placeItems: "center",
    background: `${accent}22`,
    color: accent,
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: 0.3,
    fontFeatureSettings: '"ss01"',
    fontFamily: "'JetBrains Mono', ui-monospace, monospace",
  }),
  titleStack: { display: "flex", flexDirection: "column", gap: 2, flex: 1, minWidth: 0 },
  title: { fontSize: 13, fontWeight: 600, color: A_TOKENS.text, letterSpacing: 0.1 },
  subtitle: { fontSize: 11, color: A_TOKENS.textDim, fontFeatureSettings: '"tnum"' },
  statusDot: (tone) => ({
    width: 7,
    height: 7,
    borderRadius: "50%",
    background: { ok: A_TOKENS.ok, warn: A_TOKENS.warn, danger: A_TOKENS.danger }[tone] || A_TOKENS.textDim,
    boxShadow: `0 0 0 3px ${({ ok: A_TOKENS.ok, warn: A_TOKENS.warn, danger: A_TOKENS.danger }[tone] || A_TOKENS.textDim)}22`,
  }),
  // Hero (primary metric)
  hero: { padding: "4px 16px 14px", display: "flex", alignItems: "baseline", gap: 8 },
  heroLabel: { fontSize: 11, color: A_TOKENS.textMuted, textTransform: "uppercase", letterSpacing: 1 },
  heroValue: {
    fontSize: 28,
    fontWeight: 600,
    fontFamily: "'JetBrains Mono', ui-monospace, monospace",
    fontFeatureSettings: '"tnum"',
    letterSpacing: -0.5,
    lineHeight: 1,
  },
  heroSuffix: { fontSize: 13, color: A_TOKENS.textMuted, fontFeatureSettings: '"tnum"' },
  // Body
  body: { padding: "0 16px 14px", display: "flex", flexDirection: "column", gap: 10 },
  // Stat row
  rowGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 8,
  },
  stat: {
    background: A_TOKENS.cardBgAlt,
    borderRadius: 8,
    padding: "8px 10px",
    border: `1px solid ${A_TOKENS.borderSoft}`,
  },
  statLabel: { fontSize: 10, color: A_TOKENS.textDim, letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 3 },
  statValue: { fontSize: 13, color: A_TOKENS.text, fontWeight: 600, fontFeatureSettings: '"tnum"', fontFamily: "'JetBrains Mono', ui-monospace, monospace" },
  // Bar
  barBlock: { display: "flex", flexDirection: "column", gap: 6 },
  barTopRow: { display: "flex", justifyContent: "space-between", alignItems: "baseline" },
  barLabel: { fontSize: 12, color: A_TOKENS.textMuted, fontWeight: 500 },
  barPct: (tone) => ({
    fontSize: 13,
    fontWeight: 700,
    color: { ok: A_TOKENS.info, warn: A_TOKENS.warn, danger: A_TOKENS.danger }[tone],
    fontFeatureSettings: '"tnum"',
    fontFamily: "'JetBrains Mono', ui-monospace, monospace",
  }),
  barTrack: { height: 6, background: A_TOKENS.borderSoft, borderRadius: 99, overflow: "hidden" },
  barFill: (pct, tone) => ({
    height: "100%",
    width: `${Math.min(100, pct)}%`,
    background: { ok: A_TOKENS.info, warn: A_TOKENS.warn, danger: A_TOKENS.danger }[tone],
    borderRadius: 99,
    transition: "width 400ms ease",
  }),
  barDetail: { fontSize: 11, color: A_TOKENS.textDim, fontFeatureSettings: '"tnum"' },
  // Reset chip
  resetChip: {
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
    padding: "3px 8px",
    borderRadius: 99,
    background: `${A_TOKENS.mauve}1a`,
    color: A_TOKENS.mauve,
    fontSize: 10,
    fontWeight: 600,
    letterSpacing: 0.3,
    fontFeatureSettings: '"tnum"',
  },
  divider: {
    margin: "2px 0",
    height: 1,
    background: A_TOKENS.borderSoft,
  },
  sectionLabel: {
    fontSize: 10,
    color: A_TOKENS.textDim,
    letterSpacing: 1,
    textTransform: "uppercase",
    fontWeight: 600,
    margin: "2px 0 -4px",
  },
};

function ABar({ label, percent, detail, tone, reset }) {
  return (
    <div style={aStyles.barBlock}>
      <div style={aStyles.barTopRow}>
        <span style={aStyles.barLabel}>{label}</span>
        <span style={aStyles.barPct(tone)}>{percent.toFixed(1)}%</span>
      </div>
      <div style={aStyles.barTrack}>
        <div style={aStyles.barFill(percent, tone)} />
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={aStyles.barDetail}>{detail}</span>
        {reset && <span style={aStyles.resetChip}>↻ {reset}</span>}
      </div>
    </div>
  );
}

function AStat({ label, value, accent }) {
  return (
    <div style={aStyles.stat}>
      <div style={aStyles.statLabel}>{label}</div>
      <div style={{ ...aStyles.statValue, color: accent || A_TOKENS.text }}>{value}</div>
    </div>
  );
}

function ACard({ svc, density = "comfortable" }) {
  const { name, short, accent, glyph, updated, data, id } = svc;
  const compact = density === "compact";
  return (
    <div style={aStyles.card(accent)}>
      <div style={aStyles.accentBar(accent)} />
      <div style={{ ...aStyles.header, padding: compact ? "10px 14px 8px" : "12px 16px 10px" }}>
        <div style={aStyles.glyph(accent)}>{glyph}</div>
        <div style={aStyles.titleStack}>
          <span style={aStyles.title}>{short}</span>
          <span style={aStyles.subtitle}>已更新 {updated}</span>
        </div>
        <div style={aStyles.statusDot("ok")} />
      </div>

      {id === "openai" && <AOpenAI data={data} compact={compact} />}
      {id === "claude_web" && <AClaudeWeb data={data} compact={compact} />}
      {id === "claude_api" && <AClaudeApi data={data} compact={compact} />}
      {id === "copilot" && <ACopilot data={data} compact={compact} />}
      {id === "openrouter" && <AOpenRouter data={data} compact={compact} />}
    </div>
  );
}

function AOpenAI({ data, compact }) {
  const creditsPct = (data.credits_used_usd / data.credits_total_usd) * 100;
  return (
    <>
      <div style={aStyles.hero}>
        <span style={aStyles.heroLabel}>餘額</span>
        <span style={{ ...aStyles.heroValue, color: A_TOKENS.ok }}>${data.balance_usd.toFixed(2)}</span>
      </div>
      <div style={aStyles.body}>
        <ABar
          label="Credits"
          percent={creditsPct}
          detail={`$${data.credits_used_usd.toFixed(2)} / $${data.credits_total_usd.toFixed(2)}`}
          tone={pctTone(creditsPct)}
        />
        <div style={aStyles.rowGrid}>
          <AStat label="本月用量" value={`$${data.month_usage_usd.toFixed(4)}`} />
          <AStat label="月上限" value={`$${data.hard_limit_usd.toFixed(0)}`} />
          <AStat label="用量等級" value={data.tier} />
          <AStat label="自動儲值" value={data.auto_recharge ? "已啟用" : "停用"} accent={data.auto_recharge ? A_TOKENS.ok : A_TOKENS.textDim} />
        </div>
      </div>
    </>
  );
}

function AClaudeWeb({ data, compact }) {
  const sTone = pctTone(data.session_percent);
  const wTone = pctTone(data.weekly_percent);
  const extraPct = (data.extra_spent / data.extra_limit) * 100;
  return (
    <>
      <div style={aStyles.hero}>
        <span style={aStyles.heroLabel}>每週限額</span>
        <span style={{ ...aStyles.heroValue, color: { ok: A_TOKENS.info, warn: A_TOKENS.warn, danger: A_TOKENS.danger }[wTone] }}>
          {data.weekly_percent}<span style={aStyles.heroSuffix}>%</span>
        </span>
        <span style={{ ...aStyles.resetChip, marginLeft: "auto" }}>{data.plan_type}</span>
      </div>
      <div style={aStyles.body}>
        <ABar label="本次工作階段" percent={data.session_percent} detail="" tone={sTone} reset={data.session_reset} />
        <ABar label="每週限額" percent={data.weekly_percent} detail="" tone={wTone} reset={data.weekly_reset} />
        {data.extra_enabled && (
          <>
            <div style={aStyles.divider} />
            <div style={aStyles.sectionLabel}>額外用量</div>
            <ABar
              label="本月已花費"
              percent={extraPct}
              detail={`$${data.extra_spent.toFixed(2)} / $${data.extra_limit.toFixed(0)}`}
              tone={pctTone(extraPct)}
              reset={data.extra_resets}
            />
            <div style={aStyles.rowGrid}>
              <AStat label="目前餘額" value={`$${data.extra_balance.toFixed(2)}`} accent={A_TOKENS.ok} />
              <AStat label="自動儲值" value={data.auto_reload ? "已啟用" : "停用"} accent={data.auto_reload ? A_TOKENS.ok : A_TOKENS.textDim} />
            </div>
          </>
        )}
      </div>
    </>
  );
}

function AClaudeApi({ data, compact }) {
  return (
    <>
      <div style={aStyles.hero}>
        <span style={aStyles.heroLabel}>餘額</span>
        <span style={{ ...aStyles.heroValue, color: A_TOKENS.ok }}>${data.balance_usd.toFixed(2)}</span>
        <span style={{ ...aStyles.resetChip, marginLeft: "auto" }}>{data.plan}</span>
      </div>
      <div style={aStyles.body}>
        <div style={aStyles.rowGrid}>
          <AStat label="本月用量" value={`$${data.this_month_usd.toFixed(4)}`} />
          <AStat label="下次計費" value={data.next_billing} />
          <AStat label="月費" value={`$${data.monthly_usd.toFixed(2)}`} />
          <AStat label="消費上限" value={`$${data.spend_limit_usd.toFixed(0)}`} />
        </div>
      </div>
    </>
  );
}

function ACopilot({ data, compact }) {
  const tone = pctTone(data.included_percent);
  return (
    <>
      <div style={aStyles.hero}>
        <span style={aStyles.heroLabel}>Premium</span>
        <span style={{ ...aStyles.heroValue, color: { ok: A_TOKENS.info, warn: A_TOKENS.warn, danger: A_TOKENS.danger }[tone] }}>
          {data.included_consumed}<span style={aStyles.heroSuffix}>/{data.included_total}</span>
        </span>
        <span style={{ ...aStyles.resetChip, marginLeft: "auto" }}>{data.plan}</span>
      </div>
      <div style={aStyles.body}>
        <ABar
          label="Premium Requests"
          percent={data.included_percent}
          detail={`已使用 ${data.included_percent.toFixed(1)}%`}
          tone={tone}
        />
        <div style={aStyles.rowGrid}>
          <AStat label="已計費" value={`$${data.billed_usd.toFixed(2)}`} accent={data.billed_usd > 0 ? A_TOKENS.peach : A_TOKENS.text} />
          <AStat label="重置於" value={`${data.resets_in_days} 天後`} accent={A_TOKENS.mauve} />
        </div>
      </div>
    </>
  );
}

function AOpenRouter({ data, compact }) {
  return (
    <>
      <div style={aStyles.hero}>
        <span style={aStyles.heroLabel}>餘額</span>
        <span style={{ ...aStyles.heroValue, color: A_TOKENS.ok }}>${data.balance_usd.toFixed(2)}</span>
      </div>
      <div style={aStyles.body}>
        <div style={aStyles.rowGrid}>
          <AStat label="本月花費" value={`$${data.month_spend_usd.toFixed(4)}`} />
          <AStat label="請求數" value={`${data.month_requests.toLocaleString()}`} />
          <AStat label="Tokens" value={fmtTokens(data.month_tokens)} />
          <AStat label="主要模型" value={data.top_model.split("/")[1] || data.top_model} />
        </div>
      </div>
    </>
  );
}

Object.assign(window, { ACard, A_TOKENS });
