import React, { useState } from "react";
import { Apple, Activity, MessageSquare, Utensils, Zap, CheckCircle2 } from "lucide-react";
import type { UrgencyLevel } from "../lib/types";

interface ActionCardsProps {
  dietarySuggestion: string;
  activitySuggestion: string;
  clinicalReasoning: string;
  urgencyLevel: UrgencyLevel;
  onLogMeal: (carbs: number, gi: number, name: string) => Promise<void>;
  onLogActivity: (duration: number, intensity: number, name: string) => Promise<void>;
  lang: "en" | "ar";
}

export const ActionCards: React.FC<ActionCardsProps> = ({
  dietarySuggestion,
  activitySuggestion,
  clinicalReasoning,
  urgencyLevel,
  onLogMeal,
  onLogActivity,
  lang,
}) => {
  const isAr = lang === "ar";
  const [activeTab, setActiveTab] = useState<"diet" | "activity" | "reasoning">("diet");

  // Form states
  const [foodName, setFoodName] = useState("");
  const [carbs, setCarbs] = useState("45");
  const [gi, setGi] = useState("55");
  const [mealSuccess, setMealSuccess] = useState(false);

  const [actName, setActName] = useState("");
  const [duration, setDuration] = useState("30");
  const [intensity, setIntensity] = useState("1.0");
  const [actSuccess, setActSuccess] = useState(false);

  const handleMealSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onLogMeal(Number(carbs), Number(gi), foodName || (isAr ? "وجبة مسجلة" : "Logged Meal"));
    setMealSuccess(true);
    setTimeout(() => setMealSuccess(false), 3000);
  };

  const handleActSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onLogActivity(Number(duration), Number(intensity), actName || (isAr ? "تمرين مسجل" : "Logged Exercise"));
    setActSuccess(true);
    setTimeout(() => setActSuccess(false), 3000);
  };

  return (
    <div className="flex flex-col bg-slate-900/60 backdrop-blur-xl border border-slate-800 rounded-3xl shadow-2xl overflow-hidden" dir={isAr ? "rtl" : "ltr"}>
      {/* Tabs Header */}
      <div className="flex border-b border-slate-800/80 bg-slate-950/40 p-1.5">
        <button
          onClick={() => setActiveTab("diet")}
          className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-2xl text-xs font-bold transition-all ${
            activeTab === "diet"
              ? "bg-gradient-to-r from-emerald-500/20 to-teal-500/20 text-emerald-300 border border-emerald-500/30 shadow-lg"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Apple className="w-4 h-4" />
          <span>{isAr ? "التوصيات الغذائية" : "Dietary Prescriptions"}</span>
        </button>

        <button
          onClick={() => setActiveTab("activity")}
          className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-2xl text-xs font-bold transition-all ${
            activeTab === "activity"
              ? "bg-gradient-to-r from-blue-500/20 to-indigo-500/20 text-blue-300 border border-blue-500/30 shadow-lg"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Activity className="w-4 h-4" />
          <span>{isAr ? "النشاط والحركية" : "Kinetics & Activity"}</span>
        </button>

        <button
          onClick={() => setActiveTab("reasoning")}
          className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-2xl text-xs font-bold transition-all ${
            activeTab === "reasoning"
              ? "bg-gradient-to-r from-purple-500/20 to-pink-500/20 text-purple-300 border border-purple-500/30 shadow-lg"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Zap className="w-4 h-4" />
          <span>{isAr ? "سلسلة التفكير" : "AI Reasoning Chain"}</span>
        </button>
      </div>

      {/* Tab Content */}
      <div className="p-6">
        {/* DIET TAB */}
        {activeTab === "diet" && (
          <div className="flex flex-col gap-6">
            <div className="p-4 rounded-2xl bg-emerald-950/20 border border-emerald-500/20">
              <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 block mb-1">
                {isAr ? "التوصية الغذائية للذكاء الاصطناعي (مدعومة بأدلة ADA)" : "AI Dietary Recommendation (ADA RAG Grounded)"}
              </span>
              <p className="text-xs text-slate-200 leading-relaxed font-medium">
                {dietarySuggestion || (isAr ? "لا إجراء غذائي فوري مطلوب. حركية الجلوكوز ضمن المستهدف." : "No immediate dietary action required. Glucose kinetics are within target limits.")}
              </p>
            </div>

            {/* Log Meal Form */}
            <form onSubmit={handleMealSubmit} className="flex flex-col gap-3 pt-2 border-t border-slate-800/80">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wide flex items-center gap-1.5">
                <Utensils className="w-3.5 h-3.5 text-emerald-400" />
                <span>{isAr ? "تسجيل وجبة في محاكاة الحركية" : "Log Meal Absorption Kinetics"}</span>
              </span>

              <div className="grid grid-cols-3 gap-2">
                <input
                  type="text"
                  placeholder={isAr ? "الطعام (مثال: بيتزا)" : "Food (e.g. Pizza)"}
                  value={foodName}
                  onChange={(e) => setFoodName(e.target.value)}
                  className="bg-slate-950/60 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-emerald-500"
                />
                <input
                  type="number"
                  placeholder={isAr ? "كربوهيدرات (غ)" : "Carbs (g)"}
                  value={carbs}
                  onChange={(e) => setCarbs(e.target.value)}
                  className="bg-slate-950/60 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-emerald-500"
                  required
                />
                <select
                  value={gi}
                  onChange={(e) => setGi(e.target.value)}
                  className="bg-slate-950/60 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                >
                  <option value="35">{isAr ? "مؤشر سكري منخفض (35)" : "Low GI (35)"}</option>
                  <option value="55">{isAr ? "مؤشر سكري متوسط (55)" : "Med GI (55)"}</option>
                  <option value="75">{isAr ? "مؤشر سكري مرتفع (75)" : "High GI (75)"}</option>
                </select>
              </div>

              <button
                type="submit"
                className="w-full py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold text-xs rounded-xl transition-all shadow-lg flex items-center justify-center gap-2"
              >
                {mealSuccess ? (
                  <>
                    <CheckCircle2 className="w-4 h-4" />
                    <span>{isAr ? "تم الحقن في محاكي Bergman!" : "Injected into Bergman Simulator!"}</span>
                  </>
                ) : (
                  <span>{isAr ? "حقن حدث الوجبة" : "Inject Meal Event"}</span>
                )}
              </button>
            </form>
          </div>
        )}

        {/* ACTIVITY TAB */}
        {activeTab === "activity" && (
          <div className="flex flex-col gap-6">
            <div className="p-4 rounded-2xl bg-blue-950/20 border border-blue-500/20">
              <span className="text-[10px] font-bold uppercase tracking-wider text-blue-400 block mb-1">
                {isAr ? "توصية النشاط البدني للذكاء الاصطناعي" : "AI Activity Prescription"}
              </span>
              <p className="text-xs text-slate-200 leading-relaxed font-medium">
                {activitySuggestion || (isAr ? "يُنصح بنشاط بدني يومي معتدل لتحسين حساسية الأنسولين." : "Moderate daily activity recommended to enhance insulin sensitivity.")}
              </p>
            </div>

            {/* Log Activity Form */}
            <form onSubmit={handleActSubmit} className="flex flex-col gap-3 pt-2 border-t border-slate-800/80">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wide flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5 text-blue-400" />
                <span>{isAr ? "تسجيل تمرين في محاكاة الحركية" : "Log Exercise Kinetics"}</span>
              </span>

              <div className="grid grid-cols-3 gap-2">
                <input
                  type="text"
                  placeholder={isAr ? "النشاط (مثال: جري)" : "Activity (e.g. Run)"}
                  value={actName}
                  onChange={(e) => setActName(e.target.value)}
                  className="bg-slate-950/60 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-blue-500"
                />
                <input
                  type="number"
                  placeholder={isAr ? "المدة (دقيقة)" : "Duration (min)"}
                  value={duration}
                  onChange={(e) => setDuration(e.target.value)}
                  className="bg-slate-950/60 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-blue-500"
                  required
                />
                <select
                  value={intensity}
                  onChange={(e) => setIntensity(e.target.value)}
                  className="bg-slate-950/60 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="0.5">{isAr ? "خفيف (0.5x)" : "Light (0.5x)"}</option>
                  <option value="1.0">{isAr ? "معتدل (1x)" : "Moderate (1x)"}</option>
                  <option value="2.0">{isAr ? "مكثف (2x)" : "Intense (2x)"}</option>
                </select>
              </div>

              <button
                type="submit"
                className="w-full py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold text-xs rounded-xl transition-all shadow-lg flex items-center justify-center gap-2"
              >
                {actSuccess ? (
                  <>
                    <CheckCircle2 className="w-4 h-4" />
                    <span>{isAr ? "تم الحقن في المحاكي!" : "Injected into Simulator!"}</span>
                  </>
                ) : (
                  <span>{isAr ? "حقن حدث التمرين" : "Inject Exercise Event"}</span>
                )}
              </button>
            </form>
          </div>
        )}

        {/* REASONING TAB */}
        {activeTab === "reasoning" && (
          <div className="flex flex-col gap-3">
            <span className="text-[10px] font-bold uppercase tracking-wider text-purple-400">
              {isAr ? "تتبع تنفيذ حلقة ReAct السريرية" : "LangGraph ReAct Execution Trace"}
            </span>
            <div className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800 font-mono text-[11px] text-slate-300 leading-relaxed overflow-y-auto max-h-48 whitespace-pre-wrap">
              {clinicalReasoning || (isAr ? "جاري تنفيذ حلقة التفكير الذاتي ReAct..." : "Executing autonomous ReAct reasoning loop...")}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
