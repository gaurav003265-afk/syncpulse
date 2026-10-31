import React, { useState } from "react";
import {
  ShieldAlert,
  AlertTriangle,
  PhoneCall,
  Plus,
  Clock,
  CheckCircle2,
  MapPin,
  Ambulance,
  PhoneForwarded,
  Info,
  Save,
  MessageSquare,
  Copy,
  Volume2,
  VolumeX,
} from "lucide-react";
import { dataService, EmergencyAlert } from "../engine/dataService";
import {
  dispatchGsmSms,
  copyEmergencyPayloadToClipboard,
  playEmergencySiren,
  stopEmergencySiren,
  callEmergency108,
  callMaternal102,
} from "../engine/telephony";

export const EmergencyScreen: React.FC = () => {
  const [alerts, setAlerts] = useState<EmergencyAlert[]>(dataService.getAlerts());
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [isSirenActive, setIsSirenActive] = useState(false);

  // Form states
  const [patientName, setPatientName] = useState("");
  const [village, setVillage] = useState("Venkatapuram");
  const [phone, setPhone] = useState("");
  const [severity, setSeverity] = useState<"CRITICAL" | "URGENT" | "ROUTINE">("CRITICAL");
  const [symptoms, setSymptoms] = useState("");
  const [description, setDescription] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const toggleSiren = () => {
    if (isSirenActive) {
      stopEmergencySiren();
      setIsSirenActive(false);
    } else {
      setIsSirenActive(true);
      playEmergencySiren(8);
      setTimeout(() => setIsSirenActive(false), 8000);
    }
  };

  const handleCopyPayload = async (alt: EmergencyAlert) => {
    const success = await copyEmergencyPayloadToClipboard({
      patientName: alt.patient_name,
      village: alt.village,
      symptoms: alt.symptoms,
      phone: alt.contact_phone,
      severity: alt.severity,
    });
    setToastMessage(
      success
        ? "✓ Emergency payload copied to clipboard for SMS or radio dispatch."
        : "⚠️ Clipboard copy failed."
    );
    setTimeout(() => setToastMessage(null), 4000);
  };

  const handleDispatchSms = (alt: EmergencyAlert) => {
    dispatchGsmSms({
      patientName: alt.patient_name,
      village: alt.village,
      symptoms: alt.symptoms,
      phone: alt.contact_phone,
      severity: alt.severity,
    });
  };

  const villages = dataService.getVillages();

  const handleCreateAlert = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!patientName.trim() || !symptoms.trim()) {
      setFormError("Please enter patient name and clinical symptoms.");
      return;
    }
    if (!phone.trim() || phone.trim().length < 10) {
      setFormError("Please enter a valid 10-digit mobile phone number.");
      return;
    }

    const created = dataService.createAlert({
      patient_id: `P-${Date.now().toString().slice(-4)}`,
      patient_name: patientName,
      village,
      contact_phone: phone,
      severity,
      symptoms,
      description: description || "Reported via ASHA Emergency Desk.",
      location: `${village} Village`,
      action_taken: "Recorded in local offline emergency register. Requires worker phone call.",
    });

    setAlerts(dataService.getAlerts());
    setShowCreateModal(false);
    setPatientName("");
    setPhone("");
    setSymptoms("");
    setDescription("");

    setToastMessage(`🚨 Emergency alert recorded locally on this device. Automated dispatch not configured. Please call 108 directly.`);
    setTimeout(() => setToastMessage(null), 6000);
  };

  const handleUpdateStatus = (
    alertId: string,
    status: any,
    action: string
  ) => {
    dataService.updateAlertStatus(alertId, status, action);
    setAlerts(dataService.getAlerts());
  };

  return (
    <div className="space-y-4 pb-16 sm:pb-6">
      {/* 1. Header & Direct Calling Hotline Ribbon */}
      <div className="bg-red-600 text-white rounded-2xl p-4 sm:p-5 shadow-md space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center space-x-3">
            <div className="bg-white/20 p-3 rounded-xl shrink-0">
              <ShieldAlert className="w-8 h-8 text-white animate-pulse" />
            </div>
            <div>
              <h2 className="text-base sm:text-xl font-black tracking-tight leading-tight">
                Emergency Desk & 108 Triage Hub
              </h2>
              <p className="text-xs text-red-100 font-medium">
                Immediate protocol escalation for obstetric, neonatal, and acute emergencies.
              </p>
            </div>
          </div>

          <button
            onClick={() => setShowCreateModal(true)}
            className="bg-white text-red-700 hover:bg-red-50 font-bold px-4 py-2.5 rounded-xl text-xs flex items-center justify-center space-x-1.5 shadow-sm transition shrink-0"
          >
            <Plus className="w-4 h-4" />
            <span>Record Emergency Event</span>
          </button>
        </div>

        {/* Real Direct Cellular Hotline Numbers & Siren */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5 pt-1">
          <a
            href="tel:108"
            className="bg-red-900/60 hover:bg-red-900 border border-red-400/60 rounded-xl p-3 flex items-center justify-between transition group"
          >
            <div className="flex items-center space-x-2.5">
              <Ambulance className="w-5 h-5 text-red-200" />
              <div>
                <div className="text-xs font-bold">108 Ambulance</div>
                <div className="text-[10px] text-red-200">Govt Free Emergency</div>
              </div>
            </div>
            <PhoneCall className="w-4 h-4 text-white group-hover:scale-110 transition" />
          </a>

          <a
            href="tel:102"
            className="bg-red-900/60 hover:bg-red-900 border border-red-400/60 rounded-xl p-3 flex items-center justify-between transition group"
          >
            <div className="flex items-center space-x-2.5">
              <PhoneForwarded className="w-5 h-5 text-red-200" />
              <div>
                <div className="text-xs font-bold">102 Maternal</div>
                <div className="text-[10px] text-red-200">Mother & Child Van</div>
              </div>
            </div>
            <PhoneCall className="w-4 h-4 text-white group-hover:scale-110 transition" />
          </a>

          <a
            href="tel:9848011221"
            className="bg-red-900/60 hover:bg-red-900 border border-red-400/60 rounded-xl p-3 flex items-center justify-between transition group"
          >
            <div className="flex items-center space-x-2.5">
              <PhoneCall className="w-5 h-5 text-red-200" />
              <div>
                <div className="text-xs font-bold">PHC Medical Officer</div>
                <div className="text-[10px] text-red-200">Dr. K. Srinivas</div>
              </div>
            </div>
            <PhoneCall className="w-4 h-4 text-white group-hover:scale-110 transition" />
          </a>

          <button
            onClick={toggleSiren}
            className={`border rounded-xl p-3 flex items-center justify-between transition cursor-pointer ${
              isSirenActive
                ? "bg-amber-400 text-slate-950 border-amber-500 font-black animate-pulse"
                : "bg-red-900/60 hover:bg-red-900 border-red-400/60 text-white font-bold"
            }`}
            title="Synthesized offline Web Audio siren alarm"
          >
            <div className="flex items-center space-x-2.5">
              {isSirenActive ? (
                <VolumeX className="w-5 h-5 text-slate-950" />
              ) : (
                <Volume2 className="w-5 h-5 text-red-200" />
              )}
              <div className="text-left">
                <div className="text-xs font-bold">
                  {isSirenActive ? "Stop Siren Alarm" : "Sound Field Siren"}
                </div>
                <div className="text-[10px] text-red-200">
                  {isSirenActive ? "880/1240 Hz Active" : "Zero-Asset Audio Beacon"}
                </div>
              </div>
            </div>
          </button>
        </div>
      </div>

      {/* Toast Feedback */}
      {toastMessage && (
        <div className="p-3 bg-red-50 border border-red-300 text-red-900 rounded-xl text-xs font-semibold flex items-center space-x-2 shadow-xs">
          <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Honest Delivery Status Transparency Callout */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-3.5 flex items-start space-x-2.5 text-xs text-amber-900">
        <Info className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-bold">Honest Offline Alert Notice:</p>
          <p className="text-amber-800 leading-relaxed">
            Events marked <strong>QUEUED_OFFLINE</strong> are saved safely on this device in the local outbox. They have <strong>NOT</strong> been transmitted to an external server or ambulance automatically. You must dial <strong>108 directly on cellular mobile</strong>.
          </p>
        </div>
      </div>

      {/* Emergency Incident Log Table / Feed */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <ShieldAlert className="w-4 h-4 text-red-600" />
            <h3 className="text-sm font-bold text-slate-900">
              Active Triage Incident Feed ({alerts.length})
            </h3>
          </div>
          <span className="text-[11px] text-slate-500 font-mono">
            Sorted by Recency
          </span>
        </div>

        {alerts.length === 0 ? (
          <div className="text-center py-8 text-slate-400 text-xs">
            No emergency alerts active. Create an alert if an acute danger sign is observed.
          </div>
        ) : (
          <div className="space-y-3">
            {alerts.map((alt) => {
              const isCrit = alt.severity === "CRITICAL";
              const isUrg = alt.severity === "URGENT";
              const isResolved = alt.delivery_status === "RESOLVED";

              return (
                <div
                  key={alt.alert_id}
                  className={`border rounded-xl p-4 transition space-y-2.5 ${
                    isResolved
                      ? "bg-slate-50 border-slate-200 opacity-75"
                      : isCrit
                      ? "bg-red-50/40 border-red-300"
                      : "bg-amber-50/40 border-amber-300"
                  }`}
                >
                  {/* Top row: ID, Severity, Delivery Status */}
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-xs font-bold text-slate-600 bg-white px-2 py-0.5 rounded border border-slate-200">
                        {alt.alert_id}
                      </span>
                      <span
                        className={`text-[10px] font-black px-2 py-0.5 rounded-full uppercase tracking-wider ${
                          isCrit
                            ? "bg-red-600 text-white"
                            : isUrg
                            ? "bg-amber-500 text-slate-950"
                            : "bg-slate-200 text-slate-800"
                        }`}
                      >
                        {alt.severity}
                      </span>
                    </div>

                    {/* Delivery Status Badge */}
                    <div>
                      {alt.delivery_status === "SAVED_LOCALLY" ? (
                        <span className="bg-blue-100 text-blue-900 text-[10px] font-bold px-2.5 py-0.5 rounded-full border border-blue-300 flex items-center space-x-1">
                          <Save className="w-3 h-3 text-blue-700" />
                          <span>Saved Locally (On-Device Only)</span>
                        </span>
                      ) : alt.delivery_status === "PENDING_TRANSMISSION" || alt.delivery_status === "QUEUED_OFFLINE" ? (
                        <span className="bg-amber-100 text-amber-900 text-[10px] font-bold px-2.5 py-0.5 rounded-full border border-amber-300 flex items-center space-x-1">
                          <Clock className="w-3 h-3 text-amber-700" />
                          <span>Pending Transmission (Outbox)</span>
                        </span>
                      ) : alt.delivery_status === "SENT_SUCCESSFULLY" || alt.delivery_status === "DELIVERED" ? (
                        <span className="bg-emerald-100 text-emerald-800 text-[10px] font-bold px-2.5 py-0.5 rounded-full border border-emerald-300 flex items-center space-x-1">
                          <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                          <span>Sent Successfully (Hub Reconciled)</span>
                        </span>
                      ) : alt.delivery_status === "TRANSMISSION_FAILED" ? (
                        <span className="bg-rose-100 text-rose-900 text-[10px] font-bold px-2.5 py-0.5 rounded-full border border-rose-300 flex items-center space-x-1">
                          <AlertTriangle className="w-3 h-3 text-rose-700" />
                          <span>Transmission Failed (Offline)</span>
                        </span>
                      ) : alt.delivery_status === "SERVICE_NOT_CONFIGURED" ? (
                        <span className="bg-slate-200 text-slate-800 text-[10px] font-bold px-2.5 py-0.5 rounded-full border border-slate-300 flex items-center space-x-1">
                          <Info className="w-3 h-3 text-slate-600" />
                          <span>Service Not Configured</span>
                        </span>
                      ) : (
                        <span className="bg-slate-200 text-slate-700 text-[10px] font-bold px-2.5 py-0.5 rounded-full">
                          Resolved
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Patient & Danger Presentation */}
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">
                      {alt.patient_name}{" "}
                      <span className="text-xs font-normal text-slate-500">
                        ({alt.village} • Ph: {alt.contact_phone})
                      </span>
                    </h4>
                    <div className="text-xs font-bold text-red-800 mt-1">
                      Danger Sign: {alt.symptoms}
                    </div>
                    {alt.description && (
                      <p className="text-xs text-slate-600 mt-0.5 leading-relaxed">
                        {alt.description}
                      </p>
                    )}
                    {alt.status_explanation && (
                      <div className="text-[11px] text-amber-900 bg-amber-50/80 p-2 rounded-lg border border-amber-200/60 font-medium mt-1.5">
                        <strong>Honest Transmission Status:</strong> {alt.status_explanation}
                      </div>
                    )}
                  </div>

                  {/* Action Taken & Timestamp */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-2 border-t border-slate-200/60 text-xs">
                    <span className="text-slate-500 text-[11px]">
                      Time Logged: {new Date(alt.timestamp).toLocaleString()}
                    </span>

                    <div className="flex flex-wrap items-center gap-1.5">
                      <button
                        onClick={() => handleDispatchSms(alt)}
                        className="bg-red-600 hover:bg-red-700 text-white px-2.5 py-1 rounded-lg text-xs font-bold flex items-center space-x-1 transition shadow-xs cursor-pointer"
                        title="Open native SMS pre-filled with patient details for 108"
                      >
                        <MessageSquare className="w-3 h-3" />
                        <span>GSM SMS SOS</span>
                      </button>

                      <button
                        onClick={() => handleCopyPayload(alt)}
                        className="bg-white hover:bg-slate-50 border border-slate-300 text-slate-800 px-2 py-1 rounded-lg text-xs font-semibold flex items-center space-x-1 transition cursor-pointer"
                        title="Copy GPS coordinates & symptoms to clipboard"
                      >
                        <Copy className="w-3 h-3 text-slate-600" />
                        <span>Copy SOS</span>
                      </button>

                      <a
                        href={`tel:${alt.contact_phone}`}
                        className="bg-white hover:bg-slate-50 border border-slate-300 text-slate-800 px-2.5 py-1 rounded-lg text-xs font-semibold flex items-center space-x-1 transition"
                      >
                        <PhoneCall className="w-3 h-3" />
                        <span>Call</span>
                      </a>

                      {!isResolved && (
                        <button
                          onClick={() =>
                            handleUpdateStatus(
                              alt.alert_id,
                              "RESOLVED",
                              "Patient stabilized and transferred to CHC."
                            )
                          }
                          className="bg-emerald-700 hover:bg-emerald-800 text-white px-2.5 py-1 rounded-lg text-xs font-bold transition shadow-xs cursor-pointer"
                        >
                          Resolve
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Record Emergency Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-3 z-50">
          <div className="bg-white rounded-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto shadow-2xl border border-slate-200 p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <div className="flex items-center space-x-2 text-red-700">
                <ShieldAlert className="w-5 h-5 text-red-600" />
                <h3 className="text-base font-bold text-slate-900">
                  Record Emergency Triage Event
                </h3>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
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

            <form onSubmit={handleCreateAlert} className="space-y-3 text-xs">
              <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">
                  Patient Full Name *
                </label>
                <input
                  type="text"
                  value={patientName}
                  onChange={(e) => setPatientName(e.target.value)}
                  placeholder="e.g. Kumari Devi"
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
                    {villages.map((v) => (
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

              <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">
                  Severity Level
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {(["CRITICAL", "URGENT", "ROUTINE"] as const).map((sev) => (
                    <button
                      key={sev}
                      type="button"
                      onClick={() => setSeverity(sev)}
                      className={`p-2 rounded-lg font-bold text-xs border text-center transition ${
                        severity === sev
                          ? sev === "CRITICAL"
                            ? "bg-red-600 text-white border-red-700 shadow-xs"
                            : sev === "URGENT"
                            ? "bg-amber-500 text-slate-950 border-amber-600 shadow-xs"
                            : "bg-teal-600 text-white border-teal-700 shadow-xs"
                          : "bg-slate-50 text-slate-700 border-slate-300 hover:bg-slate-100"
                      }`}
                    >
                      {sev}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">
                  Clinical Symptoms / Danger Signs *
                </label>
                <input
                  type="text"
                  value={symptoms}
                  onChange={(e) => setSymptoms(e.target.value)}
                  placeholder="e.g. Heavy vaginal bleeding in 7th month, convulsion, tachypnea rr>=60"
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900"
                  required
                />
              </div>

              <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">
                  Field Observations & Immediate Actions
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="e.g. Patient placed in left lateral tilt, family instructed to call 108 ambulance."
                  rows={3}
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900"
                />
              </div>

              <div className="bg-red-50 border border-red-200 p-3 rounded-lg text-xs text-red-900">
                <strong>Mandatory Protocol:</strong> Submitting this form logs the emergency event in the device outbox. You MUST also call <strong>108 (Ambulance)</strong> directly on your mobile.
              </div>

              <div className="flex justify-end space-x-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-xl text-xs transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-bold rounded-xl text-xs transition shadow-sm flex items-center space-x-1.5"
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>Log Emergency Locally</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
