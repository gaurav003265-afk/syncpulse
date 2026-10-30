import React, { useState } from "react";
import {
  Calendar,
  AlertTriangle,
  Search,
  Users,
  CheckCircle2,
  Clock,
  ArrowRight,
  ShieldAlert,
  Flame,
  Activity,
  PhoneCall,
  RefreshCw,
  HeartPulse,
  BookOpen,
} from "lucide-react";
import { dataService, FirstAidTopic } from "../engine/dataService";
import { NavTab } from "./Navbar";

interface HomeScreenProps {
  setActiveTab: (tab: NavTab) => void;
  isOnline: boolean;
  onOpenAskWithQuery?: (query: string) => void;
}

export const HomeScreen: React.FC<HomeScreenProps> = ({
  setActiveTab,
  isOnline,
  onOpenAskWithQuery,
}) => {
  const [selectedFirstAid, setSelectedFirstAid] = useState<FirstAidTopic | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncFeedback, setSyncFeedback] = useState<string | null>(null);

  const kpis = dataService.getKPIs();
  const activities = dataService.getActivityLog();
  const firstAidTopics = dataService.getFirstAidTopics();

  const handleQuickSync = async () => {
    setSyncing(true);
    setSyncFeedback(null);
    try {
      const res = await dataService.flushSyncToServer();
      if (res.success) {
        setSyncFeedback(`✓ Reconciled ${res.count} record(s) with sub-center SQLite register.`);
      } else {
        setSyncFeedback(`⚠️ ${res.error}`);
      }
    } catch (e: any) {
      setSyncFeedback("⚠️ Could not contact server. Records remain safe in offline outbox.");
    } finally {
      setSyncing(false);
      setTimeout(() => setSyncFeedback(null), 5000);
    }
  };

  const sampleSearchChips = [
    "7 months pregnant bleeding",
    "Routine ANC visit schedule",
    "Newborn breathing fast >= 60 bpm",
    "ORS packet mixing ratio",
  ];

  return (
    <div className="space-y-5 pb-16 sm:pb-6">
      {/* 0. Connectivity & Subsystem Readiness Banner */}
      <div
        className={`rounded-xl p-3 border flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs shadow-xs transition ${
          isOnline
            ? "bg-emerald-50 border-emerald-200 text-emerald-950"
            : "bg-amber-50 border-amber-300 text-amber-950"
        }`}
      >
        <div className="flex items-center space-x-2">
          <span
            className={`w-2.5 h-2.5 rounded-full shrink-0 ${
              isOnline ? "bg-emerald-600" : "bg-amber-500 animate-pulse"
            }`}
          />
          <span className="font-bold">
            {isOnline
              ? "Online (Connected to Local Sub-Center Hub)"
              : "100% Offline Mode (Internet Disconnected)"}
          </span>
          <span className="text-slate-400 hidden md:inline">•</span>
          <span className="text-[11px] text-slate-700 hidden md:inline">
            Local Subsystems: 500 Households SQLite • MoHFW Protocols (58 Chunks) • 100% Safety Gate Active
          </span>
        </div>
        <div className="flex items-center space-x-2 font-mono text-[11px]">
          <span className="bg-white/80 px-2 py-0.5 rounded border border-slate-200 font-bold">
            Pending Outbox: {kpis.pendingSync}
          </span>
        </div>
      </div>

      {/* 1. Worker Profile Header & Status Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 sm:p-5 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 rounded-full bg-teal-100 border border-teal-300 flex items-center justify-center text-teal-800 font-bold text-lg">
              SD
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-base sm:text-lg font-bold text-slate-900 leading-snug">
                  Namaste, Sravani Devi (ASHA)
                </h2>
                <span className="bg-teal-100 text-teal-800 text-[10px] font-bold px-2 py-0.5 rounded-full">
                  ID: ASHA-8841
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Primary Health Centre: Venkatapuram Sub-Center • Sector 4 (Rural)
              </p>
            </div>
          </div>

          {/* Sync status card & action */}
          <div className="flex items-center space-x-2 pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-100">
            {kpis.pendingSync > 0 ? (
              <button
                onClick={handleQuickSync}
                disabled={syncing}
                className="flex items-center space-x-1.5 bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-300 px-3 py-1.5 rounded-lg text-xs font-semibold transition"
                title="Click to sync offline changes with local hub"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${syncing ? "animate-spin" : ""}`} />
                <span>{kpis.pendingSync} Outbox Changes (Sync)</span>
              </button>
            ) : (
              <div className="flex items-center space-x-1.5 text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-lg font-semibold">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                <span>Register Up to Date</span>
              </div>
            )}
          </div>
        </div>

        {syncFeedback && (
          <div className="mt-3 p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-700 font-medium">
            {syncFeedback}
          </div>
        )}
      </div>

      {/* 2. Critical Emergency Shortcut Banner */}
      <div className="bg-gradient-to-r from-red-600 to-rose-700 text-white rounded-xl p-4 shadow-md flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center space-x-3">
          <div className="bg-white/20 p-2.5 rounded-lg shrink-0">
            <ShieldAlert className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="text-sm sm:text-base font-bold tracking-tight">
              Obstetric & Neonatal Emergency Desk
            </h3>
            <p className="text-xs text-red-100">
              Deterministic danger signs triage, pre-referral stabilization protocols & 108 referral.
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-2 w-full sm:w-auto">
          <button
            onClick={() => setActiveTab("emergency")}
            className="flex-1 sm:flex-initial bg-white text-red-700 hover:bg-red-50 font-bold px-3.5 py-2 rounded-lg text-xs transition shadow-sm flex items-center justify-center space-x-1.5"
          >
            <span>Open Emergency Desk</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
          <a
            href="tel:108"
            className="bg-red-950/40 hover:bg-red-950 text-white font-bold px-3 py-2 rounded-lg text-xs transition border border-red-400/50 flex items-center space-x-1"
            title="Direct Cellular Call to 108"
          >
            <PhoneCall className="w-3.5 h-3.5 text-red-200" />
            <span>108</span>
          </a>
        </div>
      </div>

      {/* 3. Real KPI Metric Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Today's Due */}
        <div
          onClick={() => setActiveTab("visits")}
          className="bg-white border border-slate-200 hover:border-teal-400 p-3.5 rounded-xl shadow-sm cursor-pointer transition"
        >
          <div className="flex items-center justify-between text-slate-500 mb-1.5">
            <span className="text-xs font-semibold">Today's Visits</span>
            <Calendar className="w-4 h-4 text-teal-600" />
          </div>
          <div className="text-2xl font-black text-slate-900 leading-tight">
            {kpis.todayDue}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Scheduled for field visit</p>
        </div>

        {/* Overdue */}
        <div
          onClick={() => setActiveTab("visits")}
          className="bg-white border border-slate-200 hover:border-amber-400 p-3.5 rounded-xl shadow-sm cursor-pointer transition"
        >
          <div className="flex items-center justify-between text-slate-500 mb-1.5">
            <span className="text-xs font-semibold">Overdue Routine</span>
            <Clock className="w-4 h-4 text-amber-600" />
          </div>
          <div className="text-2xl font-black text-amber-700 leading-tight">
            {kpis.overdue}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Beneficiaries past due date</p>
        </div>

        {/* High Risk Critical */}
        <div
          onClick={() => setActiveTab("visits")}
          className="bg-white border border-slate-200 hover:border-red-400 p-3.5 rounded-xl shadow-sm cursor-pointer transition"
        >
          <div className="flex items-center justify-between text-slate-500 mb-1.5">
            <span className="text-xs font-semibold">High-Risk Cases</span>
            <AlertTriangle className="w-4 h-4 text-red-600" />
          </div>
          <div className="text-2xl font-black text-red-700 leading-tight">
            {kpis.highRisk}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Severe anemia, hypertension, SAM</p>
        </div>

        {/* Completed Visits */}
        <div
          onClick={() => setActiveTab("households")}
          className="bg-white border border-slate-200 hover:border-emerald-400 p-3.5 rounded-xl shadow-sm cursor-pointer transition"
        >
          <div className="flex items-center justify-between text-slate-500 mb-1.5">
            <span className="text-xs font-semibold">Completed Visits</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-black text-emerald-700 leading-tight">
            {kpis.completed}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Of 500 households registered</p>
        </div>
      </div>

      {/* 4. Unified Search Bar Entry to "Ask Sakhi" */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Search className="w-4 h-4 text-teal-700" />
            <h3 className="text-sm font-bold text-slate-900">
              Ask Sakhi — Clinical Protocol Search
            </h3>
          </div>
          <span className="text-[11px] font-semibold text-teal-700 bg-teal-50 px-2 py-0.5 rounded border border-teal-200">
            100% Offline (188 KB Index)
          </span>
        </div>

        {/* Interactive Clickable Input triggering Ask Sakhi */}
        <div
          onClick={() => setActiveTab("ask")}
          className="flex items-center space-x-3 bg-slate-50 hover:bg-slate-100 border border-slate-300 rounded-xl px-3.5 py-3 text-sm text-slate-500 cursor-pointer transition shadow-inner"
        >
          <Search className="w-4 h-4 text-slate-400 shrink-0" />
          <span className="flex-1 truncate">
            Ask symptom, danger sign, ANC schedule, or ORS preparation...
          </span>
          <span className="bg-teal-700 text-white text-xs font-bold px-2.5 py-1 rounded-lg">
            Search
          </span>
        </div>

        {/* Quick Suggestion Chips */}
        <div className="flex flex-wrap gap-1.5 pt-1">
          <span className="text-[11px] font-medium text-slate-400 self-center mr-1">
            Try:
          </span>
          {sampleSearchChips.map((chip, idx) => (
            <button
              key={idx}
              onClick={() => {
                if (onOpenAskWithQuery) onOpenAskWithQuery(chip);
                setActiveTab("ask");
              }}
              className="text-[11px] bg-slate-100 hover:bg-teal-50 hover:text-teal-800 text-slate-700 px-2.5 py-1 rounded-full border border-slate-200 transition"
            >
              {chip}
            </button>
          ))}
        </div>
      </div>

      {/* 5. The Cure Window — Approved First-Aid Guides */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <HeartPulse className="w-4 h-4 text-rose-600" />
            <h3 className="text-sm font-bold text-slate-900">
              The Cure Window — Approved Field First-Aid
            </h3>
          </div>
          <span className="text-[11px] text-slate-500 font-medium">
            MoHFW & WHO Approved Guides
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
          {firstAidTopics.map((topic) => (
            <div
              key={topic.id}
              onClick={() => setSelectedFirstAid(topic)}
              className="border border-slate-200 hover:border-teal-500 p-3 rounded-lg cursor-pointer bg-slate-50/50 hover:bg-teal-50/40 transition group"
            >
              <div className="flex items-center justify-between text-xs font-bold text-teal-800 mb-1">
                <span>{topic.category}</span>
                <BookOpen className="w-3.5 h-3.5 text-slate-400 group-hover:text-teal-600" />
              </div>
              <h4 className="text-xs font-bold text-slate-800 leading-snug line-clamp-1">
                {topic.title}
              </h4>
              <p className="text-[11px] text-slate-500 line-clamp-2 mt-1">
                {topic.scenario}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* 6. Recent Stored Activity Feed */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Activity className="w-4 h-4 text-teal-700" />
            <h3 className="text-sm font-bold text-slate-900">
              Recent Field Log (Local Records)
            </h3>
          </div>
          <span className="text-[11px] text-slate-500 font-mono">
            {activities.length} Recorded
          </span>
        </div>

        {activities.length === 0 ? (
          <div className="text-center py-6 text-slate-400 text-xs">
            No recent activity recorded yet. Completed visits and alerts appear here.
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {activities.slice(0, 5).map((act) => (
              <div key={act.id} className="py-2.5 flex items-start justify-between gap-2">
                <div className="space-y-0.5">
                  <div className="flex items-center space-x-2">
                    <span
                      className={`text-xs font-bold ${
                        act.isEmergency ? "text-red-700" : "text-slate-800"
                      }`}
                    >
                      {act.title}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    {act.description}
                  </p>
                </div>
                <span className="text-[10px] text-slate-400 shrink-0 mt-0.5">
                  {act.timestamp}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 7. First-Aid Detail Modal Dialog */}
      {selectedFirstAid && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-3 z-50">
          <div className="bg-white rounded-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto shadow-2xl border border-slate-200 p-5 space-y-4">
            <div className="flex items-start justify-between border-b border-slate-200 pb-3">
              <div>
                <span className="text-[11px] font-bold text-teal-700 uppercase tracking-wide">
                  {selectedFirstAid.category}
                </span>
                <h3 className="text-base font-bold text-slate-900">
                  {selectedFirstAid.title}
                </h3>
              </div>
              <button
                onClick={() => setSelectedFirstAid(null)}
                className="text-slate-400 hover:text-slate-700 text-lg font-bold p-1 leading-none"
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            {/* Scenario */}
            <div className="bg-slate-50 p-2.5 rounded-lg text-xs text-slate-700 border border-slate-200">
              <strong>Clinical Presentation:</strong> {selectedFirstAid.scenario}
            </div>

            {/* Step-by-Step Care */}
            <div className="space-y-2">
              <h4 className="text-xs font-bold text-slate-900 uppercase">
                Step-by-Step Field Care:
              </h4>
              <ol className="list-decimal list-inside space-y-1.5 text-xs text-slate-700">
                {selectedFirstAid.steps.map((step, idx) => (
                  <li key={idx} className="leading-relaxed">
                    {step}
                  </li>
                ))}
              </ol>
            </div>

            {/* Harmful Practices Warning */}
            {selectedFirstAid.what_not_to_do && (
              <div className="bg-amber-50 border border-amber-200 p-3 rounded-lg text-xs space-y-1">
                <span className="font-bold text-amber-900 flex items-center space-x-1">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />
                  <span>Harmful Practices to Avoid:</span>
                </span>
                <ul className="list-disc list-inside text-amber-800 space-y-0.5">
                  {selectedFirstAid.what_not_to_do.map((item, idx) => (
                    <li key={idx}>{item}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Red Flags Referral */}
            <div className="bg-red-50 border border-red-200 p-3 rounded-lg text-xs space-y-1.5">
              <span className="font-bold text-red-900 flex items-center space-x-1">
                <ShieldAlert className="w-3.5 h-3.5 text-red-700" />
                <span>Immediate Hospital Referral Signs:</span>
              </span>
              <ul className="list-disc list-inside text-red-800 space-y-0.5">
                {selectedFirstAid.red_flags.map((flag, idx) => (
                  <li key={idx}>{flag}</li>
                ))}
              </ul>
              <p className="text-[11px] font-semibold text-red-900 pt-1 border-t border-red-200/60">
                {selectedFirstAid.doctor_referral_advice}
              </p>
            </div>

            <div className="flex justify-between items-center pt-2 border-t border-slate-100 text-[11px] text-slate-400">
              <span>Source: {selectedFirstAid.source_citation}</span>
              <button
                onClick={() => setSelectedFirstAid(null)}
                className="bg-slate-800 hover:bg-slate-900 text-white font-semibold px-4 py-1.5 rounded-lg text-xs transition"
              >
                Close Protocol
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
