import React, { useState, useEffect } from "react";
import { Navbar, NavTab } from "./components/Navbar";
import { HomeScreen } from "./components/HomeScreen";
import { AskScreen } from "./components/AskScreen";
import { HouseholdsScreen } from "./components/HouseholdsScreen";
import { VisitsScreen } from "./components/VisitsScreen";
import { EmergencyScreen } from "./components/EmergencyScreen";
import { StatusScreen } from "./components/StatusScreen";
import { PipelineTS } from "./engine/pipeline";
import { dataService } from "./engine/dataService";

// Client-side pipeline singleton for 100% offline inference
const pipelineTS = new PipelineTS();

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavTab>("home");
  const [isOnline, setIsOnline] = useState<boolean>(
    typeof navigator !== "undefined" ? navigator.onLine : false
  );
  const [selectedLanguage, setSelectedLanguage] = useState<"en" | "te" | "hi">("en");

  // Inter-screen navigation handoffs
  const [askQuery, setAskQuery] = useState<string>("");
  const [visitTargetHouseholdId, setVisitTargetHouseholdId] = useState<string | null>(null);

  // Live KPI counters
  const [counts, setCounts] = useState(dataService.getKPIs());

  const refreshCounts = () => {
    setCounts(dataService.getKPIs());
  };

  useEffect(() => {
    refreshCounts();

    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  const handleOpenAskWithQuery = (queryText: string) => {
    setAskQuery(queryText);
    setActiveTab("ask");
  };

  const handleStartVisitForHousehold = (hhId: string) => {
    setVisitTargetHouseholdId(hhId);
    setActiveTab("visits");
  };

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col font-sans text-slate-900 antialiased selection:bg-teal-600 selection:text-white">
      {/* Top Navbar & Header */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isOnline={isOnline}
        setIsOnline={setIsOnline}
        pendingSyncCount={counts.pendingSync}
        criticalAlertCount={counts.criticalAlerts}
        selectedLanguage={selectedLanguage}
        onSelectLanguage={setSelectedLanguage}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-5xl w-full mx-auto p-3 sm:p-5">
        {/* Screen A: Home Dashboard */}
        {activeTab === "home" && (
          <HomeScreen
            setActiveTab={setActiveTab}
            isOnline={isOnline}
            onOpenAskWithQuery={handleOpenAskWithQuery}
          />
        )}

        {/* Screen B: Ask Sakhi (Unified Search) */}
        {activeTab === "ask" && (
          <AskScreen
            pipelineTS={pipelineTS}
            isOnline={isOnline}
            initialQuery={askQuery}
            setActiveTab={setActiveTab}
            selectedLanguage={selectedLanguage}
            onSelectLanguage={setSelectedLanguage}
          />
        )}

        {/* Screen C: Households Register */}
        {activeTab === "households" && (
          <HouseholdsScreen onStartVisit={handleStartVisitForHousehold} />
        )}

        {/* Screen E: Visit Planner */}
        {activeTab === "visits" && (
          <VisitsScreen
            initialHouseholdId={visitTargetHouseholdId}
            onVisitCompleted={refreshCounts}
          />
        )}

        {/* Screen F: Emergency Desk */}
        {activeTab === "emergency" && <EmergencyScreen />}

        {/* Screen G: Settings & System Status */}
        {activeTab === "settings" && (
          <StatusScreen
            isOnline={isOnline}
            setIsOnline={setIsOnline}
            selectedLanguage={selectedLanguage}
            onSelectLanguage={setSelectedLanguage}
            pipelineTS={pipelineTS}
          />
        )}
      </main>

      {/* Emergency Sticky Footer Ribbon */}
      <footer className="bg-slate-900 text-slate-400 text-xs py-2 px-4 border-t border-slate-800 text-center z-30">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-1">
          <span>
            🚨 Medical Emergency: <strong>Dial 108 (Ambulance)</strong> • 102 (Maternal) • PHC Venkatapuram
          </span>
          <span className="font-mono text-teal-400 text-[11px]">
            SyncPulse • 100% Offline MoHFW Clinical Intelligence
          </span>
        </div>
      </footer>
    </div>
  );
};

export default App;
