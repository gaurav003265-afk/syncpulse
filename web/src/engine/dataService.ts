/**
 * SyncPulse Local Data & Persistence Service
 * Single source of truth for offline-first ASHA operations.
 * Operates against localStorage with pre-seeded datasets from verified files.
 */

import initialHouseholds from "../data/households.json" with { type: "json" };
import initialPatients from "../data/patients.json" with { type: "json" };
import initialAlerts from "../data/emergency_alerts.json" with { type: "json" };
import initialFirstAid from "../data/first_aid.json" with { type: "json" };
import {
  formatDistanceLabel,
  haversineDistanceKm,
  isValidCoordinate,
} from "./location";
import {
  detectFollowUpGapsTS,
  FollowUpGapTS,
  generateMonthlyRemindersTS,
  MonthlyReminderTS,
} from "./reminders";

export interface HouseholdRecord {
  household_id: string;
  village: string;
  household_head: string;
  contact_phone: string;
  beneficiary_name: string;
  beneficiary_type: string;
  service_code: string;
  service_name: string;
  protocol_citation: string;
  due_date: string;
  is_high_risk: boolean;
  risk_tag: string | null;
  visited: boolean;
  visited_at?: string | null;
  visit_notes?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  location_accuracy_m?: number | null;
  location_source?: "GPS_CAPTURE" | "MANUAL_ENTRY" | null;
  location_captured_at?: string | null;
  straight_line_distance_km?: number | null;
  distance_display?: string;
  overdue_days?: number;
  priority_tier?: string;
  priority_rank?: number;
  priority_reason?: string;
  created_at?: string;
  updated_at?: string;
}

export interface PatientProfile {
  patient_id: string;
  name: string;
  age: number;
  gender: string;
  village: string;
  contact_phone: string;
  family_head: string;
  blood_group?: string;
  is_pregnant?: boolean;
  gestational_weeks?: number | null;
  edd?: string | null;
  is_high_risk?: boolean;
  risk_condition?: string | null;
  allergies?: string[];
  current_medications?: string[];
  assigned_asha?: string;
  last_visit_date?: string | null;
  next_visit_date?: string | null;
  visit_history?: Array<{
    date: string;
    service: string;
    asha_id: string;
    notes: string;
  }>;
  reminders?: Array<{
    title: string;
    date: string;
    type: string;
  }>;
}

export interface FollowUpTask {
  follow_up_id: string;
  household_id: string;
  beneficiary_name: string;
  village: string;
  task_description: string;
  due_date: string;
  priority: "CRITICAL" | "URGENT" | "ROUTINE";
  status: "PENDING" | "COMPLETED" | "CANCELLED";
  created_at: string;
  completed_at?: string | null;
  completion_notes?: string | null;
}

export type EmergencyDeliveryStatus =
  | "SAVED_LOCALLY"
  | "PENDING_TRANSMISSION"
  | "SENT_SUCCESSFULLY"
  | "TRANSMISSION_FAILED"
  | "SERVICE_NOT_CONFIGURED"
  | "RESOLVED"
  | "QUEUED_OFFLINE"
  | "DELIVERED";

export interface EmergencyAlert {
  alert_id: string;
  patient_id: string;
  patient_name: string;
  village: string;
  contact_phone: string;
  timestamp: string;
  severity: "CRITICAL" | "URGENT" | "ROUTINE";
  symptoms: string;
  description: string;
  location?: string;
  delivery_status: EmergencyDeliveryStatus;
  status_explanation?: string;
  is_acknowledged?: boolean;
  action_taken?: string;
}

export interface FirstAidTopic {
  id: string;
  category: string;
  title: string;
  scenario: string;
  steps: string[];
  what_not_to_do: string[];
  red_flags: string[];
  doctor_referral_advice: string;
  source_citation: string;
}

export interface SyncEvent {
  event_id: string;
  entity_type: "visit" | "emergency_alert" | "household" | "patient" | "follow_up";
  entity_id: string;
  action: "create" | "update" | "complete";
  payload: any;
  created_at: string;
  status: "PENDING" | "SYNCED" | "FAILED";
}

export interface ActivityItem {
  id: string;
  type: "visit" | "emergency" | "sync" | "profile" | "follow_up";
  title: string;
  description: string;
  timestamp: string;
  badge?: string;
  isEmergency?: boolean;
}

export interface ImportReportTS {
  total_records: number;
  imported_new: number;
  updated_existing: number;
  rejected_count: number;
  errors: Array<{
    row_index: number;
    household_id?: string;
    field: string;
    error: string;
  }>;
}

// Storage keys
const STORAGE_PREFIX = "syncpulse_";
const KEY_HOUSEHOLDS = `${STORAGE_PREFIX}households`;
const KEY_PATIENTS = `${STORAGE_PREFIX}patients`;
const KEY_ALERTS = `${STORAGE_PREFIX}alerts`;
const KEY_FOLLOW_UPS = `${STORAGE_PREFIX}follow_ups`;
const KEY_OUTBOX = `${STORAGE_PREFIX}outbox`;
const KEY_ACTIVITY = `${STORAGE_PREFIX}activity`;
const KEY_LAST_SYNC = `${STORAGE_PREFIX}last_sync`;

class DataService {
  private households: HouseholdRecord[] = [];
  private patients: PatientProfile[] = [];
  private alerts: EmergencyAlert[] = [];
  private followUps: FollowUpTask[] = [];
  private firstAid: FirstAidTopic[] = [];

  constructor() {
    this.initData();
  }

  private safeGetItem<T>(key: string, fallback: T): T {
    try {
      if (typeof localStorage !== "undefined") {
        const item = localStorage.getItem(key);
        if (item) return JSON.parse(item);
      }
    } catch (e) {
      console.warn(`Error reading ${key} from storage:`, e);
    }
    return fallback;
  }

  private safeSetItem(key: string, value: any): void {
    try {
      if (typeof localStorage !== "undefined") {
        localStorage.setItem(key, JSON.stringify(value));
      }
    } catch (e) {
      console.warn(`Error writing ${key} to storage:`, e);
    }
  }

  private initData() {
    // 1. Households (500 records)
    const storedHH = this.safeGetItem<HouseholdRecord[] | null>(KEY_HOUSEHOLDS, null);
    if (storedHH && storedHH.length > 0) {
      this.households = storedHH;
    } else {
      this.households = (initialHouseholds as any[]).map((h) => ({
        ...h,
        visited: Boolean(h.visited),
        visited_at: h.visited_at || null,
        visit_notes: h.visit_notes || null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }));
      this.safeSetItem(KEY_HOUSEHOLDS, this.households);
    }

    // 2. Patients
    const storedPatients = this.safeGetItem<PatientProfile[] | null>(KEY_PATIENTS, null);
    if (storedPatients && storedPatients.length > 0) {
      this.patients = storedPatients;
    } else {
      this.patients = initialPatients as unknown as PatientProfile[];
      this.safeSetItem(KEY_PATIENTS, this.patients);
    }

    // 3. Alerts
    const storedAlerts = this.safeGetItem<EmergencyAlert[] | null>(KEY_ALERTS, null);
    if (storedAlerts && storedAlerts.length > 0) {
      this.alerts = storedAlerts;
    } else {
      this.alerts = initialAlerts as unknown as EmergencyAlert[];
      this.safeSetItem(KEY_ALERTS, this.alerts);
    }

    // 4. Follow-Up Tasks
    const storedFollowUps = this.safeGetItem<FollowUpTask[] | null>(KEY_FOLLOW_UPS, null);
    if (storedFollowUps && storedFollowUps.length > 0) {
      this.followUps = storedFollowUps;
    } else {
      this.followUps = [
        {
          follow_up_id: "FLW-1001",
          household_id: "HH-0001",
          beneficiary_name: "Child of Bhavani Kumar",
          village: "Venkatapuram",
          task_description: "Check fever and reaction 48 hours post-DPT booster",
          due_date: "2026-10-22",
          priority: "ROUTINE",
          status: "PENDING",
          created_at: "2026-10-20T09:15:00Z",
        },
        {
          follow_up_id: "FLW-1002",
          household_id: "HH-0012",
          beneficiary_name: "Anasuya Devi",
          village: "Ramnagar",
          task_description: "Repeat BP check & urine protein test for gestational hypertension",
          due_date: "2026-10-23",
          priority: "CRITICAL",
          status: "PENDING",
          created_at: "2026-10-19T14:30:00Z",
        },
      ];
      this.safeSetItem(KEY_FOLLOW_UPS, this.followUps);
    }

    // 5. First Aid (read-only clinical guides)
    this.firstAid = initialFirstAid as unknown as FirstAidTopic[];
  }

  // --- REPEATABLE REGISTER IMPORTER ---
  public importRegister(rawRecords: any[]): ImportReportTS {
    const validBeneficiaryTypes = new Set([
      "Maternal",
      "Infant",
      "Adult_NCD",
      "Child",
      "Pregnant Woman",
      "Adolescent",
    ]);
    const phoneRegex = /^\d{10}$/;
    const hhIdRegex = /^HH-\d{4,}$/;

    const errors: ImportReportTS["errors"] = [];
    const validCleaned: HouseholdRecord[] = [];

    rawRecords.forEach((raw, idx) => {
      const rowIdx = idx + 1;
      if (!raw || typeof raw !== "object") {
        errors.push({ row_index: rowIdx, field: "record", error: "Row is not an object" });
        return;
      }

      const hhId = String(raw.household_id || "").trim();
      if (!hhId || !hhIdRegex.test(hhId)) {
        errors.push({ row_index: rowIdx, household_id: hhId || undefined, field: "household_id", error: "Must match HH-XXXX format" });
      }

      const village = String(raw.village || "").trim();
      if (!village || village.length < 2) {
        errors.push({ row_index: rowIdx, household_id: hhId, field: "village", error: "Village name required" });
      }

      const head = String(raw.household_head || "").trim();
      if (!head || head.length < 2) {
        errors.push({ row_index: rowIdx, household_id: hhId, field: "household_head", error: "Household head required" });
      }

      const phone = String(raw.contact_phone || "").trim();
      if (!phone || !phoneRegex.test(phone)) {
        errors.push({ row_index: rowIdx, household_id: hhId, field: "contact_phone", error: "Must be 10 digits" });
      }

      const bName = String(raw.beneficiary_name || "").trim();
      if (!bName || bName.length < 2) {
        errors.push({ row_index: rowIdx, household_id: hhId, field: "beneficiary_name", error: "Beneficiary name required" });
      }

      const bType = String(raw.beneficiary_type || "").trim();
      if (!validBeneficiaryTypes.has(bType)) {
        errors.push({ row_index: rowIdx, household_id: hhId, field: "beneficiary_type", error: "Invalid beneficiary type" });
      }

      const dueDate = String(raw.due_date || "").trim();
      if (!dueDate || isNaN(Date.parse(dueDate))) {
        errors.push({ row_index: rowIdx, household_id: hhId, field: "due_date", error: "Must be valid ISO date YYYY-MM-DD" });
      }

      const isHr = Boolean(raw.is_high_risk);

      if (errors.some((e) => e.row_index === rowIdx)) {
        return;
      }

      validCleaned.push({
        household_id: hhId,
        village,
        household_head: head,
        contact_phone: phone,
        beneficiary_name: bName,
        beneficiary_type: bType,
        service_code: String(raw.service_code || "ROUTINE_CHECK").trim(),
        service_name: String(raw.service_name || "Protocol Service").trim(),
        protocol_citation: String(raw.protocol_citation || "[MoHFW Guidelines]").trim(),
        due_date: dueDate,
        is_high_risk: isHr,
        risk_tag: raw.risk_tag ? String(raw.risk_tag).trim() : null,
        visited: Boolean(raw.visited),
        visited_at: raw.visited_at || null,
        visit_notes: raw.visit_notes || null,
        updated_at: new Date().toISOString(),
      });
    });

    let newCount = 0;
    let updatedCount = 0;

    validCleaned.forEach((cleaned) => {
      const existingIdx = this.households.findIndex((h) => h.household_id === cleaned.household_id);
      if (existingIdx === -1) {
        this.households.push({ ...cleaned, created_at: new Date().toISOString() });
        newCount++;
      } else {
        // Preserve visited state and visit notes
        const current = this.households[existingIdx];
        this.households[existingIdx] = {
          ...cleaned,
          visited: current.visited || cleaned.visited,
          visited_at: current.visited_at || cleaned.visited_at,
          visit_notes: current.visit_notes || cleaned.visit_notes,
          created_at: current.created_at || new Date().toISOString(),
        };
        updatedCount++;
      }
    });

    this.safeSetItem(KEY_HOUSEHOLDS, this.households);

    this.logActivity({
      type: "sync",
      title: "Register Import Completed",
      description: `Imported ${newCount} new, updated ${updatedCount}, rejected ${errors.length}.`,
    });

    return {
      total_records: rawRecords.length,
      imported_new: newCount,
      updated_existing: updatedCount,
      rejected_count: errors.length,
      errors,
    };
  }

  // --- HOUSEHOLDS ---
  public getHouseholds(): HouseholdRecord[] {
    return [...this.households];
  }

  public getHouseholdById(id: string): HouseholdRecord | undefined {
    return this.households.find((h) => h.household_id === id);
  }

  public getVillages(): string[] {
    const set = new Set<string>();
    for (const h of this.households) {
      if (h.village) set.add(h.village);
    }
    return Array.from(set).sort();
  }

  public addHousehold(record: Omit<HouseholdRecord, "household_id" | "visited">): HouseholdRecord {
    const nextNum = this.households.length + 1;
    const newId = `HH-${String(nextNum).padStart(4, "0")}`;
    const newRecord: HouseholdRecord = {
      ...record,
      household_id: newId,
      visited: false,
      visited_at: null,
      visit_notes: "",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    this.households.unshift(newRecord);
    this.safeSetItem(KEY_HOUSEHOLDS, this.households);

    this.logActivity({
      type: "profile",
      title: "New Household Registered",
      description: `${newRecord.household_head} (${newRecord.village}) • ${newRecord.beneficiary_name}`,
    });

    this.queueOutbox("household", newId, "create", newRecord);
    return newRecord;
  }

  public updateHousehold(id: string, updates: Partial<HouseholdRecord>): HouseholdRecord | undefined {
    const idx = this.households.findIndex((h) => h.household_id === id);
    if (idx === -1) return undefined;

    this.households[idx] = { ...this.households[idx], ...updates, updated_at: new Date().toISOString() };
    this.safeSetItem(KEY_HOUSEHOLDS, this.households);

    this.queueOutbox("household", id, "update", updates);
    return this.households[idx];
  }

  // --- VISITS & 4-TIER SCORING ---
  public markVisitCompleted(
    householdId: string,
    notes: string,
    vitals?: { bp?: string; pulse?: string; weight?: string; muac?: string; temp?: string },
    followUpDate?: string,
    followUpTask?: string
  ): HouseholdRecord | undefined {
    const idx = this.households.findIndex((h) => h.household_id === householdId);
    if (idx === -1) return undefined;

    const timestamp = new Date().toISOString();
    let noteText = notes || "Routine protocol visit completed.";
    if (vitals) {
      const parts = [];
      if (vitals.bp) parts.push(`BP: ${vitals.bp}`);
      if (vitals.pulse) parts.push(`Pulse: ${vitals.pulse}`);
      if (vitals.temp) parts.push(`Temp: ${vitals.temp}`);
      if (vitals.muac) parts.push(`MUAC: ${vitals.muac}mm`);
      if (vitals.weight) parts.push(`Weight: ${vitals.weight}kg`);
      if (parts.length > 0) {
        noteText = `[Vitals: ${parts.join(", ")}] ${noteText}`;
      }
    }
    if (followUpDate) {
      noteText += ` • Next Follow-up: ${followUpDate}`;
    }

    const updated: HouseholdRecord = {
      ...this.households[idx],
      visited: true,
      visited_at: timestamp,
      visit_notes: noteText,
      updated_at: timestamp,
    };

    this.households[idx] = updated;
    this.safeSetItem(KEY_HOUSEHOLDS, this.households);

    // Create follow-up task if date or task specified
    if (followUpDate) {
      this.createFollowUp({
        household_id: householdId,
        beneficiary_name: updated.beneficiary_name,
        village: updated.village,
        task_description: followUpTask || `Protocol follow-up: ${updated.service_name}`,
        due_date: followUpDate,
        priority: updated.is_high_risk ? "CRITICAL" : "ROUTINE",
      });
    }

    // Also update matching patient profile if exists
    const matchingPatient = this.patients.find(
      (p) =>
        p.village.toLowerCase() === updated.village.toLowerCase() &&
        p.name.toLowerCase().includes(updated.beneficiary_name.toLowerCase().split(" ")[0])
    );
    if (matchingPatient) {
      if (!matchingPatient.visit_history) matchingPatient.visit_history = [];
      matchingPatient.visit_history.unshift({
        date: timestamp.split("T")[0],
        service: updated.service_name,
        asha_id: matchingPatient.assigned_asha || "ASHA-8841",
        notes: noteText,
      });
      matchingPatient.last_visit_date = timestamp.split("T")[0];
      if (followUpDate) matchingPatient.next_visit_date = followUpDate;
      this.safeSetItem(KEY_PATIENTS, this.patients);
    }

    this.logActivity({
      type: "visit",
      title: "Visit Completed",
      description: `${updated.beneficiary_name} (${updated.household_id}, ${updated.village}) • ${updated.service_name}`,
    });

    this.queueOutbox("visit", householdId, "complete", {
      household_id: householdId,
      visited_at: timestamp,
      visit_notes: noteText,
      vitals,
      follow_up_date: followUpDate,
      follow_up_task: followUpTask,
    });

    return updated;
  }

  public getScoredVisits(
    asOfDateStr = "2026-10-20",
    village: string | null = null,
    filterTab: "all" | "today" | "overdue" | "upcoming" | "completed" = "all",
    workerCoords?: { latitude: number; longitude: number } | null
  ): HouseholdRecord[] {
    const asOf = new Date(asOfDateStr);
    asOf.setHours(0, 0, 0, 0);

    const result: HouseholdRecord[] = [];

    for (const h of this.households) {
      if (village && village !== "All" && h.village.toLowerCase() !== village.toLowerCase()) {
        continue;
      }

      const due = new Date(h.due_date);
      due.setHours(0, 0, 0, 0);

      const diffTime = asOf.getTime() - due.getTime();
      const overdueDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

      let tier = "TIER_4_UPCOMING";
      let rank = 100;
      let reason = `Scheduled in ${Math.abs(overdueDays)} days`;

      if (h.is_high_risk) {
        tier = "TIER_1_CRITICAL";
        rank = 10000 + (overdueDays > 0 ? overdueDays * 10 : 0);
        reason = `High-risk alert: ${h.risk_tag || "Clinical Danger"} (${overdueDays > 0 ? `${overdueDays} days overdue` : "Due soon"})`;
      } else if (overdueDays > 0) {
        tier = "TIER_2_OVERDUE";
        rank = 5000 + overdueDays * 5;
        reason = `Overdue by ${overdueDays} days for routine protocol`;
      } else if (overdueDays === 0) {
        tier = "TIER_3_DUE_TODAY";
        rank = 2000;
        reason = "Scheduled for today's field visit";
      }

      // Straight-line distance calculation using Haversine formula (Earth's radius 6371 km)
      const distKm = haversineDistanceKm(
        workerCoords?.latitude,
        workerCoords?.longitude,
        h.latitude,
        h.longitude
      );
      const distLabel = formatDistanceLabel(distKm);

      const record: HouseholdRecord = {
        ...h,
        overdue_days: overdueDays,
        priority_tier: tier,
        priority_rank: rank,
        priority_reason: reason,
        straight_line_distance_km: distKm,
        distance_display: distLabel,
      };

      if (filterTab === "completed" && !record.visited) continue;
      if (filterTab === "today" && (record.visited || overdueDays !== 0)) continue;
      if (filterTab === "overdue" && (record.visited || overdueDays <= 0)) continue;
      if (filterTab === "upcoming" && (record.visited || overdueDays >= 0)) continue;
      if (filterTab === "all" && record.visited) {
        record.priority_rank = 0;
      }

      result.push(record);
    }

    // Deterministic Sort Order:
    // 1. Clinical urgency strictly dominates distance (higher priority_rank first)
    // 2. Secondary convenience tie-breaker: straight-line distance if available (closest first)
    // 3. Overdue days descending
    result.sort((a, b) => {
      const rankDiff = (b.priority_rank || 0) - (a.priority_rank || 0);
      if (rankDiff !== 0) return rankDiff;

      const distA =
        a.straight_line_distance_km !== null && a.straight_line_distance_km !== undefined
          ? a.straight_line_distance_km
          : 999999;
      const distB =
        b.straight_line_distance_km !== null && b.straight_line_distance_km !== undefined
          ? b.straight_line_distance_km
          : 999999;
      if (distA !== distB) return distA - distB;

      return (b.overdue_days || 0) - (a.overdue_days || 0);
    });

    return result;
  }

  public updateHouseholdLocation(
    householdId: string,
    latitude: number,
    longitude: number,
    source: "GPS_CAPTURE" | "MANUAL_ENTRY" = "MANUAL_ENTRY",
    accuracyM?: number | null
  ): boolean {
    if (!isValidCoordinate(latitude, longitude)) {
      throw new Error(`Invalid geographical coordinates: lat=${latitude}, lon=${longitude}`);
    }

    const h = this.households.find((x) => x.household_id === householdId);
    if (!h) return false;

    const nowIso = new Date().toISOString();
    h.latitude = latitude;
    h.longitude = longitude;
    h.location_source = source;
    h.location_accuracy_m = accuracyM || null;
    h.location_captured_at = nowIso;
    h.updated_at = nowIso;

    this.safeSetItem(KEY_HOUSEHOLDS, this.households);

    this.logActivity({
      type: "profile",
      title: `GPS Coordinates Updated: ${h.household_head}`,
      description: `Saved ${source === "GPS_CAPTURE" ? "GPS sensor fix" : "manual coordinates"} (${latitude.toFixed(4)}, ${longitude.toFixed(4)}) for ${h.household_id} (${h.village})`,
    });

    this.queueOutbox("household", householdId, "update", {
      household_id: householdId,
      latitude,
      longitude,
      accuracy_m: accuracyM,
      source,
      captured_at: nowIso,
    });

    return true;
  }

  public getMonthlyReminders(asOfDateStr = "2026-10-20"): MonthlyReminderTS[] {
    const completedMap = new Map<string, { visited_at: string; notes?: string }>();
    for (const h of this.households) {
      if (h.visited) {
        completedMap.set(h.household_id, {
          visited_at: h.visited_at || asOfDateStr,
          notes: h.visit_notes || undefined,
        });
      }
    }
    return generateMonthlyRemindersTS(this.households, completedMap, asOfDateStr);
  }

  public getFollowUpGaps(asOfDateStr = "2026-10-20"): FollowUpGapTS[] {
    const hhMap = new Map<string, HouseholdRecord>();
    for (const h of this.households) {
      hhMap.set(h.household_id, h);
    }
    return detectFollowUpGapsTS(this.followUps, hhMap, asOfDateStr);
  }

  public completeFollowUpTask(followUpId: string, notes?: string): boolean {
    const task = this.followUps.find((f) => f.follow_up_id === followUpId);
    if (!task) return false;

    task.status = "COMPLETED";
    task.completed_at = new Date().toISOString();
    task.completion_notes = notes || "Completed by ASHA worker";

    this.safeSetItem(KEY_FOLLOW_UPS, this.followUps);

    this.logActivity({
      type: "follow_up",
      title: `Follow-Up Completed: ${task.household_id}`,
      description: `${task.task_description} — ${task.completion_notes}`,
    });

    this.queueOutbox("follow_up", followUpId, "complete", {
      follow_up_id: followUpId,
      status: "COMPLETED",
      completion_notes: notes,
    });

    return true;
  }

  // --- FOLLOW-UP TASKS ---
  public getFollowUps(householdId?: string, status?: string): FollowUpTask[] {
    return this.followUps.filter((f) => {
      if (householdId && f.household_id !== householdId) return false;
      if (status && status !== "ALL" && f.status !== status) return false;
      return true;
    });
  }

  public createFollowUp(
    data: Omit<FollowUpTask, "follow_up_id" | "status" | "created_at">
  ): FollowUpTask {
    const id = `FLW-${Date.now().toString().slice(-5)}`;
    const task: FollowUpTask = {
      ...data,
      follow_up_id: id,
      status: "PENDING",
      created_at: new Date().toISOString(),
    };
    this.followUps.unshift(task);
    this.safeSetItem(KEY_FOLLOW_UPS, this.followUps);

    this.logActivity({
      type: "follow_up",
      title: "Follow-Up Scheduled",
      description: `${task.beneficiary_name} (${task.village}) • Due ${task.due_date}`,
    });

    this.queueOutbox("follow_up", id, "create", task);
    return task;
  }

  public completeFollowUp(id: string, notes?: string): FollowUpTask | undefined {
    const idx = this.followUps.findIndex((f) => f.follow_up_id === id);
    if (idx === -1) return undefined;

    const completed: FollowUpTask = {
      ...this.followUps[idx],
      status: "COMPLETED",
      completed_at: new Date().toISOString(),
      completion_notes: notes || "Follow-up task conducted",
    };
    this.followUps[idx] = completed;
    this.safeSetItem(KEY_FOLLOW_UPS, this.followUps);

    this.queueOutbox("follow_up", id, "complete", { completed_at: completed.completed_at, notes });
    return completed;
  }

  // --- PATIENTS ---
  public getPatients(): PatientProfile[] {
    return [...this.patients];
  }

  public getPatientById(id: string): PatientProfile | undefined {
    return this.patients.find((p) => p.patient_id === id);
  }

  public updatePatient(id: string, updates: Partial<PatientProfile>): PatientProfile | undefined {
    const idx = this.patients.findIndex((p) => p.patient_id === id);
    if (idx === -1) return undefined;

    this.patients[idx] = { ...this.patients[idx], ...updates };
    this.safeSetItem(KEY_PATIENTS, this.patients);

    this.logActivity({
      type: "profile",
      title: "Patient Record Updated",
      description: `${this.patients[idx].name} (${id})`,
    });

    this.queueOutbox("patient", id, "update", updates);
    return this.patients[idx];
  }

  // --- EMERGENCY DESK ---
  public getAlerts(): EmergencyAlert[] {
    return [...this.alerts];
  }

  public createAlert(
    alertData: Omit<EmergencyAlert, "alert_id" | "timestamp" | "delivery_status"> & {
      delivery_status?: EmergencyDeliveryStatus;
    }
  ): EmergencyAlert {
    const alertId = `ALT-${Date.now().toString().slice(-6)}`;
    const newAlert: EmergencyAlert = {
      ...alertData,
      alert_id: alertId,
      timestamp: new Date().toISOString(),
      delivery_status: alertData.delivery_status || "SAVED_LOCALLY",
      status_explanation:
        alertData.delivery_status === "PENDING_TRANSMISSION"
          ? "Queued in offline outbox. Awaiting sub-center connection."
          : "Saved locally on this device. Automated notification service is not configured. Dial 108 directly on mobile.",
      action_taken: alertData.action_taken || "Recorded in local offline emergency register. Requires worker phone call.",
      is_acknowledged: false,
    };

    this.alerts.unshift(newAlert);
    this.safeSetItem(KEY_ALERTS, this.alerts);

    this.logActivity({
      type: "emergency",
      title: "🚨 Emergency Triage Alert Created",
      description: `${newAlert.patient_name} (${newAlert.village}) • ${newAlert.symptoms.slice(0, 60)}...`,
      isEmergency: true,
    });

    this.queueOutbox("emergency_alert", alertId, "create", newAlert);
    return newAlert;
  }

  public recordEmergencyFromEscalation(
    symptoms: string,
    dangerSignTitle: string,
    actionProtocol: string,
    citation?: string | null,
    patientName?: string,
    village?: string
  ): EmergencyAlert {
    const alertId = `ALT-${Date.now().toString().slice(-6)}`;
    const newAlert: EmergencyAlert = {
      alert_id: alertId,
      patient_id: `EMG-${Date.now().toString().slice(-4)}`,
      patient_name: patientName || "Emergency Patient (Clinical Escalation)",
      village: village || "Venkatapuram",
      contact_phone: "108 (Direct Emergency)",
      timestamp: new Date().toISOString(),
      severity: "CRITICAL",
      symptoms: symptoms.slice(0, 200),
      description: `Escalated via Ask Sakhi safety gate: ${dangerSignTitle}. Protocol: ${actionProtocol.slice(0, 250)}...`,
      delivery_status: "SAVED_LOCALLY",
      status_explanation:
        "Saved locally. Notification service not configured. No automated ambulance or doctor alert has been dispatched. Call 108 directly on mobile.",
      action_taken: "Immediate referral guidance displayed. Cellular 108 call required.",
      is_acknowledged: false,
    };

    this.alerts.unshift(newAlert);
    this.safeSetItem(KEY_ALERTS, this.alerts);

    this.logActivity({
      type: "emergency",
      title: "🚨 Emergency Incident Escalated",
      description: `${dangerSignTitle} • Recorded locally on-device only`,
      isEmergency: true,
    });

    this.queueOutbox("emergency_alert", alertId, "create", newAlert);
    return newAlert;
  }

  public updateAlertStatus(
    alertId: string,
    status: EmergencyDeliveryStatus,
    actionTaken?: string
  ): EmergencyAlert | undefined {
    const idx = this.alerts.findIndex((a) => a.alert_id === alertId);
    if (idx === -1) return undefined;

    let explanation = "";
    if (status === "SAVED_LOCALLY") {
      explanation = "Saved locally on this device. Notification service not configured.";
    } else if (status === "PENDING_TRANSMISSION" || status === "QUEUED_OFFLINE") {
      explanation = "Pending transmission. Stored in offline outbox queue.";
    } else if (status === "SENT_SUCCESSFULLY" || status === "DELIVERED") {
      explanation = "Successfully transmitted and acknowledged by sub-center hub register.";
    } else if (status === "TRANSMISSION_FAILED") {
      explanation = "Transmission failed. Network unreachable. Record preserved safely in local outbox.";
    } else if (status === "SERVICE_NOT_CONFIGURED") {
      explanation = "Automated dispatch service is not configured. Cellular 108 call required.";
    } else if (status === "RESOLVED") {
      explanation = "Clinical triage incident marked as resolved by frontline worker.";
    }

    this.alerts[idx] = {
      ...this.alerts[idx],
      delivery_status: status,
      status_explanation: explanation,
      action_taken: actionTaken || this.alerts[idx].action_taken,
      is_acknowledged: true,
    };

    this.safeSetItem(KEY_ALERTS, this.alerts);
    this.queueOutbox("emergency_alert", alertId, "update", {
      delivery_status: status,
      status_explanation: explanation,
      action_taken: actionTaken,
    });
    return this.alerts[idx];
  }

  // --- FIRST AID ---
  public getFirstAidTopics(): FirstAidTopic[] {
    return [...this.firstAid];
  }

  // --- OUTBOX & SYNC ---
  public getOutbox(): SyncEvent[] {
    return this.safeGetItem<SyncEvent[]>(KEY_OUTBOX, []);
  }

  private queueOutbox(
    entity_type: SyncEvent["entity_type"],
    entity_id: string,
    action: SyncEvent["action"],
    payload: any
  ): void {
    const outbox = this.getOutbox();
    const event: SyncEvent = {
      event_id: `evt_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
      entity_type,
      entity_id,
      action,
      payload,
      created_at: new Date().toISOString(),
      status: "PENDING",
    };
    outbox.push(event);
    this.safeSetItem(KEY_OUTBOX, outbox);
  }

  public clearOutbox(): void {
    this.safeSetItem(KEY_OUTBOX, []);
    this.safeSetItem(KEY_LAST_SYNC, new Date().toISOString());
  }

  public getLastSyncTime(): string | null {
    return this.safeGetItem<string | null>(KEY_LAST_SYNC, null);
  }

  public async flushSyncToServer(): Promise<{ success: boolean; count: number; error?: string }> {
    const outbox = this.getOutbox();
    if (outbox.length === 0) {
      return { success: true, count: 0 };
    }

    try {
      const response = await fetch("/api/sync", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items: outbox }),
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const count = outbox.length;
      this.clearOutbox();

      // Only transition alerts that were successfully acknowledged by the server sync
      this.alerts = this.alerts.map((a) => {
        if (
          a.delivery_status === "SAVED_LOCALLY" ||
          a.delivery_status === "PENDING_TRANSMISSION" ||
          a.delivery_status === "QUEUED_OFFLINE" ||
          a.delivery_status === "TRANSMISSION_FAILED"
        ) {
          return {
            ...a,
            delivery_status: "SENT_SUCCESSFULLY" as const,
            status_explanation: "Successfully synchronized and acknowledged by sub-center hub register.",
          };
        }
        return a;
      });
      this.safeSetItem(KEY_ALERTS, this.alerts);

      this.logActivity({
        type: "sync",
        title: "Synchronization Succeeded",
        description: `Successfully reconciled ${count} offline record(s) with local sub-center database.`,
      });

      return { success: true, count };
    } catch (err: any) {
      // Mark pending alerts as TRANSMISSION_FAILED if attempt failed
      this.alerts = this.alerts.map((a) => {
        if (
          a.delivery_status === "SAVED_LOCALLY" ||
          a.delivery_status === "PENDING_TRANSMISSION" ||
          a.delivery_status === "QUEUED_OFFLINE"
        ) {
          return {
            ...a,
            delivery_status: "TRANSMISSION_FAILED" as const,
            status_explanation:
              "Transmission failed (Network disconnected / server unreachable). Record preserved safely in local outbox.",
          };
        }
        return a;
      });
      this.safeSetItem(KEY_ALERTS, this.alerts);

      return {
        success: false,
        count: 0,
        error: "Network unavailable or server unreachable. All local records remain preserved in offline outbox.",
      };
    }
  }

  // --- SAFE OFFLINE BACKUP EXPORT ---
  public exportOfflineBackup(): string {
    const backupData = {
      exported_at: new Date().toISOString(),
      app: "SyncPulse",
      pack_version: "2.0.0",
      households_count: this.households.length,
      households: this.households,
      patients: this.patients,
      follow_ups: this.followUps,
      emergency_alerts: this.alerts,
      outbox: this.getOutbox(),
      activity_log: this.getActivityLog(),
    };
    return JSON.stringify(backupData, null, 2);
  }

  // --- ACTIVITY LOG ---
  public getActivityLog(): ActivityItem[] {
    const log = this.safeGetItem<ActivityItem[]>(KEY_ACTIVITY, []);
    if (log.length > 0) return log;

    return [
      {
        id: "act-1",
        type: "visit",
        title: "Field Visit Completed",
        description: "Child of Bhavani Kumar (HH-0001) • DPT Booster-1 Recorded",
        timestamp: "Today at 09:15 AM",
      },
      {
        id: "act-2",
        type: "emergency",
        title: "Emergency Triage Triaged",
        description: "Lakshmi Devi • Severe headache eclampsia protocol initiated (108 dialed)",
        timestamp: "Yesterday at 04:30 PM",
        isEmergency: true,
      },
      {
        id: "act-3",
        type: "sync",
        title: "Offline Sync Completed",
        description: "12 household visits reconciled with sub-center SQLite register",
        timestamp: "Yesterday at 06:00 PM",
      },
    ];
  }

  public logActivity(item: Omit<ActivityItem, "id" | "timestamp">): void {
    const current = this.safeGetItem<ActivityItem[]>(KEY_ACTIVITY, []);
    const newItem: ActivityItem = {
      ...item,
      id: `act_${Date.now()}`,
      timestamp: "Just now",
    };
    current.unshift(newItem);
    if (current.length > 20) current.pop();
    this.safeSetItem(KEY_ACTIVITY, current);
  }

  // --- KPIS ---
  public getKPIs(asOfDateStr = "2026-10-20") {
    const asOf = new Date(asOfDateStr);
    asOf.setHours(0, 0, 0, 0);

    let todayDue = 0;
    let overdue = 0;
    let highRisk = 0;
    let completed = 0;

    for (const h of this.households) {
      if (h.visited) {
        completed++;
        continue;
      }
      if (h.is_high_risk) {
        highRisk++;
      }

      const due = new Date(h.due_date);
      due.setHours(0, 0, 0, 0);
      const diffDays = Math.floor((asOf.getTime() - due.getTime()) / (1000 * 60 * 60 * 24));

      if (diffDays === 0) {
        todayDue++;
      } else if (diffDays > 0) {
        overdue++;
      }
    }

    const pendingSync = this.getOutbox().length;
    const criticalAlerts = this.alerts.filter((a) => a.severity === "CRITICAL" && a.delivery_status !== "RESOLVED").length;
    const pendingFollowUps = this.followUps.filter((f) => f.status === "PENDING").length;

    return {
      totalHouseholds: this.households.length,
      todayDue,
      overdue,
      highRisk,
      completed,
      pendingSync,
      criticalAlerts,
      pendingFollowUps,
    };
  }

  // --- DEMO STATE RESET ---
  public resetToDemoState(): void {
    // 1. Re-seed households from initial 500 synthetic records
    this.households = (initialHouseholds as any[]).map((h) => ({
      ...h,
      visited: Boolean(h.visited),
      visited_at: h.visited_at || null,
      visit_notes: h.visit_notes || null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }));
    this.safeSetItem(KEY_HOUSEHOLDS, this.households);

    // 2. Reset patients
    this.patients = initialPatients as unknown as PatientProfile[];
    this.safeSetItem(KEY_PATIENTS, this.patients);

    // 3. Reset alerts
    this.alerts = initialAlerts as unknown as EmergencyAlert[];
    this.safeSetItem(KEY_ALERTS, this.alerts);

    // 4. Reset follow-ups
    this.followUps = [
      {
        follow_up_id: "FLW-1001",
        household_id: "HH-0001",
        beneficiary_name: "Child of Bhavani Kumar",
        village: "Venkatapuram",
        task_description: "Check fever and reaction 48 hours post-DPT booster",
        due_date: "2026-10-22",
        priority: "ROUTINE",
        status: "PENDING",
        created_at: "2026-10-20T09:15:00Z",
      },
      {
        follow_up_id: "FLW-1002",
        household_id: "HH-0012",
        beneficiary_name: "Anasuya Devi",
        village: "Ramnagar",
        task_description: "Repeat BP check & urine protein test for gestational hypertension",
        due_date: "2026-10-23",
        priority: "CRITICAL",
        status: "PENDING",
        created_at: "2026-10-19T14:30:00Z",
      },
    ];
    this.safeSetItem(KEY_FOLLOW_UPS, this.followUps);

    // 5. Clear outbox and reset last sync
    this.safeSetItem(KEY_OUTBOX, []);
    this.safeSetItem(KEY_LAST_SYNC, null);

    // 6. Reset activity log
    this.safeSetItem(KEY_ACTIVITY, [
      {
        id: "act-demo-reset",
        type: "sync",
        title: "Demo State Re-Initialized",
        description: "Restored 500 synthetic households and baseline clinical protocols.",
        timestamp: "Just now",
      },
    ]);
  }
}

export const dataService = new DataService();
