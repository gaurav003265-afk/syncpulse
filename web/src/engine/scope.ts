/**
 * Scope and refusal classification engine in TypeScript for client-side execution.
 * Full parity with core/scope.py.
 */

import { normalizeText, tokenize } from "./normalize.ts";

export interface ScopeResult {
  is_in_scope: boolean;
  scope_category: string;
  refusal_reason: string | null;
  redirect_message: string | null;
}

const PROTOCOL_AUTHORIZED_TERMS = new Set([
  "ors", "oral rehydration", "zinc", "ifa", "iron", "folic acid",
  "calcium", "albendazole", "paracetamol", "crocin", "pcm", "td",
  "tetanus", "bcg", "opv", "polio", "pentavalent", "penta", "rotavirus",
  "rvv", "fipv", "ipv", "pcv", "mr", "measles", "rubella", "vitamin a",
  "dpt", "shakir tape", "muac"
]);

const OUT_OF_SCOPE_PRESCRIPTION_TERMS = [
  "amoxicillin", "ampicillin", "ciprofloxacin", "cipro", "azithromycin",
  "ceftriaxone", "cefixime", "doxycycline", "metronidazole", "flagyl",
  "gentamycin", "gentamicin", "artesunate", "chloroquine", "penicillin",
  "augmentin", "cotrimoxazole", "bactrim", "antibiotic", "antibiotics",
  "sleeping pill", "sleeping pills", "diazepam", "alprazolam", "lorazepam",
  "steroid", "steroids", "prednisolone", "dexamethasone", "hydrocortisone",
  "insulin dose", "titrate insulin", "statin", "atorvastatin", "amlodipine",
  "atenolol", "metoprolol", "losartan", "telmisartan", "chemotherapy",
  "chemo", "dialysis"
];

const OUT_OF_SCOPE_CLINICAL_PROCEDURES = [
  "cpr", "cardiac arrest resuscitation", "surgery", "surgical", "operation",
  "appendicitis surgery", "gallbladder stone", "skin graft", "grafting",
  "intubate", "intubation", "ventilator", "lumbar puncture", "biopsy"
];

const OUT_OF_SCOPE_NON_HEALTH_KEYWORDS = [
  "cricket", "football", "movie", "cinema", "actor", "actress",
  "election", "politics", "mla", "mp", "prime minister", "president",
  "recipe", "cooking", "poem", "poetry", "smartphone", "battery",
  "quadratic equation", "algebra", "bus timing", "train ticket", "aadhaar card",
  "weather forecast", "capital city"
];

export class ScopeClassifierTS {
  private refusalBoilerplate: string;
  private nonHealthBoilerplate: string;

  constructor() {
    this.refusalBoilerplate =
      "This request falls outside frontline health-worker protocol scope. " +
      "Frontline ASHA/ANM workers provide preventive care, screening, and protocol-authorized guidance, " +
      "but are not authorized to prescribe prescription drugs, alter specialized treatment regimens, " +
      "or diagnose conditions outside standing national protocols. " +
      "Please refer the individual to the Primary Health Centre (PHC) Medical Officer or a qualified doctor.";

    this.nonHealthBoilerplate =
      "This question is outside the scope of the Frontline Health-Worker Companion. " +
      "This system assists frontline health workers with maternal health, immunisation, child nutrition, " +
      "hypertension/diabetes monitoring, and fever/dehydration protocols.";
  }

  public classify(query: string): ScopeResult {
    if (!query || !query.trim()) {
      return {
        is_in_scope: false,
        scope_category: "OUT_OF_SCOPE_NON_HEALTH",
        refusal_reason: "Empty query",
        redirect_message: this.nonHealthBoilerplate,
      };
    }

    const normQuery = normalizeText(query);
    const tokens = tokenize(normQuery);

    // 1. Prescription terms
    for (const med of OUT_OF_SCOPE_PRESCRIPTION_TERMS) {
      if (normQuery.includes(med) || tokens.includes(med)) {
        return {
          is_in_scope: false,
          scope_category: "OUT_OF_SCOPE_PRESCRIPTION",
          refusal_reason: `Request to dose or prescribe non-protocol medication: '${med}'`,
          redirect_message: this.refusalBoilerplate,
        };
      }
    }

    // 2. Generic prescription words
    if (tokens.includes("prescribe") || tokens.includes("prescription")) {
      const hasAuth = Array.from(PROTOCOL_AUTHORIZED_TERMS).some(a => normQuery.includes(a));
      if (!hasAuth) {
        return {
          is_in_scope: false,
          scope_category: "OUT_OF_SCOPE_PRESCRIPTION",
          refusal_reason: "Prescription request outside paramedical authority",
          redirect_message: this.refusalBoilerplate,
        };
      }
    }

    // 3. Procedures
    for (const proc of OUT_OF_SCOPE_CLINICAL_PROCEDURES) {
      if (normQuery.includes(proc)) {
        return {
          is_in_scope: false,
          scope_category: "OUT_OF_SCOPE_CLINICAL",
          refusal_reason: `Advanced clinical or surgical procedure: '${proc}'`,
          redirect_message: this.refusalBoilerplate,
        };
      }
    }

    // 4. Non-health
    for (const nh of OUT_OF_SCOPE_NON_HEALTH_KEYWORDS) {
      if (nh.length <= 4) {
        if (tokens.includes(nh)) {
          return {
            is_in_scope: false,
            scope_category: "OUT_OF_SCOPE_NON_HEALTH",
            refusal_reason: `Non-health inquiry: '${nh}'`,
            redirect_message: this.nonHealthBoilerplate,
          };
        }
      } else {
        if (normQuery.includes(nh)) {
          return {
            is_in_scope: false,
            scope_category: "OUT_OF_SCOPE_NON_HEALTH",
            refusal_reason: `Non-health inquiry: '${nh}'`,
            redirect_message: this.nonHealthBoilerplate,
          };
        }
      }
    }

    return {
      is_in_scope: true,
      scope_category: "IN_SCOPE",
      refusal_reason: null,
      redirect_message: null,
    };
  }
}
