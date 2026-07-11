/* ═══════════════════════════════════════════════════════════════
   DiaSentry — Constants
   Glucose zones, colors, trend arrow mappings, and configuration
   ═══════════════════════════════════════════════════════════════ */

// Backend URL detection — supports both Local Dev (5173) and Hugging Face Spaces (Docker / HTTPS)
const isDev = window.location.port === "5173" || window.location.port === "3000";
const apiHost = isDev ? `${window.location.hostname}:8000` : window.location.host;
const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
const httpProtocol = window.location.protocol === "https:" ? "https:" : "http:";

export const WS_URL = `${wsProtocol}//${apiHost}/ws/live`;
export const CHAT_WS_URL = `${wsProtocol}//${apiHost}/ws/chat`;
export const API_BASE = `${httpProtocol}//${apiHost}`;

// ── Glucose Zones ──
export const GLUCOSE_ZONES = {
  HYPO_CRITICAL: 54,
  HYPO: 70,
  TARGET_LOW: 70,
  TARGET_HIGH: 180,
  HYPER: 180,
  HYPER_CRITICAL: 250,
  HYPER_SEVERE: 300,
} as const;

// ── Zone Colors (HSL for smooth interpolation) ──
export const ZONE_COLORS = {
  critical: { bg: "rgba(239,68,68,0.15)", text: "#ef4444", glow: "0 0 24px rgba(239,68,68,0.4)" },
  warning:  { bg: "rgba(251,191,36,0.15)", text: "#fbbf24", glow: "0 0 24px rgba(251,191,36,0.3)" },
  stable:   { bg: "rgba(52,211,153,0.15)", text: "#34d399", glow: "0 0 24px rgba(52,211,153,0.3)" },
} as const;

// ── Trend Arrow Mappings ──
export const TREND_ARROWS: Record<string, { symbol: string; rotation: number; label: string }> = {
  RAPIDLY_RISING:    { symbol: "⬆⬆", rotation: 0,   label: "Rapidly Rising" },
  RISING:            { symbol: "⬆",   rotation: 0,   label: "Rising" },
  SLIGHTLY_RISING:   { symbol: "↗",   rotation: 0,   label: "Slightly Rising" },
  STABLE:            { symbol: "➡",   rotation: 0,   label: "Stable" },
  SLIGHTLY_FALLING:  { symbol: "↘",   rotation: 0,   label: "Slightly Falling" },
  FALLING:           { symbol: "⬇",   rotation: 0,   label: "Falling" },
  RAPIDLY_FALLING:   { symbol: "⬇⬇", rotation: 0,   label: "Rapidly Falling" },
};

// ── Utility Functions ──

export function getGlucoseZone(glucose: number): "critical" | "warning" | "stable" {
  if (glucose < GLUCOSE_ZONES.HYPO || glucose > GLUCOSE_ZONES.HYPER_CRITICAL) return "critical";
  if (glucose < GLUCOSE_ZONES.TARGET_LOW + 10 || glucose > GLUCOSE_ZONES.HYPER) return "warning";
  return "stable";
}

export function getGlucoseColor(glucose: number): string {
  if (glucose < GLUCOSE_ZONES.HYPO_CRITICAL) return "#ef4444";
  if (glucose < GLUCOSE_ZONES.HYPO) return "#f97316";
  if (glucose <= GLUCOSE_ZONES.TARGET_HIGH) return "#34d399";
  if (glucose <= GLUCOSE_ZONES.HYPER_CRITICAL) return "#fbbf24";
  return "#ef4444";
}

export function getGlucoseRingColor(glucose: number): string {
  if (glucose < GLUCOSE_ZONES.HYPO_CRITICAL) return "#ef4444";
  if (glucose < GLUCOSE_ZONES.HYPO) return "#f97316";
  if (glucose <= 120) return "#34d399";
  if (glucose <= 160) return "#a3e635";
  if (glucose <= GLUCOSE_ZONES.TARGET_HIGH) return "#fbbf24";
  if (glucose <= GLUCOSE_ZONES.HYPER_CRITICAL) return "#f97316";
  return "#ef4444";
}
