import React, { useState } from "react";
import {
  User,
  Phone,
  MapPin,
  Calendar,
  AlertTriangle,
  CheckCircle,
  FileText,
  Heart,
  Pill,
  Clock,
  Save,
  X,
  Plus,
} from "lucide-react";
import { dataService, PatientProfile, HouseholdRecord } from "../engine/dataService";

interface PatientDetailModalProps {
  patientId?: string;
  householdRecord?: HouseholdRecord;
  onClose: () => void;
  onRecordVisit?: (householdId: string) => void;
}

export const PatientDetailModal: React.FC<PatientDetailModalProps> = ({
  patientId,
  householdRecord,
  onClose,
  onRecordVisit,
}) => {
  // Find patient record if exists, or construct from household
  const existingPatient = patientId ? dataService.getPatientById(patientId) : undefined;

  const [phone, setPhone] = useState(
    existingPatient?.contact_phone || householdRecord?.contact_phone || ""
  );
  const [bloodGroup, setBloodGroup] = useState(existingPatient?.blood_group || "Unknown");
  const [allergiesText, setAllergiesText] = useState(
    existingPatient?.allergies ? existingPatient.allergies.join(", ") : "None"
  );
  const [medsText, setMedsText] = useState(
    existingPatient?.current_medications ? existingPatient.current_medications.join(", ") : "IFA tablets"
  );
  const [nextVisit, setNextVisit] = useState(
    existingPatient?.next_visit_date || householdRecord?.due_date || ""
  );
  const [notes, setNotes] = useState(householdRecord?.visit_notes || "");

  const [isEditing, setIsEditing] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  const name = existingPatient?.name || householdRecord?.beneficiary_name || "Beneficiary";
  const village = existingPatient?.village || householdRecord?.village || "Rural Village";
  const isHighRisk = existingPatient?.is_high_risk || householdRecord?.is_high_risk;
  const riskTag = existingPatient?.risk_condition || householdRecord?.risk_tag;

  const handleSave = () => {
    setValidationError(null);
    if (!phone || phone.length < 10) {
      setValidationError("Please enter a valid 10-digit contact number.");
      return;
    }

    const allergiesArr = allergiesText.split(",").map((s) => s.trim()).filter(Boolean);
    const medsArr = medsText.split(",").map((s) => s.trim()).filter(Boolean);

    if (existingPatient) {
      dataService.updatePatient(existingPatient.patient_id, {
        contact_phone: phone,
        blood_group: bloodGroup,
        allergies: allergiesArr,
        current_medications: medsArr,
        next_visit_date: nextVisit,
      });
    }

    if (householdRecord) {
      dataService.updateHousehold(householdRecord.household_id, {
        contact_phone: phone,
        visit_notes: notes,
        due_date: nextVisit || householdRecord.due_date,
      });
    }

    setSaveSuccess(true);
    setIsEditing(false);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-3 z-50">
      <div className="bg-white rounded-2xl max-w-xl w-full max-h-[90vh] overflow-y-auto shadow-2xl border border-slate-200 p-5 space-y-4">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-slate-200 pb-3">
          <div className="flex items-center space-x-3">
            <div className="w-11 h-11 rounded-full bg-teal-100 border border-teal-300 flex items-center justify-center text-teal-800 font-bold text-base">
              {name.slice(0, 2).toUpperCase()}
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-base font-bold text-slate-900 leading-tight">
                  {name}
                </h3>
                {isHighRisk && (
                  <span className="bg-red-100 text-red-800 text-[10px] font-bold px-2 py-0.5 rounded-full border border-red-200 flex items-center space-x-1">
                    <AlertTriangle className="w-3 h-3 text-red-600" />
                    <span>HIGH RISK</span>
                  </span>
                )}
                <span className="bg-amber-50 text-amber-900 border border-amber-300 font-mono text-[9px] font-bold px-1.5 py-0.5 rounded">
                  Synthetic Record
                </span>
              </div>
              <p className="text-xs text-slate-500">
                {householdRecord?.household_id ? `Household ID: ${householdRecord.household_id} • ` : ""}
                {village}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 text-lg font-bold p-1 leading-none"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {saveSuccess && (
          <div className="p-2.5 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs font-semibold flex items-center space-x-1.5">
            <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Profile and clinical follow-up changes saved locally to IndexedDB register.</span>
          </div>
        )}

        {validationError && (
          <div className="p-2.5 bg-red-50 border border-red-200 text-red-800 rounded-lg text-xs font-semibold">
            {validationError}
          </div>
        )}

        {/* Clinical Danger Tag if High Risk */}
        {isHighRisk && (
          <div className="bg-red-50 border border-red-200 p-3 rounded-xl text-xs text-red-900 space-y-1">
            <span className="font-bold flex items-center space-x-1">
              <AlertTriangle className="w-3.5 h-3.5 text-red-600" />
              <span>Active High-Risk Condition: {riskTag || "Severe Clinical Alert"}</span>
            </span>
            <p className="text-[11px] text-red-700 leading-snug">
              Priority protocol mandates bi-weekly monitoring, maternal vitals check, or NRC nutrition follow-up.
            </p>
          </div>
        )}

        {/* Identity & Household Attributes */}
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
            <span className="text-slate-400 text-[10px] font-bold uppercase block">
              Head of Household:
            </span>
            <span className="font-semibold text-slate-800">
              {existingPatient?.family_head || householdRecord?.household_head || "Kumar Srinivas"}
            </span>
          </div>

          <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
            <span className="text-slate-400 text-[10px] font-bold uppercase block">
              Beneficiary Type:
            </span>
            <span className="font-semibold text-slate-800">
              {householdRecord?.beneficiary_type || (existingPatient?.is_pregnant ? "Pregnant Woman" : "Adult Beneficiary")}
            </span>
          </div>

          <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
            <span className="text-slate-400 text-[10px] font-bold uppercase block">
              Blood Group:
            </span>
            {isEditing ? (
              <select
                value={bloodGroup}
                onChange={(e) => setBloodGroup(e.target.value)}
                className="w-full bg-white border border-slate-300 rounded px-1.5 py-0.5 text-xs"
              >
                {["Unknown", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"].map((bg) => (
                  <option key={bg} value={bg}>
                    {bg}
                  </option>
                ))}
              </select>
            ) : (
              <span className="font-semibold text-slate-800">{bloodGroup}</span>
            )}
          </div>

          <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
            <span className="text-slate-400 text-[10px] font-bold uppercase block">
              Contact Phone:
            </span>
            {isEditing ? (
              <input
                type="text"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="w-full bg-white border border-slate-300 rounded px-1.5 py-0.5 text-xs"
              />
            ) : (
              <span className="font-semibold text-slate-800">{phone || "Not recorded"}</span>
            )}
          </div>
        </div>

        {/* Current Protocol Service */}
        {householdRecord && (
          <div className="bg-teal-50/60 border border-teal-200 p-3 rounded-xl text-xs space-y-1">
            <span className="text-teal-800 text-[10px] font-bold uppercase tracking-wider block">
              Scheduled Due Service:
            </span>
            <div className="font-bold text-teal-950 text-sm">
              {householdRecord.service_name}
            </div>
            <div className="text-[11px] text-teal-700 font-mono">
              Citation: {householdRecord.protocol_citation}
            </div>
            <div className="flex justify-between items-center pt-1 text-[11px] text-slate-500">
              <span>Scheduled Due: {householdRecord.due_date}</span>
              <span
                className={`font-bold ${
                  householdRecord.visited ? "text-emerald-700" : "text-amber-700"
                }`}
              >
                {householdRecord.visited ? "✓ Visited" : "Pending Field Visit"}
              </span>
            </div>
          </div>
        )}

        {/* Medical & Allergies Notes */}
        <div className="space-y-2 text-xs">
          <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200 space-y-1">
            <span className="text-slate-400 text-[10px] font-bold uppercase block">
              Known Drug Allergies:
            </span>
            {isEditing ? (
              <input
                type="text"
                value={allergiesText}
                onChange={(e) => setAllergiesText(e.target.value)}
                placeholder="e.g. None, Penicillin"
                className="w-full bg-white border border-slate-300 rounded px-2 py-1 text-xs"
              />
            ) : (
              <span className="font-medium text-slate-800">{allergiesText}</span>
            )}
          </div>

          <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200 space-y-1">
            <span className="text-slate-400 text-[10px] font-bold uppercase block">
              Current Standing Protocol Supplements:
            </span>
            {isEditing ? (
              <input
                type="text"
                value={medsText}
                onChange={(e) => setMedsText(e.target.value)}
                placeholder="e.g. IFA tablet (1 daily), Calcium"
                className="w-full bg-white border border-slate-300 rounded px-2 py-1 text-xs"
              />
            ) : (
              <span className="font-medium text-slate-800">{medsText}</span>
            )}
          </div>
        </div>

        {/* Next Follow-Up Date & Notes */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
          <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200 space-y-1">
            <span className="text-slate-400 text-[10px] font-bold uppercase block">
              Next Scheduled Follow-up:
            </span>
            {isEditing ? (
              <input
                type="date"
                value={nextVisit}
                onChange={(e) => setNextVisit(e.target.value)}
                className="w-full bg-white border border-slate-300 rounded px-2 py-1 text-xs"
              />
            ) : (
              <span className="font-semibold text-slate-800">{nextVisit || "Not set"}</span>
            )}
          </div>

          <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200 space-y-1">
            <span className="text-slate-400 text-[10px] font-bold uppercase block">
              Field Notes / Observations:
            </span>
            {isEditing ? (
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                className="w-full bg-white border border-slate-300 rounded px-2 py-1 text-xs"
              />
            ) : (
              <span className="text-slate-700 italic">{notes || "No visit notes recorded yet."}</span>
            )}
          </div>
        </div>

        {/* Longitudinal Visit History if exists */}
        {existingPatient?.visit_history && existingPatient.visit_history.length > 0 && (
          <div className="space-y-1.5 pt-1">
            <h4 className="text-xs font-bold text-slate-900 uppercase">Past Visit Timeline:</h4>
            <div className="divide-y divide-slate-100 max-h-28 overflow-y-auto bg-slate-50 rounded-lg p-2 border border-slate-200 text-xs">
              {existingPatient.visit_history.map((vh, idx) => (
                <div key={idx} className="py-1">
                  <div className="flex justify-between font-semibold text-slate-800">
                    <span>{vh.service}</span>
                    <span className="text-slate-400 font-mono text-[10px]">{vh.date}</span>
                  </div>
                  <p className="text-[11px] text-slate-600">{vh.notes}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Footer Actions */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-2 pt-3 border-t border-slate-200">
          <div className="flex items-center space-x-2 w-full sm:w-auto">
            {isEditing ? (
              <>
                <button
                  onClick={handleSave}
                  className="flex-1 sm:flex-initial bg-teal-700 hover:bg-teal-800 text-white font-bold py-2 px-4 rounded-xl text-xs flex items-center justify-center space-x-1.5 shadow-sm transition"
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>Save Changes</span>
                </button>
                <button
                  onClick={() => setIsEditing(false)}
                  className="bg-slate-200 hover:bg-slate-300 text-slate-700 font-semibold py-2 px-3 rounded-xl text-xs transition"
                >
                  Cancel
                </button>
              </>
            ) : (
              <button
                onClick={() => setIsEditing(true)}
                className="bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-300 font-semibold py-2 px-3.5 rounded-xl text-xs transition"
              >
                Edit Permitted Fields
              </button>
            )}
          </div>

          <div className="flex items-center space-x-2 w-full sm:w-auto">
            {householdRecord && !householdRecord.visited && onRecordVisit && (
              <button
                onClick={() => {
                  onClose();
                  onRecordVisit(householdRecord.household_id);
                }}
                className="flex-1 sm:flex-initial bg-emerald-700 hover:bg-emerald-800 text-white font-bold py-2 px-4 rounded-xl text-xs transition shadow-sm flex items-center justify-center space-x-1"
              >
                <CheckCircle className="w-3.5 h-3.5" />
                <span>Conduct Visit</span>
              </button>
            )}
            <button
              onClick={onClose}
              className="bg-slate-800 hover:bg-slate-900 text-white font-semibold py-2 px-4 rounded-xl text-xs transition"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
