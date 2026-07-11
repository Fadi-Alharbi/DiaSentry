import React from "react";
import { AlertTriangle, ShieldCheck, Activity } from "lucide-react";
import type { UrgencyLevel } from "../lib/types";

interface PredictionPanelProps {
  predictionText: string;
  predictedHypo: boolean;
  predictedHyper: boolean;
  urgencyLevel: UrgencyLevel;
  anomalyDetected: boolean;
  anomalyDetails: string;
  lang: "en" | "ar";
}

export const PredictionPanel: React.FC<PredictionPanelProps> = ({
  predictionText,
  predictedHypo,
  predictedHyper,
  urgencyLevel,
  anomalyDetected,
  anomalyDetails,
  lang,
}) => {
  const isAr = lang === "ar";

  return (
    <div className="flex flex-col gap-3" dir={isAr ? "rtl" : "ltr"}>
      {/* Urgent Warning Banners */}
      {(predictedHypo || predictedHyper || urgencyLevel === "critical" || anomalyDetected) && (
        <div className="flex flex-col gap-2">
          {predictedHypo && (
            <div className="flex items-start gap-3 p-4 bg-red-500/15 border border-red-500/30 rounded-2xl animate-pulse">
              <AlertTriangle className="w-6 h-6 text-red-400 shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-bold text-red-300 uppercase tracking-wide">
                  {isAr ? "تنبيه هبوط السكر (متوقع)" : "Hypoglycemia Alert (Predicted)"}
                </h4>
                <p className="text-xs text-red-200 mt-1">
                  {isAr
                    ? "يُتوقع انخفاض الجلوكوز دون 70 ملغ/ديسيلتر قريباً. تناول 15غ كربوهيدرات سريعة فوراً."
                    : "Glucose is forecasted to breach the 70 mg/dL threshold soon. Consume 15g fast-acting carbs immediately."}
                </p>
              </div>
            </div>
          )}

          {predictedHyper && (
            <div className="flex items-start gap-3 p-4 bg-amber-500/15 border border-amber-500/30 rounded-2xl">
              <AlertTriangle className="w-6 h-6 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-bold text-amber-300 uppercase tracking-wide">
                  {isAr ? "تحذير ارتفاع السكر" : "Hyperglycemia Warning"}
                </h4>
                <p className="text-xs text-amber-200 mt-1">
                  {isAr
                    ? "يُتوقع تجاوز الجلوكوز 180 ملغ/ديسيلتر. اتبع بروتوكول التصحيح واشرب الماء بانتظام."
                    : "Glucose is forecasted to exceed 180 mg/dL. Follow your correction protocol and stay hydrated."}
                </p>
              </div>
            </div>
          )}

          {anomalyDetected && (
            <div className="flex items-start gap-3 p-4 bg-purple-500/15 border border-purple-500/30 rounded-2xl">
              <Activity className="w-6 h-6 text-purple-400 shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-bold text-purple-300 uppercase tracking-wide">
                  {isAr ? "شذوذ غير مبرر في حركية السكر" : "Unexplained Kinetics Anomaly"}
                </h4>
                <p className="text-xs text-purple-200 mt-1">{anomalyDetails}</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* AI Predictive Summary Card */}
      <div className="p-5 bg-slate-900/60 backdrop-blur-xl border border-slate-800 rounded-3xl shadow-xl flex items-start gap-3">
        <ShieldCheck className="w-5 h-5 text-purple-400 shrink-0 mt-0.5" />
        <div className="flex-1">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-bold uppercase tracking-wider text-purple-400">
              {isAr ? "توقعات الذكاء الاصطناعي الزمنية" : "AI Time-Series Prediction"}
            </span>
            <span className="text-[10px] font-semibold px-2 py-0.5 bg-purple-500/10 border border-purple-500/20 text-purple-300 rounded-full">
              {isAr ? "محرك ReAct" : "ReAct Engine"}
            </span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed font-medium">
            {predictionText || (isAr ? "جاري تحليل الحركية وبناء الأفق التوقعي..." : "Analyzing sensor kinetics and generating predictive horizon...")}
          </p>
        </div>
      </div>
    </div>
  );
};
