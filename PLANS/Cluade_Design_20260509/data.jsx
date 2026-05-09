// Shared service data used by both variants.
// Mirrors the field structure produced by services/browser_data.py

const SERVICES = [
  {
    id: "openai",
    name: "OpenAI 帳單",
    short: "OpenAI",
    accent: "#74c7ec", // sapphire
    accentRGB: "116, 199, 236",
    glyph: "OA",
    updated: "13:42:08",
    data: {
      balance_usd: 42.18,
      credits_used_usd: 3.74,
      credits_total_usd: 5.0,
      month_usage_usd: 1.2341,
      hard_limit_usd: 120.0,
      tier: "Tier 1",
      auto_recharge: true,
    },
  },
  {
    id: "claude_web",
    name: "Claude.ai 用量",
    short: "Claude.ai",
    accent: "#c6a0f6", // mauve
    accentRGB: "198, 160, 246",
    glyph: "C",
    updated: "13:41:55",
    data: {
      plan_type: "Pro",
      session_percent: 32,
      session_reset: "今晚 23:00",
      weekly_percent: 67,
      weekly_reset: "週一 09:00",
      extra_enabled: true,
      extra_spent: 4.2,
      extra_limit: 25.0,
      extra_balance: 20.8,
      extra_resets: "2026/06/01",
      auto_reload: true,
    },
  },
  {
    id: "claude_api",
    name: "Claude API 帳單",
    short: "Claude API",
    accent: "#cba6f7", // lavender
    accentRGB: "203, 166, 247",
    glyph: "API",
    updated: "13:42:01",
    data: {
      balance_usd: 87.4,
      plan: "Build",
      this_month_usd: 14.231,
      next_billing: "2026/05/28",
      monthly_usd: 5.0,
      spend_limit_usd: 200.0,
    },
  },
  {
    id: "copilot",
    name: "GitHub Copilot",
    short: "Copilot",
    accent: "#a6e3a1", // green
    accentRGB: "166, 227, 161",
    glyph: "GH",
    updated: "13:40:12",
    data: {
      plan: "Copilot Pro",
      included_consumed: 312,
      included_total: 1500,
      included_percent: 20.8,
      billed_usd: 0,
      resets_in_days: 12,
      next_billing: "2026/05/21",
    },
  },
  {
    id: "openrouter",
    name: "OpenRouter",
    short: "OpenRouter",
    accent: "#7287fd", // periwinkle
    accentRGB: "114, 135, 253",
    glyph: "OR",
    updated: "13:42:14",
    data: {
      balance_usd: 24.5,
      month_spend_usd: 3.821,
      month_requests: 1247,
      month_tokens: 4_220_000,
      top_model: "anthropic/claude-3.5",
    },
  },
];

function fmtTokens(n) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function pctTone(pct) {
  if (pct >= 85) return "danger";
  if (pct >= 60) return "warn";
  return "ok";
}

window.SERVICES = SERVICES;
window.fmtTokens = fmtTokens;
window.pctTone = pctTone;
