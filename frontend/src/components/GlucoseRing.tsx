import React from "react";
import { getGlucoseRingColor, GLUCOSE_ZONES } from "../lib/constants";

interface GlucoseRingProps {
  glucose: number;
  trendArrow: string;
  rateOfChange: number;
  tirPercent: number;
  lang?: "en" | "ar";
}

export const GlucoseRing: React.FC<GlucoseRingProps> = ({
  glucose,
  trendArrow,
  rateOfChange,
  tirPercent,
  lang = "ar",
}) => {
  const isAr = lang === "ar";
  const radius = 90;
  const strokeWidth = 14;
  const normalizedRadius = radius - strokeWidth * 0.5;
  const circumference = normalizedRadius * 2 * Math.PI;

  // Map glucose (40 - 350) to progress (0 - 1)
  const minG = 40;
  const maxG = 350;
  const progress = Math.min(Math.max((glucose - minG) / (maxG - minG), 0), 1);
  const strokeDashoffset = circumference - progress * circumference;

  const ringColor = getGlucoseRingColor(glucose);

  let statusText = isAr ? "ضمن المستهدف" : "IN RANGE";
  if (glucose < GLUCOSE_ZONES.HYPO) statusText = isAr ? "خطر هبوط" : "HYPORISK";
  else if (glucose > GLUCOSE_ZONES.HYPER) statusText = isAr ? "خطر ارتفاع" : "HYPER RISK";

  return (
    <div className="flex flex-col items-center justify-center p-6 bg-slate-900/60 backdrop-blur-xl border border-slate-800 rounded-3xl shadow-2xl relative overflow-hidden">
      {/* Background glow */}
      <div
        className="absolute w-48 h-48 rounded-full blur-3xl opacity-20 pointer-events-none transition-all duration-700"
        style={{ backgroundColor: ringColor }}
      />

      <div className="relative flex items-center justify-center">
        <svg
          height={radius * 2}
          width={radius * 2}
          className="transform -rotate-90 transition-all duration-500"
        >
          {/* Track Circle */}
          <circle
            stroke="rgba(255, 255, 255, 0.05)"
            fill="transparent"
            strokeWidth={strokeWidth}
            r={normalizedRadius}
            cx={radius}
            cy={radius}
          />
          {/* Progress Circle */}
          <circle
            stroke={ringColor}
            fill="transparent"
            strokeWidth={strokeWidth}
            strokeDasharray={circumference + " " + circumference}
            style={{ strokeDashoffset, transition: "stroke-dashoffset 0.8s ease-in-out, stroke 0.5s ease" }}
            strokeLinecap="round"
            r={normalizedRadius}
            cx={radius}
            cy={radius}
          />
        </svg>
        {/* Center Content */}
        <div className="absolute flex flex-col items-center justify-center text-center">
          <span className="text-xs font-semibold tracking-widest uppercase text-slate-400 mb-1">
            {statusText}
          </span>
          <div className="flex items-baseline gap-1">
            <span className="text-5xl font-extrabold tracking-tight text-white transition-all duration-300">
              {Math.round(glucose)}
            </span>
            <span className="text-3xl font-bold text-slate-300 animate-pulse">
              {trendArrow}
            </span>
          </div>
          <span className="text-xs font-medium text-slate-400 mt-1" dir="ltr">
            {rateOfChange > 0 ? `+${rateOfChange.toFixed(1)}` : rateOfChange.toFixed(1)} {isAr ? "ملغ/د/دقيقة" : "mg/dL/min"}
          </span>
        </div>
      </div>

      {/* Footer info */}
      <div className="flex items-center justify-between w-full mt-6 pt-4 border-t border-slate-800/80 text-xs text-slate-400 px-2">
        <div className="flex flex-col">
          <span className="text-slate-500 uppercase tracking-wider text-[10px]">{isAr ? "النطاق المستهدف" : "Target Range"}</span>
          <span className="font-semibold text-slate-300" dir="ltr">70 - 180 {isAr ? "ملغ/د" : "mg/dL"}</span>
        </div>
        <div className="flex flex-col text-right">
          <span className="text-slate-500 uppercase tracking-wider text-[10px]">{isAr ? "الوقت في النطاق" : "Time in Range"}</span>
          <span className="font-semibold text-emerald-400">{tirPercent}%</span>
        </div>
      </div>
    </div>
  );
};
