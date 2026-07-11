import React from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceArea,
  ReferenceLine,
} from "recharts";
import type { GlucoseHistoryPoint, ForecastPoint } from "../lib/types";
import { GLUCOSE_ZONES } from "../lib/constants";

interface GlucoseChartProps {
  history: GlucoseHistoryPoint[];
  forecast: ForecastPoint[];
  lang?: "en" | "ar";
}

export const GlucoseChart: React.FC<GlucoseChartProps> = ({ history, forecast, lang = "ar" }) => {
  const isAr = lang === "ar";
  // Merge history and forecast into a unified data array for Recharts
  const mergedData = [
    ...history.map((h) => ({
      time: h.time,
      actual: h.glucose,
      forecast: null as number | null,
    })),
    ...forecast.map((f, idx) => ({
      time: f.time,
      // Connect first forecast point to last actual reading for continuity
      actual: idx === 0 && history.length > 0 ? history[history.length - 1].glucose : null,
      forecast: f.predicted_glucose,
    })),
  ];

  return (
    <div className="p-5 bg-slate-900/60 backdrop-blur-xl border border-slate-800 rounded-3xl shadow-2xl flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold text-white tracking-wide uppercase">
            {isAr ? "حركية الجلوكوز وتوقعات الذكاء الاصطناعي" : "Glucose Kinetics & AI Forecast"}
          </h3>
          <p className="text-xs text-slate-400">
            {isAr ? "آخر 6 ساعات + أفق التوقع لمدة 60 دقيقة" : "Past 6 Hours + 60-Minute Predictive Horizon"}
          </p>
        </div>
        <div className="flex items-center gap-4 text-xs font-medium">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 inline-block" />
            <span className="text-slate-300">{isAr ? "الفعلية" : "Actual"}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-400 border border-purple-300 border-dashed inline-block" />
            <span className="text-slate-300">{isAr ? "توقع الذكاء الاصطناعي" : "AI Forecast"}</span>
          </div>
        </div>
      </div>

      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={mergedData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            {/* Target Range Band (70 - 180) */}
            <ReferenceArea
              y1={GLUCOSE_ZONES.TARGET_LOW}
              y2={GLUCOSE_ZONES.TARGET_HIGH}
              fill="rgba(52, 211, 153, 0.06)"
              strokeOpacity={0}
            />

            {/* Hypo threshold line */}
            <ReferenceLine
              y={GLUCOSE_ZONES.HYPO}
              stroke="rgba(239, 68, 68, 0.4)"
              strokeDasharray="3 3"
              label={{ value: isAr ? "هبوط (70)" : "Hypo (70)", fill: "#ef4444", fontSize: 10, position: "insideBottomLeft" }}
            />

            {/* Hyper threshold line */}
            <ReferenceLine
              y={GLUCOSE_ZONES.HYPER}
              stroke="rgba(251, 191, 36, 0.4)"
              strokeDasharray="3 3"
              label={{ value: isAr ? "ارتفاع (180)" : "Hyper (180)", fill: "#fbbf24", fontSize: 10, position: "insideTopLeft" }}
            />

            <XAxis
              dataKey="time"
              stroke="#64748b"
              fontSize={10}
              tickLine={false}
              axisLine={{ stroke: "rgba(255,255,255,0.08)" }}
              interval="preserveStartEnd"
            />
            <YAxis
              domain={[40, 350]}
              stroke="#64748b"
              fontSize={10}
              tickLine={false}
              axisLine={false}
              ticks={[50, 100, 150, 200, 250, 300]}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(15, 23, 42, 0.9)",
                borderColor: "rgba(255, 255, 255, 0.1)",
                borderRadius: "12px",
                fontSize: "12px",
                color: "#fff",
                backdropFilter: "blur(8px)",
              }}
            />

            {/* Actual Glucose Line */}
            <Line
              type="monotone"
              dataKey="actual"
              stroke="#34d399"
              strokeWidth={3}
              dot={false}
              activeDot={{ r: 6, fill: "#34d399", stroke: "#fff", strokeWidth: 2 }}
              isAnimationActive={false}
            />

            {/* AI Forecast Dotted Line */}
            <Line
              type="monotone"
              dataKey="forecast"
              stroke="#c084fc"
              strokeWidth={2.5}
              strokeDasharray="4 4"
              dot={false}
              activeDot={{ r: 5, fill: "#c084fc", stroke: "#fff", strokeWidth: 2 }}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
