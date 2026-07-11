import React, { useState } from "react";
import { useWebSocket } from "./hooks/useWebSocket";
import { useApi } from "./hooks/useApi";
import { GlucoseRing } from "./components/GlucoseRing";
import { GlucoseChart } from "./components/GlucoseChart";
import { PredictionPanel } from "./components/PredictionPanel";
import { ActionCards } from "./components/ActionCards";
import { ChatWindow } from "./components/ChatWindow";
import { TREND_ARROWS } from "./lib/constants";
import { Activity, ShieldCheck, RefreshCw, Languages } from "lucide-react";

export function App() {
  const [lang, setLang] = useState<"en" | "ar">("ar");
  const { data, isConnected, reconnect } = useWebSocket();
  const { logMeal, logActivity } = useApi();

  const isAr = lang === "ar";

  // Fallback default states before WebSocket connects
  const glucose = data?.glucose ?? 115;
  const trend = data?.trend ?? "STABLE";
  const trendArrowObj = TREND_ARROWS[trend] || TREND_ARROWS.STABLE;
  const rateOfChange = data?.rate_of_change ?? 0.0;
  const tirPercent = data?.tir_percent ?? 88.5;
  const history = data?.history ?? [];
  const forecast = data?.forecast ?? [];
  const urgencyLevel = data?.urgency_level ?? "stable";

  const cleanText = (str?: string) => {
    if (!str) return "";
    return str.replace(/[\*]/g, "");
  };

  const getDietarySuggestion = () => {
    if (!isAr) return cleanText(data?.dietary_suggestion || "");
    if (data?.dietary_suggestion_ar) return cleanText(data.dietary_suggestion_ar);
    const eng = data?.dietary_suggestion || "";
    if (!eng) return "";
    if (eng.includes("target range")) return "✅ الجلوكوز في النطاق المثالي. استمر على نمطك الغذائي الحالي. لوجبتك القادمة احرص على توازن حصص البروتين والخضروات والكربوهيدرات المعقدة.";
    if (eng.includes("Consume")) return "⚠️ تناول 15غ كربوهيدرات سريعة الآن (عصير برتقال أو أقراص جلوكوز). انتظر 15 دقيقة ثم أعد الفحص.";
    if (eng.includes("Avoid all carbohydrates") || eng.includes("Skip additional")) return "تجنب جميع الكربوهيدرات حتى ينخفض السكر دون 200 ملغ/ديسيلتر. اشرب كوبين من الماء الآن.";
    return cleanText(eng);
  };

  const getActivitySuggestion = () => {
    if (!isAr) return cleanText(data?.activity_suggestion || "");
    if (data?.activity_suggestion_ar) return cleanText(data.activity_suggestion_ar);
    const eng = data?.activity_suggestion || "";
    if (!eng) return "";
    if (eng.includes("Moderate exercise") || eng.includes("Great control")) return "الممارسة المعتدلة للرياضة (مشي سريع 30 دقيقة) مفيدة جداً. إذا خططت لتمرين شاق جهز وجبة خفيفة 15غ.";
    if (eng.includes("Stop any exercise") || eng.includes("Avoid exercise")) return "توقف عن ممارسة أي تمرين فوراً. استرح حتى يرتفع السكر فوق 100 ملغ/ديسيلتر.";
    if (eng.includes("walk at moderate pace") || eng.includes("light 15-minute walk")) return "المشي لمدة 15-20 دقيقة بوتيرة معتدلة سيساعد كثيراً في خفض مستوى الجلوكوز.";
    return cleanText(eng);
  };

  const getClinicalReasoning = () => {
    if (!isAr) return cleanText(data?.clinical_reasoning || "");
    if (data?.clinical_reasoning_ar) return cleanText(data.clinical_reasoning_ar);
    const eng = data?.clinical_reasoning || "";
    if (!eng) return "";
    if (eng.includes("target range")) return `الجلوكوز في النطاق المثالي (${Math.round(glucose)} ملغ/ديسيلتر). استمر في خطة العلاج الحالية.`;
    if (eng.includes("hypoglycemia") || eng.includes("Hypoglycemia")) return `هبوط سكر (${Math.round(glucose)} ملغ/ديسيلتر). تطبيق قاعدة 15 للعلاج الفوري بالكربوهيدرات.`;
    if (eng.includes("hyperglycemia") || eng.includes("Hyperglycemia")) return `ارتفاع في السكر (${Math.round(glucose)} ملغ/ديسيلتر). يُنصح بشرب الماء والمشي الخفيف ومراقبة الجرعات.`;
    return cleanText(eng);
  };

  const getPredictionText = () => {
    if (!isAr) return cleanText(data?.prediction_text || "");
    if (data?.prediction_text_ar) return cleanText(data.prediction_text_ar);
    const eng = data?.prediction_text || "";
    if (!eng) return "";
    if (eng.includes("Current glucose:") || eng.includes("Prediction:")) {
      const predMin = forecast.length > 0 ? Math.round(forecast[forecast.length - 1].predicted_glucose) : Math.round(glucose);
      return `السكر الحالي: ${Math.round(glucose)} ملغ/د | التوقعات: يُتوقع أن يصل الجلوكوز إلى حوالي ${predMin} ملغ/د خلال الـ 60 دقيقة القادمة | دقة التوقعات: عالية`;
    }
    return cleanText(eng);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 text-slate-100 flex flex-col font-sans selection:bg-purple-500 selection:text-white pb-12" dir={isAr ? "rtl" : "ltr"}>
      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-md border-b border-slate-800/80 px-6 py-4 flex items-center justify-between shadow-xl">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-emerald-500 via-teal-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <Activity className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-black tracking-tight text-white flex items-center gap-2">
              <span>DiaSentry</span>
              <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 bg-gradient-to-r from-purple-500 to-indigo-500 rounded-full text-white tracking-widest shadow-sm">
                Pro-Active AI
              </span>
            </h1>
            <p className="text-[11px] text-slate-400 font-medium">
              {isAr ? "نموذج Bergman الحركي • محرك LangGraph ReAct • أدلة ADA" : "Bergman Minimal Model • LangGraph ReAct Engine • ADA RAG"}
            </p>
          </div>
        </div>

        {/* Controls & Status */}
        <div className="flex items-center gap-4">
          {/* Language Switcher */}
          <button
            onClick={() => setLang(isAr ? "en" : "ar")}
            className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900 hover:bg-slate-800 border border-purple-500/30 text-xs font-bold text-purple-300 transition-all shadow-md shadow-purple-500/10"
            title="Toggle Language / تبديل اللغة"
          >
            <Languages className="w-3.5 h-3.5 text-purple-400" />
            <span>{isAr ? "English 🇺🇸" : "العربية 🇸🇦"}</span>
          </button>

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-xs font-semibold">
            <span className={`w-2 h-2 rounded-full animate-ping ${isConnected ? "bg-emerald-400" : "bg-red-500"}`} />
            <span className={`w-2 h-2 rounded-full ${isConnected ? "bg-emerald-400" : "bg-red-500"} -ml-4`} />
            <span className={isConnected ? "text-emerald-400" : "text-red-400"}>
              {isConnected ? (isAr ? "قياس عن بُعد مباشر" : "Live CGM Telemetry") : (isAr ? "غير متصل" : "Disconnected")}
            </span>
          </div>

          {!isConnected && (
            <button
              onClick={reconnect}
              className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition-all"
              title="Reconnect"
            >
              <RefreshCw className="w-4 h-4 animate-spin" />
            </button>
          )}
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 mt-2">
        {/* LEFT COLUMN: Core Metrics & Chart (7 Cols) */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          {/* SECTION 1: Core Metrics Gauge */}
          <section>
            <div className="flex items-center justify-between mb-3 px-1">
              <h2 className="text-xs font-extrabold uppercase tracking-widest text-slate-400 flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>{isAr ? "القسم 1: حركية سكر الدم اللحظية" : "Section 1: Real-Time CGM Kinetics"}</span>
              </h2>
              <span className="text-[11px] font-mono text-slate-500">
                {isAr ? "التحديث:" : "Updated:"} {data?.timestamp ? new Date(data.timestamp).toLocaleTimeString() : (isAr ? "الآن" : "Just now")}
              </span>
            </div>
            <GlucoseRing
              glucose={glucose}
              trendArrow={trendArrowObj.symbol}
              rateOfChange={rateOfChange}
              tirPercent={tirPercent}
              lang={lang}
            />
          </section>

          {/* SECTION 2: Predictive Horizon & Chart */}
          <section className="flex flex-col gap-4">
            <div className="flex items-center justify-between px-1">
              <h2 className="text-xs font-extrabold uppercase tracking-widest text-slate-400 flex items-center gap-1.5">
                <Activity className="w-4 h-4 text-purple-400" />
                <span>{isAr ? "القسم 2: تحليلات الأفق التوقعي" : "Section 2: Predictive Horizon Analytics"}</span>
              </h2>
            </div>
            <PredictionPanel
              predictionText={getPredictionText()}
              predictedHypo={data?.predicted_hypo || false}
              predictedHyper={data?.predicted_hyper || false}
              urgencyLevel={urgencyLevel}
              anomalyDetected={data?.anomaly_detected || false}
              anomalyDetails={isAr ? (data?.anomaly_details_ar || data?.anomaly_details || "") : (data?.anomaly_details || "")}
              lang={lang}
            />
            <GlucoseChart history={history} forecast={forecast} lang={lang} />
          </section>
        </div>

        {/* RIGHT COLUMN: Actionable AI Prescriptions & Chat (5 Cols) */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          {/* SECTION 3: Actionable AI Prescriptions */}
          <section className="flex flex-col gap-4">
            <div className="flex items-center justify-between px-1">
              <h2 className="text-xs font-extrabold uppercase tracking-widest text-slate-400 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                <span>{isAr ? "القسم 3: التوصيات العلاجية الاستباقية" : "Section 3: Actionable AI Prescriptions"}</span>
              </h2>
            </div>
            <ActionCards
              dietarySuggestion={getDietarySuggestion()}
              activitySuggestion={getActivitySuggestion()}
              clinicalReasoning={getClinicalReasoning()}
              urgencyLevel={urgencyLevel}
              onLogMeal={logMeal}
              onLogActivity={logActivity}
              lang={lang}
            />
          </section>

          {/* AI Conversational Assistant */}
          <section className="flex flex-col gap-2 mt-auto">
            <div className="flex items-center justify-between px-1">
              <h2 className="text-xs font-extrabold uppercase tracking-widest text-slate-400">
                {isAr ? "المساعد السريري التفاعلي بالذكاء الاصطناعي" : "Interactive Clinical AI Assistant"}
              </h2>
            </div>
            <ChatWindow lang={lang} />
          </section>
        </div>
      </main>
    </div>
  );
}
export default App;
