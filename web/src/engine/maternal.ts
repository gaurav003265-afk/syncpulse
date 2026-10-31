/**
 * SyncPulse MoHFW Obstetric Decision & Gestational Age Engine
 * Computes Expected Date of Delivery (Naegele's Rule), Gestational Age,
 * ANC Visit Milestones, and High-Risk Pregnancy (HRP) Stratification.
 * 100% Offline, Deterministic, and Zero External Dependencies.
 */

export interface ObstetricProfile {
  lmpDate: string;
  eddDate: string;
  gestationalDays: number;
  gestationalWeeks: number;
  gestationalRemainingDays: number;
  gestationalAgeFormatted: string;
  trimester: 1 | 2 | 3;
  trimesterLabel: string;
  currentAncMilestone: {
    milestone: "ANC-1" | "ANC-2" | "ANC-3" | "ANC-4" | "POST-TERM";
    title: string;
    targetWindowWeeks: string;
    clinicalChecklist: string[];
    isOverdue: boolean;
  };
  highRiskFactors: string[];
  isHighRisk: boolean;
  recommendedAction: string;
}

export interface MaternalClinicalInputs {
  lmpDate: string;
  asOfDate?: string;
  ageYears?: number;
  systolicBp?: number;
  diastolicBp?: number;
  hemoglobinGdl?: number;
  previousCSection?: boolean;
  hasDangerSigns?: boolean;
  dangerSignDetails?: string;
}

/**
 * Calculates Naegele's Rule: EDD = LMP + 280 days (40 weeks)
 */
export function calculateEdd(lmpDateStr: string): string {
  const lmp = new Date(lmpDateStr);
  if (isNaN(lmp.getTime())) return "";
  const edd = new Date(lmp.getTime() + 280 * 24 * 60 * 60 * 1000);
  return edd.toISOString().split("T")[0];
}

/**
 * Calculates complete obstetric profile grounded in MoHFW Maternal Care Protocols.
 */
export function calculateObstetricProfile(inputs: MaternalClinicalInputs): ObstetricProfile | null {
  if (!inputs.lmpDate) return null;
  const lmp = new Date(inputs.lmpDate);
  if (isNaN(lmp.getTime())) return null;

  const ref = inputs.asOfDate ? new Date(inputs.asOfDate) : new Date();
  const diffMs = ref.getTime() - lmp.getTime();
  const gestationalDays = Math.max(0, Math.floor(diffMs / (1000 * 60 * 60 * 24)));

  const gestationalWeeks = Math.floor(gestationalDays / 7);
  const gestationalRemainingDays = gestationalDays % 7;
  const gestationalAgeFormatted = `${gestationalWeeks} Weeks ${gestationalRemainingDays} Days`;

  const eddDate = calculateEdd(inputs.lmpDate);

  // Trimester classification
  let trimester: 1 | 2 | 3 = 1;
  let trimesterLabel = "1st Trimester (1–12 Weeks)";
  if (gestationalWeeks >= 28) {
    trimester = 3;
    trimesterLabel = "3rd Trimester (28–40 Weeks)";
  } else if (gestationalWeeks >= 13) {
    trimester = 2;
    trimesterLabel = "2nd Trimester (13–27 Weeks)";
  }

  // ANC Milestone according to MoHFW protocol (01_ANC_antenatal_care.md)
  let milestone: "ANC-1" | "ANC-2" | "ANC-3" | "ANC-4" | "POST-TERM" = "ANC-1";
  let title = "ANC-1: First Check-up & Early Registration";
  let targetWindowWeeks = "Within first 12 weeks";
  let checklist = [
    "Confirm pregnancy & issue MCP card",
    "Record baseline weight & Blood Pressure",
    "Screen for anemia (Hemoglobin) & syphilis/HIV",
    "Distribute Folic Acid (400 mcg daily)",
    "Counsel on nutrition and danger signs"
  ];
  let isOverdue = false;

  if (gestationalWeeks > 40) {
    milestone = "POST-TERM";
    title = "Post-Term Pregnancy Alert (> 40 Weeks)";
    targetWindowWeeks = "Immediate Referral";
    checklist = [
      "Immediate institutional referral to FRU / District Hospital",
      "Do not delay for home labor onset",
      "Monitor fetal movements (DFMC)"
    ];
    isOverdue = true;
  } else if (gestationalWeeks >= 36) {
    milestone = "ANC-4";
    title = "ANC-4: Pre-Delivery & Birth Preparedness Check-up";
    targetWindowWeeks = "36 weeks to expected delivery";
    checklist = [
      "Assess fetal presentation and lie",
      "Check BP for late pre-eclampsia",
      "Finalize designated institutional delivery facility",
      "Verify 108 emergency transport contact and accompany plan",
      "Confirm Janani Suraksha Yojana (JSY) entitlements"
    ];
  } else if (gestationalWeeks >= 28) {
    milestone = "ANC-3";
    title = "ANC-3: Third Trimester Growth & Pressure Check";
    targetWindowWeeks = "28 to 34 weeks";
    checklist = [
      "Check BP and test urine albumin for preeclampsia",
      "Administer Td-2 or Td-Booster injection",
      "Measure symphysis-fundal height (SFH)",
      "Screen for severe anemia (Repeat Hb test)",
      "Dispense 180 IFA tablets (1 daily) + 360 Calcium tablets"
    ];
  } else if (gestationalWeeks >= 14) {
    milestone = "ANC-2";
    title = "ANC-2: Mid-Trimester Anomaly & Vitals Screening";
    targetWindowWeeks = "14 to 26 weeks";
    checklist = [
      "Administer Td-1 injection (or Td-Booster if vaccinated <3 yrs)",
      "Screen blood pressure & check pedal edema",
      "Refer for Ultrasound (Anomaly scan at 18–20 weeks)",
      "Start IFA tablets (after 1st trimester)",
      "Monitor gestational weight gain"
    ];
  }

  // High-Risk Pregnancy (HRP) Stratification
  const highRiskFactors: string[] = [];

  if (inputs.ageYears !== undefined) {
    if (inputs.ageYears < 18) {
      highRiskFactors.push(`Adolescent Pregnancy (Age ${inputs.ageYears} < 18)`);
    } else if (inputs.ageYears >= 35) {
      highRiskFactors.push(`Advanced Maternal Age (Age ${inputs.ageYears} ≥ 35)`);
    }
  }

  if (inputs.systolicBp !== undefined && inputs.diastolicBp !== undefined) {
    if (inputs.systolicBp >= 160 || inputs.diastolicBp >= 110) {
      highRiskFactors.push(`Severe Hypertensive Crisis (BP ${inputs.systolicBp}/${inputs.diastolicBp} mmHg)`);
    } else if (inputs.systolicBp >= 140 || inputs.diastolicBp >= 90) {
      highRiskFactors.push(`Gestational Hypertension / Preeclampsia (BP ${inputs.systolicBp}/${inputs.diastolicBp} mmHg)`);
    }
  }

  if (inputs.hemoglobinGdl !== undefined) {
    if (inputs.hemoglobinGdl < 7.0) {
      highRiskFactors.push(`Critical Severe Anemia (Hb ${inputs.hemoglobinGdl} g/dL < 7.0)`);
    } else if (inputs.hemoglobinGdl < 11.0) {
      highRiskFactors.push(`Moderate Anemia (Hb ${inputs.hemoglobinGdl} g/dL)`);
    }
  }

  if (inputs.previousCSection) {
    highRiskFactors.push("Previous Cesarean Section (High uterine rupture risk)");
  }

  if (inputs.hasDangerSigns) {
    highRiskFactors.push(inputs.dangerSignDetails || "Acute Obstetric Danger Sign Detected");
  }

  const isHighRisk = highRiskFactors.length > 0;
  let recommendedAction = "Proceed with routine ANC schedule and counseling.";
  if (isHighRisk) {
    if (highRiskFactors.some((f) => f.includes("Severe") || f.includes("Crisis") || f.includes("Danger"))) {
      recommendedAction = "🚨 EMERGENCY: Immediate 108 transfer to First Referral Unit (FRU) / District Hospital.";
    } else {
      recommendedAction = "⚠️ High-Risk: Flag on MCP card and arrange Medical Officer (PHC) clinical review.";
    }
  }

  return {
    lmpDate: inputs.lmpDate,
    eddDate,
    gestationalDays,
    gestationalWeeks,
    gestationalRemainingDays,
    gestationalAgeFormatted,
    trimester,
    trimesterLabel,
    currentAncMilestone: {
      milestone,
      title,
      targetWindowWeeks,
      clinicalChecklist: checklist,
      isOverdue,
    },
    highRiskFactors,
    isHighRisk,
    recommendedAction,
  };
}

