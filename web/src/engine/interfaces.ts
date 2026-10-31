/**
 * SyncPulse SOLID Interface Definitions
 * Implements Dependency Inversion Principle (DIP), Interface Segregation (ISP),
 * and Liskov Substitution Principle (LSP) for the frontend engine and storage layer.
 */

import type { HouseholdRecord, PatientProfile, FollowUpTask, EmergencyAlert } from "./dataService";

// ─────────────────────────────────────────────────────────────────────────────
// Storage Engine Interfaces (LSP — Liskov Substitution Principle)
// ─────────────────────────────────────────────────────────────────────────────

export interface IAsyncStorageEngine {
  init(): Promise<void>;
  query<T>(sql: string, params?: unknown[]): Promise<T[]>;
  execute(sql: string, params?: unknown[]): Promise<{ rowsAffected: number }>;
  transaction<T>(action: (tx: IAsyncStorageEngine) => Promise<T>): Promise<T>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Repository Interfaces (ISP — Interface Segregation Principle)
// ─────────────────────────────────────────────────────────────────────────────

export interface IReadableRepository<T, ID = string> {
  findById(id: ID): Promise<T | null>;
  findAll(filter?: Partial<T>): Promise<T[]>;
}

export interface IWritableRepository<T, ID = string> {
  save(entity: T): Promise<T>;
  update(id: ID, patch: Partial<T>): Promise<boolean>;
  delete(id: ID): Promise<boolean>;
}

export interface ISyncEvent {
  event_id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  payload: Record<string, unknown>;
  created_at: string;
  status: "PENDING" | "SYNCED" | "FAILED";
}

export interface ISyncableRepository {
  getPendingSyncItems(): Promise<ISyncEvent[]>;
  markSynced(eventIds: string[]): Promise<void>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Clinical Pipeline & Rule Strategy Interfaces (DIP & OCP)
// ─────────────────────────────────────────────────────────────────────────────

export interface VitalSigns {
  systolicBp?: number;
  diastolicBp?: number;
  pulseBpm?: number;
  temperatureF?: number;
  weightKg?: number;
  muacMm?: number;
}

export interface RuleEvaluationResult {
  triggered: boolean;
  ruleId: string;
  actionText: string;
  citation?: string;
  category?: string;
}

export interface IClinicalRuleStrategy {
  readonly ruleId: string;
  readonly category: "OBSTETRIC" | "PEDIATRIC" | "NCD" | "INFECTIOUS";
  evaluate(query: string, vitals?: VitalSigns): RuleEvaluationResult;
}

// ─────────────────────────────────────────────────────────────────────────────
// Domain Repository Contracts
// ─────────────────────────────────────────────────────────────────────────────

export interface IHouseholdRepository
  extends IReadableRepository<HouseholdRecord>,
    IWritableRepository<HouseholdRecord> {}

export interface IPatientRepository
  extends IReadableRepository<PatientProfile>,
    IWritableRepository<PatientProfile> {}

export interface IEmergencyAlertRepository
  extends IReadableRepository<EmergencyAlert>,
    IWritableRepository<EmergencyAlert>,
    ISyncableRepository {}

export interface IFollowUpRepository
  extends IReadableRepository<FollowUpTask>,
    IWritableRepository<FollowUpTask> {}

