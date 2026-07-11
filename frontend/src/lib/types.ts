/* ═══════════════════════════════════════════════════════════════
   DiaSentry — TypeScript Interfaces
   Matching backend Pydantic models for type-safe communication
   ═══════════════════════════════════════════════════════════════ */

// Trend direction matching CGM standards
export type TrendDirection =
  | "RAPIDLY_RISING"
  | "RISING"
  | "SLIGHTLY_RISING"
  | "STABLE"
  | "SLIGHTLY_FALLING"
  | "FALLING"
  | "RAPIDLY_FALLING";

export type UrgencyLevel = "critical" | "warning" | "stable";

// A single historical glucose reading for the chart
export interface GlucoseHistoryPoint {
  time: string;           // HH:MM formatted
  glucose: number;        // mg/dL
  timestamp: string;      // ISO string
}

// A single forecast point
export interface ForecastPoint {
  time: string;
  minutes_ahead: number;
  predicted_glucose: number;
  timestamp: string;
}

// Complete dashboard payload from the WebSocket
export interface DashboardPayload {
  type: string;            // "glucose_update"
  timestamp: string;

  // Core metrics
  glucose: number;
  trend: TrendDirection;
  trend_arrow: string;
  rate_of_change: number;

  // Chart data
  history: GlucoseHistoryPoint[];
  forecast: ForecastPoint[];

  // Predictions
  predicted_hypo: boolean;
  predicted_hyper: boolean;
  prediction_text: string;
  prediction_text_ar?: string;

  // AI Recommendations
  urgency_level: UrgencyLevel;
  dietary_suggestion: string;
  dietary_suggestion_ar?: string;
  activity_suggestion: string;
  activity_suggestion_ar?: string;
  clinical_reasoning: string;
  clinical_reasoning_ar?: string;

  // Anomaly
  anomaly_detected: boolean;
  anomaly_details: string;
  anomaly_details_ar?: string;

  // Context
  iob_units: number;
  exercise_active: boolean;
  tir_percent: number;
}

// Chat message
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

// Chat response from WebSocket
export interface ChatResponse {
  type: "chat_response";
  response: string;
  timestamp: string;
}

// Meal event for logging
export interface MealEventPayload {
  type: "log_meal";
  carbs_g: number;
  glycemic_index: number;
  food_name: string;
}

// Activity event for logging
export interface ActivityEventPayload {
  type: "log_activity";
  duration_min: number;
  intensity: number;
  activity_name: string;
}
