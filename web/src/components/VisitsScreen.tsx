import React, { useState, useEffect, useMemo } from "react";
import {
  Calendar,
  Clock,
  AlertTriangle,
  CheckCircle2,
  Phone,
  Home,
  MapPin,
  ClipboardList,
  HeartPulse,
  Save,
  X,
  Filter,
  Info,
  Navigation,
  Crosshair,
  Compass,
  Check,
  Edit2,
  List,
  Map,
  BellRing,
  AlertCircle,
  RotateCcw,
} from "lucide-react";
import { dataService, HouseholdRecord } from "../engine/dataService";
import {
  captureWorkerLocation,
  CoordinatesTS,
  formatDistanceLabel,
  haversineDistanceKm,
  isValidCoordinate,
} from "../engine/location";
import { FollowUpGapTS, MonthlyReminderTS } from "../engine/reminders";
import { PatientDetailModal } from "./PatientDetailModal";

interface VisitsScreenProps {
  initialHouseholdId?: string | null;
  onVisitCompleted?: () => void;
}

type FilterTab =
  | "all"
  | "today"
  | "overdue"
  | "upcoming"
  | "follow_ups"
  | "reminders"
  | "completed";

type ViewMode = "list" | "radar_map";

export const VisitsScreen: React.FC<VisitsScreenProps> = ({
  initialHouseholdId,
  onVisitCompleted,
}) => {
  const [selectedVillage, setSelectedVillage] = useState("All");
  const [filterTab, setFilterTab] = useState<FilterTab>("all");
  const [viewMode, setViewMode] = useState<ViewMode>("list");

  // Worker Location State (Part A & B)
  const [workerCoords, setWorkerCoords] = useState<CoordinatesTS | null>(null);
  const [capturingWorkerGps, setCapturingWorkerGps] = useState(false);
  const [gpsNotice, setGpsNotice] = useState<string | null>(null);

  // Selected household for view/modal
  const [detailHousehold, setDetailHousehold] = useState<HouseholdRecord | null>(null);

  // Household Location Capture / Correction Modal (Part A)
  const [locationModalHousehold, setLocationModalHousehold] = useState<HouseholdRecord | null>(null);
  const [editLat, setEditLat] = useState("");
  const [editLon, setEditLon] = useState("");
  const [locationFeedback, setLocationFeedback] = useState<string | null>(null);

  // Conduct Visit Modal
  const [activeVisitModal, setActiveVisitModal] = useState<HouseholdRecord | null>(null);
  const [bpSystolic, setBpSystolic] = useState("");
  const [bpDiastolic, setBpDiastolic] = useState("");
  const [pulse, setPulse] = useState("");
  const [temp, setTemp] = useState("");
  const [weight, setWeight] = useState("");
  const [muac, setMuac] = useState("");
  const [notes, setNotes] = useState("");
  const [followUpDate, setFollowUpDate] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Follow-up completion modal (Part F)
  const [followUpToComplete, setFollowUpToComplete] = useState<FollowUpGapTS | null>(null);
  const [followUpNotes, setFollowUpNotes] = useState("");

  const villages = useMemo(() => ["All", ...dataService.getVillages()], []);

  // Fetch scored visits with location awareness and secondary tie-breaking
  const scoredVisits = useMemo(() => {
    return dataService.getScoredVisits(
      "2026-10-20",
      selectedVillage,
      filterTab === "follow_ups" || filterTab === "reminders" ? "all" : filterTab,
      workerCoords ? { latitude: workerCoords.latitude, longitude: workerCoords.longitude } : null
    );
  }, [selectedVillage, filterTab, workerCoords]);

  // Fetch monthly reminders (Part E)
  const monthlyReminders = useMemo(() => {
    if (filterTab !== "reminders") return [];
    const all = dataService.getMonthlyReminders("2026-10-20");
    if (selectedVillage === "All") return all;
    return all.filter((r) => r.village.toLowerCase() === selectedVillage.toLowerCase());
  }, [filterTab, selectedVillage]);

  // Fetch follow-up gaps (Part F)
  const followUpGaps = useMemo(() => {
    if (filterTab !== "follow_ups") return [];
    const all = dataService.getFollowUpGaps("2026-10-20");
    if (selectedVillage === "All") return all;
    return all.filter((g) => g.village.toLowerCase() === selectedVillage.toLowerCase());
  }, [filterTab, selectedVillage]);

  useEffect(() => {
    if (initialHouseholdId) {
      const target = dataService.getHouseholdById(initialHouseholdId);
      if (target) {
        setActiveVisitModal(target);
      }
    }
  }, [initialHouseholdId]);

  // Worker GPS capture handler
  const handleCaptureWorkerGps = () => {
    setCapturingWorkerGps(true);
    setGpsNotice(null);

    captureWorkerLocation(
      (coords) => {
        setWorkerCoords(coords);
        setCapturingWorkerGps(false);
        setGpsNotice(`Worker GPS active: ${coords.latitude.toFixed(4)}° N, ${coords.longitude.toFixed(4)}° E (±${coords.accuracy_m || 10}m)`);
      },
      (status, message) => {
        setCapturingWorkerGps(false);
        setGpsNotice(`${message}`);
      }
    );
  };

  // Preset location helper for field simulation (e.g. Sub-Center HQ)
  const handleSetSubCenterLocation = () => {
    const subCenterCoords: CoordinatesTS = {
      latitude: 16.5062,
      longitude: 80.648,
      accuracy_m: 5.0,
      source: "MANUAL_ENTRY",
      captured_at: new Date().toISOString(),
    };
    setWorkerCoords(subCenterCoords);
    setGpsNotice("Worker position set to Venkatapuram Sub-Center HQ (16.5062° N, 80.6480° E)");
  };

  const handleClearWorkerGps = () => {
    setWorkerCoords(null);
    setGpsNotice("Worker location cleared. Straight-line distances are now marked unavailable.");
  };

  // Open household location edit modal
  const handleOpenLocationModal = (h: HouseholdRecord) => {
    setLocationModalHousehold(h);
    setEditLat(h.latitude !== undefined && h.latitude !== null ? h.latitude.toString() : "");
    setEditLon(h.longitude !== undefined && h.longitude !== null ? h.longitude.toString() : "");
    setLocationFeedback(null);
  };

  const handleCaptureGpsForHousehold = () => {
    setLocationFeedback("Requesting device GPS sensor...");
    captureWorkerLocation(
      (coords) => {
        setEditLat(coords.latitude.toString());
        setEditLon(coords.longitude.toString());
        setLocationFeedback(`Captured: ${coords.latitude.toFixed(5)}, ${coords.longitude.toFixed(5)} (±${coords.accuracy_m || 10}m)`);
      },
      (status, message) => {
        setLocationFeedback(message);
      }
    );
  };

  const handleSaveHouseholdLocation = (e: React.FormEvent) => {
    e.preventDefault();
    if (!locationModalHousehold) return;

    const lat = parseFloat(editLat);
    const lon = parseFloat(editLon);

    if (!isValidCoordinate(lat, lon)) {
      setLocationFeedback("Error: Latitude must be between -90 and 90; Longitude between -180 and 180.");
      return;
    }

    const success = dataService.updateHouseholdLocation(
      locationModalHousehold.household_id,
      lat,
      lon,
      editLat === workerCoords?.latitude.toString() ? "GPS_CAPTURE" : "MANUAL_ENTRY",
      10.0
    );

    if (success) {
      setToastMessage(`✓ GPS Coordinates saved for ${locationModalHousehold.household_id} (${lat.toFixed(4)}, ${lon.toFixed(4)}).`);
      setTimeout(() => setToastMessage(null), 4000);
      setLocationModalHousehold(null);
    }
  };

  const handleOpenVisitModal = (h: HouseholdRecord) => {
    setActiveVisitModal(h);
    setBpSystolic("");
    setBpDiastolic("");
    setPulse("");
    setTemp("");
    setWeight("");
    setMuac("");
    setNotes(h.visit_notes || "");
    setFollowUpDate("");
  };

  const handleCompleteVisitSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeVisitModal) return;

    setSubmitting(true);
    let bpStr = undefined;
    if (bpSystolic || bpDiastolic) {
      bpStr = `${bpSystolic || "120"}/${bpDiastolic || "80"} mmHg`;
    }

    const vitals = {
      bp: bpStr,
      pulse: pulse ? `${pulse} bpm` : undefined,
      temp: temp ? `${temp}°F` : undefined,
      weight: weight ? weight : undefined,
      muac: muac ? muac : undefined,
    };

    dataService.markVisitCompleted(
      activeVisitModal.household_id,
      notes,
      vitals,
      followUpDate || undefined
    );

    setSubmitting(false);
    setActiveVisitModal(null);
    setToastMessage(`✓ Visit for ${activeVisitModal.beneficiary_name} saved to local offline register.`);
    setTimeout(() => setToastMessage(null), 4000);

    if (onVisitCompleted) {
      onVisitCompleted();
    }
  };

  const handleCompleteFollowUpSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!followUpToComplete) return;

    dataService.completeFollowUpTask(followUpToComplete.follow_up_id, followUpNotes);
    setFollowUpToComplete(null);
    setFollowUpNotes("");
    setToastMessage(`✓ Follow-up marked as completed in local database.`);
    setTimeout(() => setToastMessage(null), 4000);
  };

  // Households with valid coordinates for spatial radar
  const mappedHouseholds = useMemo(() => {
    return scoredVisits.filter((h) => isValidCoordinate(h.latitude, h.longitude));
  }, [scoredVisits]);

  return (
    <div className="space-y-4 pb-16 sm:pb-6">
      {/* Screen Header */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center space-x-2">
            <Calendar className="w-5 h-5 text-teal-700" />
            <h2 className="text-base font-bold text-slate-900">
              Location-Aware Field Visit Planner
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            4-Tier clinical triage: High-Risk danger alerts strictly outrank distance. Straight-line distance serves as secondary convenience.
          </p>
        </div>

        {/* View Mode & Village Filters */}
        <div className="flex flex-wrap items-center gap-2">
          {/* View Mode Toggle (Part D) */}
          <div className="flex items-center bg-slate-100 p-1 rounded-lg border border-slate-200 text-xs font-semibold">
            <button
              onClick={() => setViewMode("list")}
              className={`flex items-center space-x-1 px-2.5 py-1 rounded transition ${
                viewMode === "list" ? "bg-white text-teal-900 shadow-xs" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <List className="w-3.5 h-3.5" />
              <span>List</span>
            </button>
            <button
              onClick={() => setViewMode("radar_map")}
              className={`flex items-center space-x-1 px-2.5 py-1 rounded transition ${
                viewMode === "radar_map" ? "bg-teal-700 text-white shadow-xs" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <Compass className="w-3.5 h-3.5" />
              <span>Spatial Radar</span>
            </button>
          </div>

          {/* Village Filter */}
          <div className="flex items-center space-x-1.5">
            <label className="text-xs font-semibold text-slate-500">Village:</label>
            <select
              value={selectedVillage}
              onChange={(e) => setSelectedVillage(e.target.value)}
              className="bg-slate-50 border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs font-medium text-slate-800"
            >
              {villages.map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Worker Location Bar (Part A & B) */}
      <div className="bg-white border border-teal-200/80 rounded-xl p-3.5 shadow-xs space-y-2">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
          <div className="flex items-center space-x-2 text-xs">
            <div className={`p-1.5 rounded-lg ${workerCoords ? "bg-teal-100 text-teal-800" : "bg-slate-100 text-slate-500"}`}>
              <Navigation className="w-4 h-4" />
            </div>
            <div>
              <div className="font-bold text-slate-800 flex items-center space-x-1.5">
                <span>Worker Position:</span>
                {workerCoords ? (
                  <span className="text-teal-700 font-mono text-[11px] bg-teal-50 px-2 py-0.5 rounded border border-teal-200">
                    {workerCoords.latitude.toFixed(4)}° N, {workerCoords.longitude.toFixed(4)}° E
                    {workerCoords.accuracy_m ? ` (±${workerCoords.accuracy_m}m)` : ""}
                  </span>
                ) : (
                  <span className="text-slate-400 font-normal italic">
                    Location inactive (Straight-line distance unavailable)
                  </span>
                )}
              </div>
              <p className="text-[11px] text-slate-500">
                Formula: Haversine (R = 6371 km). Strictly straight-line distance; never road routes or travel time.
              </p>
            </div>
          </div>

          {/* Location Actions */}
          <div className="flex items-center space-x-1.5 self-start sm:self-auto">
            <button
              onClick={handleCaptureWorkerGps}
              disabled={capturingWorkerGps}
              className="bg-teal-700 hover:bg-teal-800 text-white font-semibold px-2.5 py-1.5 rounded-lg text-xs flex items-center space-x-1 transition shadow-xs"
            >
              <Crosshair className={`w-3.5 h-3.5 ${capturingWorkerGps ? "animate-spin" : ""}`} />
              <span>{capturingWorkerGps ? "Acquiring..." : "Capture GPS"}</span>
            </button>
            <button
              onClick={handleSetSubCenterLocation}
              className="bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold px-2.5 py-1.5 rounded-lg text-xs transition"
              title="Set to Sub-Center HQ for testing Haversine distance"
            >
              Sub-Center Preset
            </button>
            {workerCoords && (
              <button
                onClick={handleClearWorkerGps}
                className="text-slate-400 hover:text-red-600 p-1.5 rounded-lg transition"
                title="Clear worker position"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {gpsNotice && (
          <div className="text-[11px] bg-slate-50 p-2 rounded-lg border border-slate-200 text-slate-600 flex items-center space-x-1.5">
            <Info className="w-3.5 h-3.5 text-teal-600 shrink-0" />
            <span>{gpsNotice}</span>
          </div>
        )}
      </div>

      {/* Toast Notification */}
      {toastMessage && (
        <div className="p-3 bg-emerald-50 border border-emerald-300 text-emerald-900 rounded-xl text-xs font-semibold flex items-center space-x-2 shadow-xs">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Filter Tabs (Part C, E, F) */}
      <div className="flex flex-wrap gap-1.5 bg-white p-1.5 rounded-xl border border-slate-200 text-xs font-semibold">
        <button
          onClick={() => setFilterTab("all")}
          className={`px-3 py-1.5 rounded-lg transition ${
            filterTab === "all" ? "bg-teal-700 text-white shadow-xs" : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          All Prioritized
        </button>
        <button
          onClick={() => setFilterTab("today")}
          className={`px-3 py-1.5 rounded-lg transition ${
            filterTab === "today" ? "bg-teal-700 text-white shadow-xs" : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          Due Today
        </button>
        <button
          onClick={() => setFilterTab("overdue")}
          className={`px-3 py-1.5 rounded-lg transition ${
            filterTab === "overdue" ? "bg-amber-600 text-white shadow-xs" : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          Overdue
        </button>
        <button
          onClick={() => setFilterTab("upcoming")}
          className={`px-3 py-1.5 rounded-lg transition ${
            filterTab === "upcoming" ? "bg-teal-700 text-white shadow-xs" : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          Upcoming
        </button>
        <button
          onClick={() => setFilterTab("follow_ups")}
          className={`px-3 py-1.5 rounded-lg transition flex items-center space-x-1 ${
            filterTab === "follow_ups" ? "bg-rose-700 text-white shadow-xs" : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          <ClipboardList className="w-3.5 h-3.5" />
          <span>Follow-Up Gaps</span>
        </button>
        <button
          onClick={() => setFilterTab("reminders")}
          className={`px-3 py-1.5 rounded-lg transition flex items-center space-x-1 ${
            filterTab === "reminders" ? "bg-indigo-700 text-white shadow-xs" : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          <BellRing className="w-3.5 h-3.5" />
          <span>Monthly Reminders</span>
        </button>
        <button
          onClick={() => setFilterTab("completed")}
          className={`px-3 py-1.5 rounded-lg transition ${
            filterTab === "completed" ? "bg-emerald-700 text-white shadow-xs" : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          Completed
        </button>
      </div>

      {/* VIEW MODE 1: SPATIAL RADAR / LOCAL COORDINATE PLOT (Part D) */}
      {viewMode === "radar_map" && filterTab !== "follow_ups" && filterTab !== "reminders" && (
        <div className="bg-white rounded-2xl border border-slate-200 p-5 space-y-4 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-1.5">
                <Compass className="w-4 h-4 text-teal-700" />
                <span>Schematic Proximity Radar (Local Coordinate Plot)</span>
              </h3>
              <p className="text-xs text-slate-500">
                Visualizing {mappedHouseholds.length} households with recorded coordinates relative to worker position.
              </p>
            </div>
            <div className="text-[11px] text-slate-500 font-medium bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-200">
              Unmapped in Register: {scoredVisits.length - mappedHouseholds.length}
            </div>
          </div>

          {/* Honest Offline Map Disclosure Callout (Part D Requirement) */}
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-xs text-amber-900 space-y-1">
            <span className="font-bold flex items-center space-x-1.5">
              <Info className="w-3.5 h-3.5 text-amber-700" />
              <span>Offline Mapping Architecture Reality:</span>
            </span>
            <p className="text-[11px] leading-relaxed text-amber-800">
              Online map tiles (Google Maps / Mapbox) and driving route calculations are intentionally disabled offline to maintain zero-network reliability. This local schematic radar plots straight-line spatial distribution for households whose GPS coordinates have been verified or recorded. It does NOT pretend road paths or travel times were calculated.
            </p>
          </div>

          {/* SVG Schematic Radar Visualization */}
          <div className="relative w-full aspect-square max-w-md mx-auto bg-slate-900 rounded-2xl p-4 flex items-center justify-center overflow-hidden shadow-inner">
            <svg viewBox="0 0 400 400" className="w-full h-full">
              {/* Radar concentric range rings */}
              <circle cx="200" cy="200" r="160" fill="none" stroke="#334155" strokeWidth="1" strokeDasharray="3 3" />
              <circle cx="200" cy="200" r="110" fill="none" stroke="#334155" strokeWidth="1" strokeDasharray="3 3" />
              <circle cx="200" cy="200" r="60" fill="none" stroke="#334155" strokeWidth="1" strokeDasharray="3 3" />
              {/* Crosshairs */}
              <line x1="200" y1="20" x2="200" y2="380" stroke="#1e293b" strokeWidth="1" />
              <line x1="20" y1="200" x2="380" y2="200" stroke="#1e293b" strokeWidth="1" />

              {/* Range ring distance labels */}
              <text x="205" y="145" fill="#64748b" fontSize="9" fontFamily="monospace">1.0 km</text>
              <text x="205" y="95" fill="#64748b" fontSize="9" fontFamily="monospace">2.5 km</text>
              <text x="205" y="45" fill="#64748b" fontSize="9" fontFamily="monospace">5.0 km</text>

              {/* Worker center pin */}
              <circle cx="200" cy="200" r="7" fill="#0d9488" className="animate-pulse" />
              <circle cx="200" cy="200" r="3" fill="#ffffff" />
              <text x="200" y="218" textAnchor="middle" fill="#2dd4bf" fontSize="10" fontWeight="bold">
                Worker (You)
              </text>

              {/* Household plotted points */}
              {mappedHouseholds.map((h) => {
                const centerLat = workerCoords ? workerCoords.latitude : 16.5062;
                const centerLon = workerCoords ? workerCoords.longitude : 80.648;
                const dLat = (h.latitude! - centerLat) * 111.0; // approx km
                const dLon = (h.longitude! - centerLon) * 111.0 * Math.cos((centerLat * Math.PI) / 180);

                // Scale: 30 px per km
                const scale = 28;
                const cx = Math.max(25, Math.min(375, 200 + dLon * scale));
                const cy = Math.max(25, Math.min(375, 200 - dLat * scale));

                const isCritical = h.priority_tier === "TIER_1_CRITICAL";
                const isOverdue = h.priority_tier === "TIER_2_OVERDUE";
                const color = isCritical ? "#ef4444" : isOverdue ? "#f59e0b" : "#10b981";

                return (
                  <g
                    key={h.household_id}
                    className="cursor-pointer group"
                    onClick={() => handleOpenLocationModal(h)}
                  >
                    <circle cx={cx} cy={cy} r="6" fill={color} stroke="#0f172a" strokeWidth="1.5" />
                    <text
                      x={cx}
                      y={cy - 9}
                      textAnchor="middle"
                      fill="#e2e8f0"
                      fontSize="9"
                      fontWeight="bold"
                      className="opacity-80 group-hover:opacity-100"
                    >
                      {h.household_id}
                    </text>
                  </g>
                );
              })}
            </svg>

            {/* Radar Legend */}
            <div className="absolute bottom-2 left-2 right-2 bg-slate-900/80 backdrop-blur-xs p-2 rounded-lg flex items-center justify-between text-[10px] text-slate-300">
              <div className="flex items-center space-x-3">
                <span className="flex items-center space-x-1">
                  <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
                  <span>Tier 1 Critical</span>
                </span>
                <span className="flex items-center space-x-1">
                  <span className="w-2 h-2 rounded-full bg-amber-500 inline-block" />
                  <span>Tier 2 Overdue</span>
                </span>
                <span className="flex items-center space-x-1">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />
                  <span>Routine</span>
                </span>
              </div>
              <span className="text-slate-400">Tap pin to edit GPS</span>
            </div>
          </div>

          {/* Unmapped households note */}
          {scoredVisits.length > mappedHouseholds.length && (
            <div className="text-center py-2 text-xs text-slate-500">
              {scoredVisits.length - mappedHouseholds.length} households in this list do not yet have recorded GPS coordinates. Tap <strong>"Record GPS"</strong> on any household card in List View during your visit.
            </div>
          )}
        </div>
      )}

      {/* VIEW MODE 2: FOLLOW-UP GAP DETECTOR LIST (Part F) */}
      {filterTab === "follow_ups" && (
        <div className="space-y-3">
          <div className="bg-rose-50 border border-rose-200 rounded-xl p-3.5 text-xs text-rose-950 flex items-start space-x-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold">Follow-Up Gap Detector:</span>
              <p className="text-[11px] text-rose-800 leading-relaxed mt-0.5">
                Identifies recorded clinical follow-up tasks from previous visits whose due dates have passed. Every task is grounded in actual local visit outcomes without invented clinical advice.
              </p>
            </div>
          </div>

          {followUpGaps.length === 0 ? (
            <div className="bg-white rounded-xl border border-slate-200 p-8 text-center space-y-2">
              <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto" />
              <h3 className="text-sm font-bold text-slate-800">No overdue follow-up gaps detected</h3>
              <p className="text-xs text-slate-500">All recorded follow-up tasks are completed or within scheduled due dates.</p>
            </div>
          ) : (
            <div className="space-y-2.5">
              {followUpGaps.map((gap) => (
                <div
                  key={gap.follow_up_id}
                  className="bg-white border border-rose-200 rounded-xl p-4 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:border-rose-400 transition"
                >
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="bg-rose-100 text-rose-800 text-[10px] font-bold px-2 py-0.5 rounded uppercase">
                        {gap.status === "OVERDUE_GAP" ? `Overdue ${gap.overdue_days} Days` : "Due Today"}
                      </span>
                      <span className="font-bold text-xs text-slate-800">{gap.household_id}</span>
                      <span className="text-xs text-slate-500">({gap.village})</span>
                    </div>
                    <h4 className="text-sm font-bold text-slate-900">{gap.task_description}</h4>
                    <p className="text-xs text-slate-600">
                      Beneficiary: <strong>{gap.beneficiary_name}</strong> • Scheduled Due Date: <span className="font-mono">{gap.due_date}</span>
                    </p>
                    <p className="text-[11px] text-rose-700 italic">{gap.explanation}</p>
                  </div>

                  <button
                    onClick={() => {
                      setFollowUpToComplete(gap);
                      setFollowUpNotes("");
                    }}
                    className="bg-teal-700 hover:bg-teal-800 text-white font-bold py-1.5 px-3.5 rounded-xl text-xs flex items-center justify-center space-x-1 transition shadow-xs shrink-0"
                  >
                    <Check className="w-3.5 h-3.5" />
                    <span>Complete Follow-Up</span>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* VIEW MODE 3: MONTHLY REMINDERS LIST (Part E) */}
      {filterTab === "reminders" && (
        <div className="space-y-3">
          <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-3.5 text-xs text-indigo-950 flex items-start space-x-2">
            <BellRing className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold">Monthly Service Reminders (MoHFW Approved Schedules):</span>
              <p className="text-[11px] text-indigo-800 leading-relaxed mt-0.5">
                Reminders generated deterministically from maternal ANC schedules, infant immunization dates, and NCD adult screenings. Stored strictly on-device (zero fabricated cloud push delivery).
              </p>
            </div>
          </div>

          <div className="space-y-2.5">
            {monthlyReminders.slice(0, 30).map((rem) => {
              const isOverdue = rem.status === "OVERDUE";
              const isThisMonth = rem.status === "DUE_THIS_MONTH";
              const isDone = rem.status === "COMPLETED";

              return (
                <div
                  key={rem.reminder_id}
                  className={`bg-white border rounded-xl p-4 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition ${
                    isDone
                      ? "border-emerald-200 bg-emerald-50/20"
                      : isOverdue
                      ? "border-amber-300 bg-amber-50/20"
                      : "border-slate-200"
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                          isDone
                            ? "bg-emerald-100 text-emerald-800"
                            : isOverdue
                            ? "bg-amber-100 text-amber-800"
                            : isThisMonth
                            ? "bg-indigo-100 text-indigo-800"
                            : "bg-slate-100 text-slate-700"
                        }`}
                      >
                        {isDone
                          ? "Completed"
                          : isOverdue
                          ? `Overdue (${rem.days_diff}d)`
                          : isThisMonth
                          ? "Due This Month"
                          : "Upcoming Next Month"}
                      </span>
                      <span className="font-bold text-xs text-slate-800">{rem.household_id}</span>
                      <span className="text-xs text-slate-500">({rem.village})</span>
                    </div>

                    <h4 className="text-sm font-bold text-slate-900">{rem.service_name}</h4>
                    <p className="text-xs text-slate-600">
                      Beneficiary: <strong>{rem.beneficiary_name}</strong> ({rem.beneficiary_type}) • Due Date: <span className="font-mono">{rem.due_date}</span>
                    </p>
                    <p className="text-[11px] text-slate-500 font-mono">{rem.protocol_citation}</p>
                  </div>

                  <div>
                    {!rem.is_completed && (
                      <button
                        onClick={() => {
                          const h = dataService.getHouseholdById(rem.household_id);
                          if (h) handleOpenVisitModal(h);
                        }}
                        className="bg-teal-700 hover:bg-teal-800 text-white font-bold py-1.5 px-3.5 rounded-xl text-xs flex items-center space-x-1 transition shadow-xs"
                      >
                        <HeartPulse className="w-3.5 h-3.5" />
                        <span>Conduct Visit</span>
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* VIEW MODE 4: STANDARD PRIORITIZED VISIT LIST (Part C) */}
      {viewMode === "list" && filterTab !== "follow_ups" && filterTab !== "reminders" && (
        <div className="space-y-3">
          {scoredVisits.length === 0 ? (
            <div className="bg-white rounded-xl border border-slate-200 p-8 text-center space-y-2">
              <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto" />
              <h3 className="text-sm font-bold text-slate-800">No visits found in this category</h3>
              <p className="text-xs text-slate-500">All scheduled visits for this filter appear up to date!</p>
            </div>
          ) : (
            <div className="space-y-3">
              {scoredVisits.slice(0, 35).map((visit) => {
                const isCritical = visit.priority_tier === "TIER_1_CRITICAL";
                const isOverdue = visit.priority_tier === "TIER_2_OVERDUE";
                const isToday = visit.priority_tier === "TIER_3_DUE_TODAY";
                const hasGps = isValidCoordinate(visit.latitude, visit.longitude);

                return (
                  <div
                    key={visit.household_id}
                    className={`bg-white border rounded-xl p-4 shadow-xs transition space-y-3 ${
                      isCritical
                        ? "border-red-300 bg-red-50/20 hover:border-red-400"
                        : isOverdue
                        ? "border-amber-300 bg-amber-50/20 hover:border-amber-400"
                        : "border-slate-200 hover:border-teal-400"
                    }`}
                  >
                    {/* Header Row: Tier Badge, Household ID, Distance, GPS Status */}
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2.5">
                      <div className="flex items-center space-x-2">
                        <span
                          className={`text-[10px] font-black px-2.5 py-0.5 rounded-full uppercase tracking-wider ${
                            isCritical
                              ? "bg-red-600 text-white animate-pulse"
                              : isOverdue
                              ? "bg-amber-500 text-slate-950 font-bold"
                              : isToday
                              ? "bg-teal-600 text-white"
                              : "bg-slate-200 text-slate-700"
                          }`}
                        >
                          {isCritical
                            ? "🚨 Tier 1: High Risk"
                            : isOverdue
                            ? "⚠️ Tier 2: Overdue"
                            : isToday
                            ? "📅 Tier 3: Due Today"
                            : "Tier 4: Upcoming"}
                        </span>
                        <span className="font-mono text-xs font-bold text-slate-700">
                          {visit.household_id}
                        </span>
                      </div>

                      {/* Distance & GPS indicator (Part B) */}
                      <div className="flex items-center space-x-2 text-xs">
                        <div
                          className={`flex items-center space-x-1 px-2 py-0.5 rounded font-mono text-[11px] ${
                            visit.straight_line_distance_km !== null && visit.straight_line_distance_km !== undefined
                              ? "bg-teal-50 text-teal-800 border border-teal-200"
                              : "bg-slate-50 text-slate-400 border border-slate-200"
                          }`}
                        >
                          <Navigation className="w-3 h-3" />
                          <span>{visit.distance_display || "Distance unavailable"}</span>
                        </div>

                        <button
                          type="button"
                          onClick={() => handleOpenLocationModal(visit)}
                          className={`flex items-center space-x-1 text-[11px] px-2 py-0.5 rounded border transition ${
                            hasGps
                              ? "bg-emerald-50 text-emerald-800 border-emerald-200 hover:bg-emerald-100"
                              : "bg-slate-50 text-slate-500 border-slate-200 hover:bg-slate-100"
                          }`}
                          title="Record or correct household GPS coordinates"
                        >
                          <MapPin className="w-3 h-3 text-slate-500" />
                          <span>{hasGps ? "GPS Recorded" : "Record GPS"}</span>
                        </button>
                      </div>
                    </div>

                    {/* Beneficiary Details */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div>
                        <h3 className="text-sm sm:text-base font-bold text-slate-900">
                          {visit.beneficiary_name}
                        </h3>
                        <p className="text-xs text-slate-600">
                          Head: {visit.household_head} • Type: <span className="font-semibold text-slate-800">{visit.beneficiary_type}</span> • Village: <strong>{visit.village}</strong>
                        </p>
                        <p className="text-xs font-semibold text-teal-800 mt-1">
                          Protocol: {visit.service_name}
                        </p>
                        <p className="text-[11px] text-slate-400 font-mono">
                          {visit.protocol_citation}
                        </p>
                      </div>

                      {/* Clinical Priority Reason (Part C Requirement) */}
                      <div className="bg-slate-50 border border-slate-200 p-2.5 rounded-lg text-xs max-w-xs sm:text-right space-y-0.5">
                        <span className="text-[10px] font-bold text-slate-400 uppercase block">
                          Clinical Triage Explanation:
                        </span>
                        <span className="font-medium text-slate-700 block">
                          {visit.priority_reason}
                        </span>
                        {visit.straight_line_distance_km !== null && (
                          <span className="text-[10px] text-teal-700 block font-semibold">
                            Tie-breaker: {visit.distance_display}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Completed Observation */}
                    {visit.visited && visit.visit_notes && (
                      <div className="bg-emerald-50 border border-emerald-200 p-2.5 rounded-lg text-xs text-emerald-900">
                        <span className="font-bold">Completed Observation: </span>
                        <span>{visit.visit_notes}</span>
                      </div>
                    )}

                    {/* Action Buttons */}
                    <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100">
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => setDetailHousehold(visit)}
                          className="text-xs font-semibold text-teal-700 hover:text-teal-900 px-2 py-1 rounded hover:bg-teal-50 transition"
                        >
                          View Profile
                        </button>
                        <a
                          href={`tel:${visit.contact_phone}`}
                          className="flex items-center space-x-1 text-xs text-slate-600 hover:text-slate-900 px-2 py-1 rounded hover:bg-slate-100 transition"
                        >
                          <Phone className="w-3.5 h-3.5 text-slate-400" />
                          <span>{visit.contact_phone}</span>
                        </a>
                      </div>

                      <div>
                        {visit.visited ? (
                          <span className="bg-emerald-100 text-emerald-800 text-xs font-bold px-3 py-1 rounded-full flex items-center space-x-1">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                            <span>Visit Completed</span>
                          </span>
                        ) : (
                          <button
                            onClick={() => handleOpenVisitModal(visit)}
                            className="bg-teal-700 hover:bg-teal-800 text-white font-bold py-1.5 px-4 rounded-xl text-xs flex items-center space-x-1.5 shadow-xs transition"
                          >
                            <HeartPulse className="w-3.5 h-3.5" />
                            <span>Conduct & Record Visit</span>
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}

              {scoredVisits.length > 35 && (
                <div className="text-center py-2 text-xs text-slate-400 italic">
                  Showing top 35 prioritized households. Filter by village to focus daily fieldwork.
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* HOUSEHOLD LOCATION CAPTURE & CORRECTION MODAL (Part A) */}
      {locationModalHousehold && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-3 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-slate-200 p-5 space-y-4">
            <div className="flex items-start justify-between border-b border-slate-200 pb-3">
              <div>
                <span className="text-[10px] font-bold text-teal-700 uppercase tracking-wide">
                  Household Geographic Location
                </span>
                <h3 className="text-base font-bold text-slate-900">
                  {locationModalHousehold.household_id} — {locationModalHousehold.household_head}
                </h3>
                <p className="text-xs text-slate-500">
                  Village: {locationModalHousehold.village} • Beneficiary: {locationModalHousehold.beneficiary_name}
                </p>
              </div>
              <button
                onClick={() => setLocationModalHousehold(null)}
                className="text-slate-400 hover:text-slate-700 text-lg font-bold p-1 leading-none"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveHouseholdLocation} className="space-y-3 text-xs">
              <div className="bg-slate-50 border border-slate-200 p-3 rounded-xl space-y-2">
                <span className="font-bold text-slate-700 flex items-center space-x-1">
                  <MapPin className="w-3.5 h-3.5 text-teal-600" />
                  <span>Current Stored Coordinates:</span>
                </span>
                <p className="font-mono text-xs text-slate-800">
                  {isValidCoordinate(locationModalHousehold.latitude, locationModalHousehold.longitude)
                    ? `${locationModalHousehold.latitude}° N, ${locationModalHousehold.longitude}° E (${locationModalHousehold.location_source || "Recorded"})`
                    : "Coordinates not recorded (Location unverified)"}
                </p>
              </div>

              {/* Quick GPS sensor capture */}
              <div>
                <button
                  type="button"
                  onClick={handleCaptureGpsForHousehold}
                  className="w-full bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold py-2 px-3 rounded-xl text-xs flex items-center justify-center space-x-1.5 transition"
                >
                  <Crosshair className="w-3.5 h-3.5 text-teal-700" />
                  <span>Tag with Current Device GPS Sensor</span>
                </button>
              </div>

              {/* Manual coordinate inputs with strict validation */}
              <div className="grid grid-cols-2 gap-2 pt-1">
                <div>
                  <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">
                    Latitude (-90 to +90) *
                  </label>
                  <input
                    type="number"
                    step="0.000001"
                    placeholder="e.g. 16.5062"
                    value={editLat}
                    onChange={(e) => setEditLat(e.target.value)}
                    required
                    className="w-full bg-slate-50 border border-slate-300 rounded p-2 text-xs font-mono text-slate-900 focus:bg-white focus:outline-teal-600"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">
                    Longitude (-180 to +180) *
                  </label>
                  <input
                    type="number"
                    step="0.000001"
                    placeholder="e.g. 80.6480"
                    value={editLon}
                    onChange={(e) => setEditLon(e.target.value)}
                    required
                    className="w-full bg-slate-50 border border-slate-300 rounded p-2 text-xs font-mono text-slate-900 focus:bg-white focus:outline-teal-600"
                  />
                </div>
              </div>

              {locationFeedback && (
                <div className="text-[11px] text-teal-800 bg-teal-50 p-2 rounded-lg border border-teal-200">
                  {locationFeedback}
                </div>
              )}

              <div className="flex justify-end space-x-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setLocationModalHousehold(null)}
                  className="px-3.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-xl text-xs transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-3.5 py-1.5 bg-teal-700 hover:bg-teal-800 text-white font-bold rounded-xl text-xs transition shadow-xs flex items-center space-x-1"
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>Save Verified Coordinates</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* FOLLOW-UP COMPLETION MODAL (Part F) */}
      {followUpToComplete && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-3 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-slate-200 p-5 space-y-4">
            <div className="flex items-start justify-between border-b border-slate-200 pb-3">
              <div>
                <span className="text-[10px] font-bold text-rose-700 uppercase tracking-wide">
                  Complete Clinical Follow-Up
                </span>
                <h3 className="text-base font-bold text-slate-900">
                  {followUpToComplete.task_description}
                </h3>
                <p className="text-xs text-slate-500">
                  Beneficiary: {followUpToComplete.beneficiary_name} ({followUpToComplete.household_id}, {followUpToComplete.village})
                </p>
              </div>
              <button
                onClick={() => setFollowUpToComplete(null)}
                className="text-slate-400 hover:text-slate-700 text-lg font-bold p-1 leading-none"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCompleteFollowUpSubmit} className="space-y-3 text-xs">
              <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">
                  Completion Observations & Outcome *
                </label>
                <textarea
                  rows={3}
                  value={followUpNotes}
                  onChange={(e) => setFollowUpNotes(e.target.value)}
                  placeholder="e.g. Visited mother at home. BP re-checked: 122/82 mmHg normal. Advised continued rest and hydration."
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900 focus:bg-white"
                  required
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setFollowUpToComplete(null)}
                  className="px-3.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-xl text-xs transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-3.5 py-1.5 bg-rose-700 hover:bg-rose-800 text-white font-bold rounded-xl text-xs transition shadow-xs flex items-center space-x-1"
                >
                  <Check className="w-3.5 h-3.5" />
                  <span>Mark Completed</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CONDUCT VISIT MODAL */}
      {activeVisitModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-3 z-50">
          <div className="bg-white rounded-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto shadow-2xl border border-slate-200 p-5 space-y-4">
            <div className="flex items-start justify-between border-b border-slate-200 pb-3">
              <div>
                <span className="text-[10px] font-bold text-teal-700 uppercase tracking-wide">
                  Record Household Field Visit
                </span>
                <h3 className="text-base font-bold text-slate-900">
                  {activeVisitModal.beneficiary_name} ({activeVisitModal.household_id})
                </h3>
                <p className="text-xs text-slate-500">
                  Village: {activeVisitModal.village} • Service: {activeVisitModal.service_name}
                </p>
              </div>
              <button
                onClick={() => setActiveVisitModal(null)}
                className="text-slate-400 hover:text-slate-700 text-lg font-bold p-1 leading-none"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCompleteVisitSubmit} className="space-y-3 text-xs">
              {/* Clinical Vitals Section */}
              <div className="bg-slate-50 border border-slate-200 p-3 rounded-xl space-y-2">
                <span className="font-bold text-slate-800 flex items-center space-x-1.5">
                  <HeartPulse className="w-4 h-4 text-teal-600" />
                  <span>Clinical Observations & Vitals:</span>
                </span>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">
                      Blood Pressure (mmHg)
                    </label>
                    <div className="flex space-x-1">
                      <input
                        type="number"
                        placeholder="Sys (120)"
                        value={bpSystolic}
                        onChange={(e) => setBpSystolic(e.target.value)}
                        className="w-1/2 bg-white border border-slate-300 rounded p-1.5 text-xs text-slate-900"
                      />
                      <span className="self-center text-slate-400">/</span>
                      <input
                        type="number"
                        placeholder="Dia (80)"
                        value={bpDiastolic}
                        onChange={(e) => setBpDiastolic(e.target.value)}
                        className="w-1/2 bg-white border border-slate-300 rounded p-1.5 text-xs text-slate-900"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">
                      Pulse Rate (bpm)
                    </label>
                    <input
                      type="number"
                      placeholder="e.g. 76"
                      value={pulse}
                      onChange={(e) => setPulse(e.target.value)}
                      className="w-full bg-white border border-slate-300 rounded p-1.5 text-xs text-slate-900"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">
                      Temp (°F)
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      placeholder="98.6"
                      value={temp}
                      onChange={(e) => setTemp(e.target.value)}
                      className="w-full bg-white border border-slate-300 rounded p-1.5 text-xs text-slate-900"
                    />
                  </div>

                  <div>
                    <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">
                      Weight (kg)
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      placeholder="e.g. 52.4"
                      value={weight}
                      onChange={(e) => setWeight(e.target.value)}
                      className="w-full bg-white border border-slate-300 rounded p-1.5 text-xs text-slate-900"
                    />
                  </div>

                  <div>
                    <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">
                      MUAC (mm)
                    </label>
                    <input
                      type="number"
                      placeholder="<115=SAM"
                      value={muac}
                      onChange={(e) => setMuac(e.target.value)}
                      className="w-full bg-white border border-slate-300 rounded p-1.5 text-xs text-slate-900"
                    />
                  </div>
                </div>
              </div>

              {/* Service Outcome Notes */}
              <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">
                  Services Provided & Clinical Notes *
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="e.g. Dispensed IFA 30 tablets, advised dietary iron, checked fetal movement, mother counselled on birth preparedness."
                  rows={3}
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900"
                  required
                />
              </div>

              {/* Next Scheduled Follow-up */}
              <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">
                  Schedule Next Follow-Up Date
                </label>
                <input
                  type="date"
                  value={followUpDate}
                  onChange={(e) => setFollowUpDate(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2 text-xs text-slate-900"
                />
              </div>

              {/* Actions */}
              <div className="flex justify-end space-x-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setActiveVisitModal(null)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-xl text-xs transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-teal-700 hover:bg-teal-800 text-white font-bold rounded-xl text-xs transition shadow-sm flex items-center space-x-1.5"
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>{submitting ? "Saving..." : "Commit Visit (Offline)"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* PATIENT DETAIL MODAL */}
      {detailHousehold && (
        <PatientDetailModal
          householdRecord={detailHousehold}
          onClose={() => setDetailHousehold(null)}
          onRecordVisit={(hhId) => {
            const h = dataService.getHouseholdById(hhId);
            if (h) handleOpenVisitModal(h);
          }}
        />
      )}
    </div>
  );
};
