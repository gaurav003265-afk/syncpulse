/**
 * Visit management and offline queue persistence in TypeScript.
 */

import householdsData from "../data/households.json" with { type: "json" };

export interface VisitRecord {
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
  overdue_days: number;
  is_high_risk: boolean;
  risk_tag: string | null;
  priority_tier: string;
  priority_rank: number;
  priority_reason: string;
  visited: boolean;
  visited_at: string | null;
}

const STORAGE_KEY_VISITS = "h5_completed_visits";
const STORAGE_KEY_OUTBOX = "h5_sync_outbox";

// Memory storage fallback when running under Node or environments without localStorage
const memoryStorage = new Map<string, string>();

function getStorageItem(key: string): string | null {
  try {
    if (typeof localStorage !== "undefined") {
      return localStorage.getItem(key);
    }
  } catch {}
  return memoryStorage.get(key) || null;
}

function setStorageItem(key: string, value: string): void {
  try {
    if (typeof localStorage !== "undefined") {
      localStorage.setItem(key, value);
      return;
    }
  } catch {}
  memoryStorage.set(key, value);
}

function removeStorageItem(key: string): void {
  try {
    if (typeof localStorage !== "undefined") {
      localStorage.removeItem(key);
      return;
    }
  } catch {}
  memoryStorage.delete(key);
}

export class VisitManagerTS {
  private households: any[];

  constructor() {
    this.households = (householdsData as any[]) || [];
  }

  private getCompletedMap(): Map<string, { visited_at: string; notes: string }> {
    try {
      const raw = getStorageItem(STORAGE_KEY_VISITS);
      if (raw) {
        const arr = JSON.parse(raw);
        const map = new Map();
        for (const item of arr) {
          map.set(item.household_id, item);
        }
        return map;
      }
    } catch (e) {
      // Fall through to empty map
    }
    return new Map();
  }

  public getVisitList(
    asOfDateStr = "2026-10-20",
    village: string | null = null,
    limit = 25,
    includeCompleted = false
  ): VisitRecord[] {
    const asOf = new Date(asOfDateStr);
    const completedMap = this.getCompletedMap();
    const scored: VisitRecord[] = [];

    for (const h of this.households) {
      const isVisited = completedMap.has(h.household_id);
      if (!includeCompleted && isVisited) {
        continue;
      }

      if (village && village !== "All" && h.village.toLowerCase() !== village.toLowerCase()) {
        continue;
      }

      const due = new Date(h.due_date);
      const diffTime = asOf.getTime() - due.getTime();
      const diffDays = Math.round(diffTime / (1000 * 3600 * 24)); // positive = overdue

      const isHr = Boolean(h.is_high_risk);
      let tier = "TIER_4_UPCOMING";
      let rankScore = 100;
      let reason = "";

      if (isHr || diffDays >= 14) {
        tier = "TIER_1_CRITICAL";
        rankScore = 1000 + (isHr ? 100 : 0) + diffDays;
        reason = isHr ? "High-risk alert" : "";
        if (diffDays > 0) {
          reason += reason ? ` (Overdue by ${diffDays} days)` : `Critically overdue by ${diffDays} days`;
        }
        if (h.risk_tag) {
          reason += ` [${h.risk_tag}]`;
        }
      } else if (diffDays > 0) {
        tier = "TIER_2_OVERDUE";
        rankScore = 500 + diffDays;
        reason = `Routine schedule overdue by ${diffDays} days`;
      } else if (diffDays === 0) {
        tier = "TIER_3_DUE_TODAY";
        rankScore = 200;
        reason = "Routine schedule due today";
      } else if (diffDays >= -7) {
        tier = "TIER_4_UPCOMING";
        rankScore = 100 + diffDays;
        reason = `Upcoming routine visit due in ${-diffDays} days`;
      } else {
        continue; // further out
      }

      const compInfo = completedMap.get(h.household_id);

      scored.push({
        household_id: h.household_id,
        village: h.village,
        household_head: h.household_head,
        contact_phone: h.contact_phone,
        beneficiary_name: h.beneficiary_name,
        beneficiary_type: h.beneficiary_type,
        service_code: h.service_code,
        service_name: h.service_name,
        protocol_citation: h.protocol_citation,
        due_date: h.due_date,
        overdue_days: diffDays,
        is_high_risk: isHr,
        risk_tag: h.risk_tag || null,
        priority_tier: tier,
        priority_rank: rankScore,
        priority_reason: reason.trim(),
        visited: isVisited,
        visited_at: compInfo ? compInfo.visited_at : null,
      });
    }

    scored.sort((a, b) => {
      if (b.priority_rank !== a.priority_rank) {
        return b.priority_rank - a.priority_rank;
      }
      if (b.overdue_days !== a.overdue_days) {
        return b.overdue_days - a.overdue_days;
      }
      const numA = parseInt(a.household_id.replace("HH-", ""), 10);
      const numB = parseInt(b.household_id.replace("HH-", ""), 10);
      return numA - numB;
    });

    return scored.slice(0, limit);
  }

  public markVisited(householdId: string, notes = ""): boolean {
    try {
      const raw = getStorageItem(STORAGE_KEY_VISITS);
      const list = raw ? JSON.parse(raw) : [];
      const item = {
        household_id: householdId,
        visited_at: new Date().toISOString(),
        notes,
      };
      list.push(item);
      setStorageItem(STORAGE_KEY_VISITS, JSON.stringify(list));

      // Append to outbox for offline sync
      const outboxRaw = getStorageItem(STORAGE_KEY_OUTBOX);
      const outbox = outboxRaw ? JSON.parse(outboxRaw) : [];
      outbox.push({
        client_uuid: `action-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`,
        action_type: "MARK_VISITED",
        household_id: householdId,
        timestamp: item.visited_at,
        notes,
      });
      setStorageItem(STORAGE_KEY_OUTBOX, JSON.stringify(outbox));
      return true;
    } catch (e) {
      console.error("Mark visited error", e);
      return false;
    }
  }

  public getOutboxCount(): number {
    try {
      const raw = getStorageItem(STORAGE_KEY_OUTBOX);
      return raw ? JSON.parse(raw).length : 0;
    } catch {
      return 0;
    }
  }

  public clearOutbox(): void {
    removeStorageItem(STORAGE_KEY_OUTBOX);
  }

  public resetAll(): void {
    removeStorageItem(STORAGE_KEY_VISITS);
    removeStorageItem(STORAGE_KEY_OUTBOX);
  }
}
