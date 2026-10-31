import React, { useState, useEffect, lazy, Suspense } from "react";
import { Navbar, NavTab } from "./components/Navbar";
import { HomeScreen } from "./components/HomeScreen";
import { AskScreen } from "./components/AskScreen";
import { PipelineTS } from "./engine/pipeline";
import { dataService } from "./engine/dataService";

// Safe PWA Code-Splitting: Lazy load secondary screens with 2D skeleton fallback
const HouseholdsScreen = lazy(() =>
  import("./components/HouseholdsScreen").then((m) => ({ default: m.HouseholdsScreen }))
);
const VisitsScreen = lazy(() =>
  import("./components/VisitsScreen").then((m) => ({ default: m.VisitsScreen }))
);
const EmergencyScreen = lazy(() =>
  import("./components/EmergencyScreen").then((m) => ({ default: m.EmergencyScreen }))
);
const StatusScreen = lazy(() =>
  import("./components/StatusScreen").then((m) => ({ default: m.StatusScreen }))
);

// Clean 2D Screen Loading Skeleton
const ScreenSkeleton: React.FC = () => (
  <div className="space-y-4 p-4 animate-pulse">
    <div className="h-8 bg-slate-200 rounded-xl w-1/3"></div>
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <div className="h-24 bg-slate-200 rounded-xl"></div>
      <div className="h-24 bg-slate-200 rounded-xl"></div>
    </div>
    <div className="h-44 bg-slate-200 rounded-xl"></div>
  </div>
);

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

    // Offline PWA Guarantee: Pre-warm lazy chunks during browser idle so all screens are cached offline
    const prewarmIdle = () => {
      import("./components/HouseholdsScreen");
      import("./components/VisitsScreen");
      import("./components/EmergencyScreen");
      import("./components/StatusScreen");
    };
    if (typeof window !== "undefined") {
      if ("requestIdleCallback" in window) {
        (window as any).requestIdleCallback(prewarmIdle);
      } else {
        setTimeout(prewarmIdle, 1500);
      }
    }

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
      <main className="flex-1 max-w-5xl w-full mx-auto p-3 sm:p-5 pb-24 md:pb-8">
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
          <Suspense fallback={<ScreenSkeleton />}>
            <HouseholdsScreen onStartVisit={handleStartVisitForHousehold} />
          </Suspense>
        )}

        {/* Screen E: Visit Planner */}
        {activeTab === "visits" && (
          <Suspense fallback={<ScreenSkeleton />}>
            <VisitsScreen
              initialHouseholdId={visitTargetHouseholdId}
              onVisitCompleted={refreshCounts}
            />
          </Suspense>
        )}

        {/* Screen F: Emergency Desk */}
        {activeTab === "emergency" && (
          <Suspense fallback={<ScreenSkeleton />}>
            <EmergencyScreen />
          </Suspense>
        )}

        {/* Screen G: Settings & System Status */}
        {activeTab === "settings" && (
          <Suspense fallback={<ScreenSkeleton />}>
            <StatusScreen
              isOnline={isOnline}
              setIsOnline={setIsOnline}
              selectedLanguage={selectedLanguage}
              onSelectLanguage={setSelectedLanguage}
              pipelineTS={pipelineTS}
            />
          </Suspense>
        )}
      </main>

      {/* Emergency Sticky Footer Ribbon */}
      <footer className="bg-slate-900 text-slate-400 text-xs py-2 px-4 border-t border-slate-800 text-center z-30 mb-14 md:mb-0">
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
