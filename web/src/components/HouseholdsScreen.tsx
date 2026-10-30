import React, { useState, useMemo } from "react";
import {
  Users,
  Search,
  Filter,
  Plus,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Phone,
  Home,
  ChevronRight,
  BookOpen,
} from "lucide-react";
import { dataService, HouseholdRecord } from "../engine/dataService";
import { PatientDetailModal } from "./PatientDetailModal";

interface HouseholdsScreenProps {
  onStartVisit?: (householdId: string) => void;
}

export const HouseholdsScreen: React.FC<HouseholdsScreenProps> = ({ onStartVisit }) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedVillage, setSelectedVillage] = useState<string>("All");
  const [selectedType, setSelectedType] = useState<string>("All");
  const [selectedRisk, setSelectedRisk] = useState<string>("All");
  const [selectedStatus, setSelectedStatus] = useState<string>("All");

  const [selectedHousehold, setSelectedHousehold] = useState<HouseholdRecord | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);

  // Add Household form state
  const [headName, setHeadName] = useState("");
  const [village, setVillage] = useState("Venkatapuram");
  const [phone, setPhone] = useState("");
  const [beneficiaryName, setBeneficiaryName] = useState("");
  const [beneficiaryType, setBeneficiaryType] = useState("Pregnant Woman");
  const [serviceName, setServiceName] = useState("ANC Visit 2 (14-26 Weeks)");
  const [dueDate, setDueDate] = useState("2026-10-30");
  const [isHighRisk, setIsHighRisk] = useState(false);
  const [riskTag, setRiskTag] = useState("SEVERE_ANEMIA");
  const [formError, setFormError] = useState<string | null>(null);

  const villages = useMemo(() => ["All", ...dataService.getVillages()], []);
  const allHouseholds = dataService.getHouseholds();

  // Filtered households
  const filteredHouseholds = useMemo(() => {
    return allHouseholds.filter((h) => {
      // Search term
      if (searchTerm.trim()) {
        const term = searchTerm.toLowerCase();
        const matches =
          h.household_id.toLowerCase().includes(term) ||
          h.household_head.toLowerCase().includes(term) ||
          h.beneficiary_name.toLowerCase().includes(term) ||
          h.contact_phone.includes(term) ||
          h.service_name.toLowerCase().includes(term);
        if (!matches) return false;
      }

      // Village
      if (selectedVillage !== "All" && h.village.toLowerCase() !== selectedVillage.toLowerCase()) {
        return false;
      }

      // Type
      if (selectedType !== "All" && h.beneficiary_type.toLowerCase() !== selectedType.toLowerCase()) {
        return false;
      }

      // Risk
      if (selectedRisk === "high" && !h.is_high_risk) return false;
      if (selectedRisk === "routine" && h.is_high_risk) return false;

      // Status
      if (selectedStatus === "visited" && !h.visited) return false;
      if (selectedStatus === "pending" && h.visited) return false;

      return true;
    });
  }, [allHouseholds, searchTerm, selectedVillage, selectedType, selectedRisk, selectedStatus]);

  const handleAddSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!headName.trim() || !beneficiaryName.trim()) {
      setFormError("Please enter head of household and beneficiary name.");
      return;
    }
    if (!phone.trim() || phone.trim().length < 10) {
      setFormError("Please enter a valid 10-digit phone number.");
      return;
    }

    dataService.addHousehold({
      village,
      household_head: headName,
      contact_phone: phone,
      beneficiary_name: beneficiaryName,
      beneficiary_type: beneficiaryType,
      service_code: "CUSTOM_PROTOCOL",
      service_name: serviceName,
      protocol_citation: "[DOC-ANC-01] National Health Mission AP Guidelines",
      due_date: dueDate,
      is_high_risk: isHighRisk,
      risk_tag: isHighRisk ? riskTag : null,
      visit_notes: "",
    });

    // Reset
    setHeadName("");
    setPhone("");
    setBeneficiaryName("");
    setShowAddModal(false);
  };

  return (
    <div className="space-y-4 pb-16 sm:pb-6">
      {/* Header & Add Button */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center space-x-2">
            <Users className="w-5 h-5 text-teal-700" />
            <h2 className="text-base font-bold text-slate-900">
              Digital Household Register
            </h2>
            <span className="bg-teal-50 text-teal-800 text-xs font-bold px-2 py-0.5 rounded-full border border-teal-200">
              {allHouseholds.length} Families
            </span>
            <span className="bg-amber-50 text-amber-900 border border-amber-300 font-mono text-[10px] font-bold px-2 py-0.5 rounded">
              Synthetic Demo Data
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            500 Synthetic Register Households across rural Andhra Pradesh. Offline persistent storage.
          </p>
        </div>

        <button
          onClick={() => setShowAddModal(true)}
          className="bg-teal-700 hover:bg-teal-800 text-white font-bold py-2 px-3.5 rounded-xl text-xs flex items-center justify-center space-x-1.5 shadow-sm transition self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>Register Household</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 space-y-3">
        {/* Search */}
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by ID (HH-0001), name, village, or service..."
            className="w-full pl-9 pr-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-teal-600 focus:bg-white text-slate-900"
          />
        </div>

        {/* Filters Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
          {/* Village */}
          <div>
            <label className="text-[10px] font-bold text-slate-400 uppercase block mb-1">
              Village:
            </label>
            <select
              value={selectedVillage}
              onChange={(e) => setSelectedVillage(e.target.value)}
              className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2 text-xs font-medium text-slate-800"
            >
              {villages.map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
            </select>
          </div>

          {/* Beneficiary Type */}
          <div>
            <label className="text-[10px] font-bold text-slate-400 uppercase block mb-1">
              Beneficiary:
            </label>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2 text-xs font-medium text-slate-800"
            >
              <option value="All">All Types</option>
              <option value="Child">Child</option>
              <option value="Pregnant Woman">Pregnant Woman</option>
              <option value="Hypertension Patient">Hypertension</option>
              <option value="SAM Child">SAM Child</option>
              <option value="Adolescent">Adolescent</option>
            </select>
          </div>

          {/* Risk Level */}
          <div>
            <label className="text-[10px] font-bold text-slate-400 uppercase block mb-1">
              Clinical Risk:
            </label>
            <select
              value={selectedRisk}
              onChange={(e) => setSelectedRisk(e.target.value)}
              className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2 text-xs font-medium text-slate-800"
            >
              <option value="All">All Records</option>
              <option value="high">High Risk Only</option>
              <option value="routine">Routine</option>
            </select>
          </div>

          {/* Status */}
          <div>
            <label className="text-[10px] font-bold text-slate-400 uppercase block mb-1">
              Field Status:
            </label>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2 text-xs font-medium text-slate-800"
            >
              <option value="All">All Statuses</option>
              <option value="pending">Pending Visit</option>
              <option value="visited">Completed</option>
            </select>
          </div>
        </div>

        {/* Results Count Banner */}
        <div className="flex justify-between items-center text-[11px] text-slate-500 pt-1 border-t border-slate-100">
          <span>
            Showing <strong>{filteredHouseholds.length}</strong> matching households
          </span>
          {(searchTerm ||
            selectedVillage !== "All" ||
            selectedType !== "All" ||
            selectedRisk !== "All" ||
            selectedStatus !== "All") && (
            <button
              onClick={() => {
                setSearchTerm("");
                setSelectedVillage("All");
                setSelectedType("All");
                setSelectedRisk("All");
                setSelectedStatus("All");
              }}
              className="text-teal-700 hover:underline font-semibold"
            >
              Reset Filters
            </button>
          )}
        </div>
      </div>

      {/* Households List Cards */}
      {filteredHouseholds.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-8 text-center space-y-2">
          <Users className="w-8 h-8 text-slate-300 mx-auto" />
          <h3 className="text-sm font-bold text-slate-700">No matching households found</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Try adjusting your search terms, village filter, or risk filter.
          </p>
        </div>
      ) : (
        <div className="space-y-2.5">
          {filteredHouseholds.slice(0, 40).map((h) => (
            <div
              key={h.household_id}
              onClick={() => setSelectedHousehold(h)}
              className="bg-white border border-slate-200 hover:border-teal-500 rounded-xl p-3.5 shadow-xs transition cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-3 group"
            >
              {/* Left Column: ID, Head, Beneficiary, Village */}
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="font-mono text-xs font-bold text-slate-600 bg-slate-100 px-2 py-0.5 rounded">
                    {h.household_id}
                  </span>
                  <h4 className="text-sm font-bold text-slate-900 group-hover:text-teal-800 transition">
                    {h.beneficiary_name}
                  </h4>
                  {h.is_high_risk && (
                    <span className="bg-red-100 text-red-800 text-[10px] font-bold px-2 py-0.5 rounded-full border border-red-200 flex items-center space-x-1">
                      <AlertTriangle className="w-3 h-3 text-red-600" />
                      <span>{h.risk_tag || "HIGH RISK"}</span>
                    </span>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
                  <span className="flex items-center space-x-1">
                    <Home className="w-3.5 h-3.5 text-slate-400" />
                    <span>Head: {h.household_head}</span>
                  </span>
                  <span>•</span>
                  <span>Village: {h.village}</span>
                  <span>•</span>
                  <span className="font-medium text-slate-700">Type: {h.beneficiary_type}</span>
                </div>

                <div className="text-xs text-teal-800 font-medium">
                  Service: {h.service_name}
                </div>
              </div>

              {/* Right Column: Due Date, Visited Badge, Actions */}
              <div className="flex sm:flex-col items-center sm:items-end justify-between sm:justify-center border-t sm:border-t-0 pt-2 sm:pt-0 border-slate-100 gap-1.5 shrink-0">
                <div className="text-right">
                  <div className="text-[11px] text-slate-400">Scheduled Due</div>
                  <div className="font-mono text-xs font-bold text-slate-800">
                    {h.due_date}
                  </div>
                </div>

                <div>
                  {h.visited ? (
                    <span className="bg-emerald-100 text-emerald-800 text-xs font-bold px-2.5 py-1 rounded-full flex items-center space-x-1">
                      <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                      <span>Visited</span>
                    </span>
                  ) : (
                    <span className="bg-amber-100 text-amber-900 text-xs font-semibold px-2.5 py-1 rounded-full flex items-center space-x-1">
                      <Clock className="w-3 h-3 text-amber-700" />
                      <span>Pending</span>
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}

          {filteredHouseholds.length > 40 && (
            <div className="text-center py-2 text-xs text-slate-400 italic">
              Showing top 40 of {filteredHouseholds.length} matching records. Use filters to narrow view.
            </div>
          )}
        </div>
      )}

      {/* Household / Patient Detail Modal */}
      {selectedHousehold && (
        <PatientDetailModal
          householdRecord={selectedHousehold}
          onClose={() => setSelectedHousehold(null)}
          onRecordVisit={(hhId) => {
            if (onStartVisit) onStartVisit(hhId);
          }}
        />
      )}

      {/* Add Household Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-3 z-50">
          <div className="bg-white rounded-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto shadow-2xl border border-slate-200 p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <h3 className="text-base font-bold text-slate-900">
                Register New Household
              </h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-slate-400 hover:text-slate-700 text-lg font-bold p-1 leading-none"
              >
                ✕
              </button>
            </div>

            {formError && (
              <div className="p-2.5 bg-red-50 border border-red-200 text-red-800 rounded-lg text-xs font-semibold">
                {formError}
              </div>
            )}

            <form onSubmit={handleAddSubmit} className="space-y-3 text-xs">
              <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">
                  Head of Household Name *
                </label>
                <input
                  type="text"
                  value={headName}
                  onChange={(e) => setHeadName(e.target.value)}
                  placeholder="e.g. Ramesh Naidu"
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">
                    Village *
                  </label>
                  <select
                    value={village}
                    onChange={(e) => setVillage(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900"
                  >
                    {villages.filter((v) => v !== "All").map((v) => (
                      <option key={v} value={v}>
                        {v}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">
                    Contact Phone *
                  </label>
                  <input
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="10-digit mobile"
                    className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">
                    Beneficiary Name *
                  </label>
                  <input
                    type="text"
                    value={beneficiaryName}
                    onChange={(e) => setBeneficiaryName(e.target.value)}
                    placeholder="e.g. Lakshmi Devi"
                    className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900"
                    required
                  />
                </div>

                <div>
                  <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">
                    Beneficiary Type
                  </label>
                  <select
                    value={beneficiaryType}
                    onChange={(e) => setBeneficiaryType(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900"
                  >
                    <option value="Pregnant Woman">Pregnant Woman</option>
                    <option value="Child">Child (0-5 Yrs)</option>
                    <option value="Hypertension Patient">Hypertension Patient</option>
                    <option value="SAM Child">SAM Child</option>
                    <option value="Adolescent">Adolescent</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">
                  Scheduled Due Service
                </label>
                <input
                  type="text"
                  value={serviceName}
                  onChange={(e) => setServiceName(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900"
                />
              </div>

              <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">
                  Scheduled Due Date
                </label>
                <input
                  type="date"
                  value={dueDate}
                  onChange={(e) => setDueDate(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900"
                />
              </div>

              {/* High Risk Toggle */}
              <div className="bg-slate-50 border border-slate-200 p-3 rounded-lg space-y-2">
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isHighRisk}
                    onChange={(e) => setIsHighRisk(e.target.checked)}
                    className="rounded text-teal-600 focus:ring-teal-500"
                  />
                  <span className="font-bold text-slate-800 text-xs">
                    Mark as High-Risk Beneficiary (Tier 1 Priority)
                  </span>
                </label>

                {isHighRisk && (
                  <div>
                    <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">
                      Clinical Risk Condition:
                    </label>
                    <select
                      value={riskTag}
                      onChange={(e) => setRiskTag(e.target.value)}
                      className="w-full bg-white border border-slate-300 rounded-lg p-2 text-xs"
                    >
                      <option value="SEVERE_ANEMIA">Severe Anemia (Hb &lt; 7 g/dL)</option>
                      <option value="PREGNANCY_HYPERTENSION">Pregnancy-Induced Hypertension</option>
                      <option value="SAM_CHILD">Severe Acute Malnutrition (SAM)</option>
                      <option value="GESTATIONAL_DIABETES">Gestational Diabetes</option>
                      <option value="PREVIOUS_C_SECTION">Previous C-Section Red Flag</option>
                    </select>
                  </div>
                )}
              </div>

              <div className="flex justify-end space-x-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-xl text-xs transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-teal-700 hover:bg-teal-800 text-white font-bold rounded-xl text-xs transition shadow-sm"
                >
                  Save Household Locally
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
