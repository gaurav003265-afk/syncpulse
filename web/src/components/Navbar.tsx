import React, { useState } from "react";
import {
  Home,
  MessageSquare,
  Users,
  Calendar,
  AlertTriangle,
  Activity,
  Wifi,
  WifiOff,
  Globe,
  UserCheck,
} from "lucide-react";

export type NavTab = "home" | "ask" | "households" | "visits" | "emergency" | "settings";

interface NavbarProps {
  activeTab: NavTab;
  setActiveTab: (tab: NavTab) => void;
  isOnline: boolean;
  setIsOnline: (online: boolean) => void;
  pendingSyncCount: number;
  criticalAlertCount: number;
  selectedLanguage: "en" | "te" | "hi";
  onSelectLanguage: (lang: "en" | "te" | "hi") => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  isOnline,
  setIsOnline,
  pendingSyncCount,
  criticalAlertCount,
  selectedLanguage,
  onSelectLanguage,
}) => {
  const [showLangMenu, setShowLangMenu] = useState(false);

  const navItems: Array<{ id: NavTab; label: string; icon: React.ReactNode; badge?: number; alertBadge?: boolean }> = [
    { id: "home", label: "Home", icon: <Home className="w-4 h-4 sm:w-4.5 sm:h-4.5" /> },
    { id: "ask", label: "Ask Sakhi", icon: <MessageSquare className="w-4 h-4 sm:w-4.5 sm:h-4.5" /> },
    { id: "households", label: "Households", icon: <Users className="w-4 h-4 sm:w-4.5 sm:h-4.5" /> },
    { id: "visits", label: "Visit Planner", icon: <Calendar className="w-4 h-4 sm:w-4.5 sm:h-4.5" /> },
    {
      id: "emergency",
      label: "Emergency",
      icon: <AlertTriangle className="w-4 h-4 sm:w-4.5 sm:h-4.5" />,
      badge: criticalAlertCount > 0 ? criticalAlertCount : undefined,
      alertBadge: true,
    },
    {
      id: "settings",
      label: "Status",
      icon: <Activity className="w-4 h-4 sm:w-4.5 sm:h-4.5" />,
      badge: pendingSyncCount > 0 ? pendingSyncCount : undefined,
    },
  ];

  return (
    <>
      {/* Top Main App Header */}
      <header className="bg-teal-900 text-white shadow-md sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-3 sm:px-5 py-2.5 flex items-center justify-between gap-2">
          {/* Brand Identity */}
          <div className="flex items-center space-x-2.5 cursor-pointer" onClick={() => setActiveTab("home")}>
            <div className="bg-teal-700 text-teal-100 font-black rounded-lg w-9 h-9 flex items-center justify-center text-sm shadow-inner border border-teal-500/30">
              SP
            </div>
            <div>
              <div className="flex items-center space-x-1.5">
                <span className="text-base sm:text-lg font-bold tracking-tight text-white leading-none">
                  SyncPulse
                </span>
                <span className="bg-teal-800 text-teal-200 text-[10px] font-semibold px-1.5 py-0.5 rounded border border-teal-700">
                  v2.0
                </span>
              </div>
              <p className="text-[11px] text-teal-200 font-medium leading-tight hidden xs:block">
                ASHA Clinical Companion • MoHFW Protocols
              </p>
            </div>
          </div>

          {/* Right Action Controls: Worker Info, Language, Network Pill */}
          <div className="flex items-center space-x-2">
            {/* Language Switcher */}
            <div className="relative">
              <button
                onClick={() => setShowLangMenu(!showLangMenu)}
                className="flex items-center space-x-1 text-xs font-semibold bg-teal-800/80 hover:bg-teal-800 text-teal-100 px-2 py-1.5 rounded-md border border-teal-700 transition"
                title="Change Language"
                aria-label="Select Language"
              >
                <Globe className="w-3.5 h-3.5 text-teal-300" />
                <span className="uppercase text-[11px] font-bold">
                  {selectedLanguage === "en" ? "EN" : selectedLanguage === "te" ? "తెలుగు" : "हिंदी"}
                </span>
              </button>

              {showLangMenu && (
                <div className="absolute right-0 mt-1 w-32 bg-white rounded-md shadow-lg py-1 border border-slate-200 z-50 text-slate-800 text-xs">
                  <button
                    onClick={() => {
                      onSelectLanguage("en");
                      setShowLangMenu(false);
                    }}
                    className={`w-full text-left px-3 py-1.5 hover:bg-slate-100 ${
                      selectedLanguage === "en" ? "font-bold text-teal-700 bg-teal-50" : ""
                    }`}
                  >
                    English (EN)
                  </button>
                  <button
                    onClick={() => {
                      onSelectLanguage("te");
                      setShowLangMenu(false);
                    }}
                    className={`w-full text-left px-3 py-1.5 hover:bg-slate-100 ${
                      selectedLanguage === "te" ? "font-bold text-teal-700 bg-teal-50" : ""
                    }`}
                  >
                    తెలుగు (Telugu)
                  </button>
                  <button
                    onClick={() => {
                      onSelectLanguage("hi");
                      setShowLangMenu(false);
                    }}
                    className={`w-full text-left px-3 py-1.5 hover:bg-slate-100 ${
                      selectedLanguage === "hi" ? "font-bold text-teal-700 bg-teal-50" : ""
                    }`}
                  >
                    हिंदी (Hindi)
                  </button>
                </div>
              )}
            </div>

            {/* Offline / Online Pill with manual toggle for demonstration */}
            <button
              onClick={() => setIsOnline(!isOnline)}
              className={`flex items-center space-x-1.5 text-xs font-semibold px-2.5 py-1.5 rounded-full border transition cursor-pointer shadow-sm ${
                isOnline
                  ? "bg-emerald-950/80 text-emerald-300 border-emerald-600/60 hover:bg-emerald-900"
                  : "bg-amber-950/90 text-amber-200 border-amber-600/70 hover:bg-amber-900"
              }`}
              title="Click to simulate network disconnect/reconnect for field testing"
            >
              {isOnline ? (
                <>
                  <Wifi className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="hidden md:inline font-mono text-[11px]">Online</span>
                </>
              ) : (
                <>
                  <WifiOff className="w-3.5 h-3.5 text-amber-400" />
                  <span className="font-mono text-[11px]">100% Offline</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Desktop / Tablet Nav Tabs Bar */}
        <nav className="hidden sm:flex bg-teal-950 border-t border-teal-800/80 px-4">
          <div className="max-w-6xl mx-auto w-full flex justify-between">
            {navItems.map((item) => {
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`flex items-center space-x-2 py-3 px-3 text-xs md:text-sm font-medium border-b-2 transition-all ${
                    isActive
                      ? "border-teal-400 text-teal-200 font-bold bg-teal-900/40"
                      : "border-transparent text-teal-300/80 hover:text-white hover:bg-teal-900/20"
                  }`}
                >
                  {item.icon}
                  <span>{item.label}</span>
                  {item.badge !== undefined && (
                    <span
                      className={`text-[10px] font-bold px-1.5 py-0.2 rounded-full ${
                        item.alertBadge
                          ? "bg-red-600 text-white animate-pulse"
                          : "bg-amber-500 text-slate-900"
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </nav>
      </header>

      {/* Mobile Bottom Fixed Navigation Bar */}
      <nav className="sm:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-slate-200 z-50 shadow-lg pb-safe">
        <div className="grid grid-cols-6 h-14">
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex flex-col items-center justify-center relative transition-colors ${
                  isActive ? "text-teal-700 font-bold" : "text-slate-500 hover:text-slate-800"
                }`}
                aria-label={item.label}
              >
                {item.icon}
                <span className="text-[10px] tracking-tight mt-0.5 truncate max-w-[50px] leading-none">
                  {item.label.split(" ")[0]}
                </span>
                {item.badge !== undefined && (
                  <span
                    className={`absolute top-1 right-2 text-[9px] font-extrabold w-4 h-4 flex items-center justify-center rounded-full ${
                      item.alertBadge
                        ? "bg-red-600 text-white animate-pulse"
                        : "bg-amber-500 text-slate-900"
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
                {isActive && (
                  <span className="absolute bottom-0 w-8 h-0.5 bg-teal-700 rounded-t-full" />
                )}
              </button>
            );
          })}
        </div>
      </nav>
    </>
  );
};
