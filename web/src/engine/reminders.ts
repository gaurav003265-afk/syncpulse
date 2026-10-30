/**
 * Monthly Reminders & Follow-Up Gap Detector for TypeScript Engine.
 *
 * Implements Part E and Part F:
 * - Generates reminders strictly from approved MoHFW schedules and actual due dates.
 * - Detects overdue recorded follow-up tasks from real local data.
 * - Month-end boundary safety (handles Feb 28/29, 30-day months).
 * - Deduplication by household + service + due date.
 * - Explicitly denoted as LOCAL_DEVICE_ONLY (no false push delivery claims).
 */

export interface MonthlyReminderTS {
  reminder_id: string;
  household_id: string;
  village: string;
  beneficiary_name: string;
  beneficiary_type: string;
  service_code: string;
  service_name: string;
  protocol_citation: string;
  due_date: string;
  status: "OVERDUE" | "DUE_THIS_MONTH" | "UPCOMING_NEXT_MONTH" | "COMPLETED";
  days_diff: number;
  explanation: string;
  is_high_risk: boolean;
  risk_tag: string | null;
  is_completed: boolean;
  completed_at: string | null;
  notification_channel: "LOCAL_DEVICE_ONLY";
}

export interface FollowUpGapTS {
  follow_up_id: string;
  household_id: string;
  village: string;
  beneficiary_name: string;
  task_description: string;
  due_date: string;
  overdue_days: number;
  priority: string;
  status: "OVERDUE_GAP" | "DUE_TODAY" | "UPCOMING";
  created_at: string;
  explanation: string;
  is_high_risk: boolean;
}

export function generateMonthlyRemindersTS(
  households: any[],
  completedMap: Map<string, { visited_at: string; notes?: string }>,
  asOfDateStr = "2026-10-20"
): MonthlyReminderTS[] {
  const asOf = new Date(asOfDateStr);
  const year = asOf.getFullYear();
  const month = asOf.getMonth(); // 0-indexed

  // Month start and end
  const monthStart = new Date(year, month, 1);
  const monthEnd = new Date(year, month + 1, 0); // Last day of current month

  // Next month end
  const nextMonthEnd = new Date(year, month + 2, 0);

  const reminders: MonthlyReminderTS[] = [];
  const seenKeys = new Set<string>();

  for (const h of households) {
    if (!h.due_date) continue;

    const dedupKey = `${h.household_id}#${h.service_code}#${h.due_date}`;
    if (seenKeys.has(dedupKey)) continue;
    seenKeys.add(dedupKey);

    const dueDate = new Date(h.due_date);
    if (isNaN(dueDate.getTime())) continue;

    const diffTime = asOf.getTime() - dueDate.getTime();
    const diffDays = Math.round(diffTime / (1000 * 3600 * 24));

    const isDone = completedMap.has(h.household_id) || Boolean(h.visited);
    const completedInfo = completedMap.get(h.household_id);
    const completedAt = completedInfo?.visited_at || h.visited_at || null;

    let status: "OVERDUE" | "DUE_THIS_MONTH" | "UPCOMING_NEXT_MONTH" | "COMPLETED";
    let explanation = "";

    if (isDone) {
      status = "COMPLETED";
      explanation = `Completed scheduled service on ${completedAt ? completedAt.substring(0, 10) : "record"}`;
    } else if (diffDays > 0) {
      status = "OVERDUE";
      explanation = `Overdue by ${diffDays} days (Due ${h.due_date}) per ${h.protocol_citation || "MoHFW schedule"}`;
    } else if (dueDate >= monthStart && dueDate <= monthEnd) {
      status = "DUE_THIS_MONTH";
      const daysLeft = -diffDays;
      explanation = `Due this month in ${daysLeft} days (${h.due_date}) per ${h.protocol_citation || "MoHFW schedule"}`;
    } else if (dueDate > monthEnd && dueDate <= nextMonthEnd) {
      status = "UPCOMING_NEXT_MONTH";
      explanation = `Upcoming next month on ${h.due_date} per ${h.protocol_citation || "MoHFW schedule"}`;
    } else {
      continue;
    }

    const remId = `REM-${h.household_id}-${h.service_code}-${h.due_date}`;

    reminders.push({
      reminder_id: remId,
      household_id: h.household_id,
      village: h.village,
      beneficiary_name: h.beneficiary_name,
      beneficiary_type: h.beneficiary_type,
      service_code: h.service_code,
      service_name: h.service_name,
      protocol_citation: h.protocol_citation || "[MoHFW Protocol]",
      due_date: h.due_date,
      status,
      days_diff: diffDays,
      explanation,
      is_high_risk: Boolean(h.is_high_risk),
      risk_tag: h.risk_tag || null,
      is_completed: isDone,
      completed_at: completedAt,
      notification_channel: "LOCAL_DEVICE_ONLY",
    });
  }

  // Sort: High-risk first, then overdue descending, then due date ascending
  reminders.sort((a, b) => {
    if (a.is_high_risk !== b.is_high_risk) return a.is_high_risk ? -1 : 1;
    if (a.status === "OVERDUE" && b.status !== "OVERDUE") return -1;
    if (b.status === "OVERDUE" && a.status !== "OVERDUE") return 1;
    return a.due_date.localeCompare(b.due_date);
  });

  return reminders;
}

export function detectFollowUpGapsTS(
  followUps: any[],
  householdsMap: Map<string, any>,
  asOfDateStr = "2026-10-20"
): FollowUpGapTS[] {
  const asOf = new Date(asOfDateStr);
  const gaps: FollowUpGapTS[] = [];

  for (const f of followUps) {
    if (f.status === "COMPLETED" || f.status === "CANCELLED") continue;

    const dueStr = (f.due_date || "").substring(0, 10);
    const dueDate = new Date(dueStr);
    if (isNaN(dueDate.getTime())) continue;

    const diffTime = asOf.getTime() - dueDate.getTime();
    const diffDays = Math.round(diffTime / (1000 * 3600 * 24));

    const hh = householdsMap.get(f.household_id) || {};

    let status: "OVERDUE_GAP" | "DUE_TODAY" | "UPCOMING";
    let explanation = "";

    if (diffDays > 0) {
      status = "OVERDUE_GAP";
      explanation = `Recorded clinical task overdue by ${diffDays} days (Due ${dueStr}): "${f.task_description}"`;
    } else if (diffDays === 0) {
      status = "DUE_TODAY";
      explanation = `Recorded clinical task due today: "${f.task_description}"`;
    } else {
      status = "UPCOMING";
      explanation = `Upcoming follow-up due in ${-diffDays} days (${dueStr}): "${f.task_description}"`;
    }

    gaps.push({
      follow_up_id: f.follow_up_id,
      household_id: f.household_id,
      village: hh.village || "Village Sub-Center",
      beneficiary_name: hh.beneficiary_name || "Beneficiary",
      task_description: f.task_description,
      due_date: dueStr,
      overdue_days: Math.max(0, diffDays),
      priority: f.priority || "ROUTINE",
      status,
      created_at: f.created_at || asOfDateStr,
      explanation,
      is_high_risk: Boolean(hh.is_high_risk),
    });
  }

  // Sort overdue gaps first, highest priority first
  gaps.sort((a, b) => {
    if (a.status === "OVERDUE_GAP" && b.status !== "OVERDUE_GAP") return -1;
    if (b.status === "OVERDUE_GAP" && a.status !== "OVERDUE_GAP") return 1;
    return b.overdue_days - a.overdue_days;
  });

  return gaps;
}
