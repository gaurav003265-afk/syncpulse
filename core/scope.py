"""
Scope and refusal classification engine for frontline health workers.

NON-NEGOTIABLE PRINCIPLES:
1. Strict paramedical guardrails: Frontline ASHA/ANM workers are paramedical guides,
   not prescribing physicians or surgeons.
2. Refuses requests for:
   - Prescription medications (antibiotics, steroids, sedatives, insulin titration, chemotherapy).
   - Unapproved dosages not in frontline protocol guidelines.
   - Non-protocol clinical procedures or diagnoses (surgeries, invasive treatments).
   - Non-health queries (sports, politics, technology, general knowledge).
3. Preserves access to protocol-authorized interventions:
   - ORS preparation & administration
   - Zinc tablets (10mg/20mg for 14 days)
   - IFA and Calcium supplementation schedules
   - Albendazole deworming in 2nd trimester
   - National Immunisation Schedule doses and routes
   - Paracetamol per protocol guidance
4. ESCALATION PRECEDENCE:
   - If a danger sign is present, the escalation layer handles it first.
   - Scope checking runs only on non-emergency queries.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from core.normalize import normalize_text, tokenize


@dataclass
class ScopeResult:
    is_in_scope: bool
    scope_category: str  # "IN_SCOPE", "OUT_OF_SCOPE_PRESCRIPTION", "OUT_OF_SCOPE_CLINICAL", "OUT_OF_SCOPE_NON_HEALTH"
    refusal_reason: Optional[str]
    redirect_message: Optional[str]


# Protocol-authorized substances/topics that must NOT be falsely refused
PROTOCOL_AUTHORIZED_TERMS = {
    "ors", "oral rehydration", "zinc", "ifa", "iron", "folic acid",
    "calcium", "albendazole", "paracetamol", "crocin", "pcm", "td",
    "tetanus", "bcg", "opv", "polio", "pentavalent", "penta", "rotavirus",
    "rvv", "fipv", "ipv", "pcv", "mr", "measles", "rubella", "vitamin a",
    "dpt", "shakir tape", "muac"
}

# Unapproved drug classes, prescription antibiotics, and invasive procedures
OUT_OF_SCOPE_PRESCRIPTION_TERMS = [
    # Antibiotics & Antivirals
    "amoxicillin", "ampicillin", "ciprofloxacin", "cipro", "azithromycin",
    "ceftriaxone", "cefixime", "doxycycline", "metronidazole", "flagyl",
    "gentamycin", "gentamicin", "artesunate", "chloroquine", "penicillin",
    "augmentin", "cotrimoxazole", "bactrim", "antibiotic", "antibiotics",
    # Sedatives, Psychotropics, Steroids
    "sleeping pill", "sleeping pills", "diazepam", "alprazolam", "lorazepam",
    "steroid", "steroids", "prednisolone", "dexamethasone", "hydrocortisone",
    # Advanced Cardiovascular & Endocrine
    "insulin dose", "titrate insulin", "statin", "atorvastatin", "amlodipine",
    "atenolol", "metoprolol", "losartan", "telmisartan", "chemotherapy",
    "chemo", "dialysis"
]

OUT_OF_SCOPE_CLINICAL_PROCEDURES = [
    "cpr", "cardiac arrest resuscitation", "surgery", "surgical", "operation",
    "appendicitis surgery", "gallbladder stone", "skin graft", "grafting",
    "intubate", "intubation", "ventilator", "lumbar puncture", "biopsy"
]

OUT_OF_SCOPE_NON_HEALTH_KEYWORDS = [
    "cricket", "football", "movie", "cinema", "actor", "actress",
    "election", "politics", "mla", "mp", "prime minister", "president",
    "recipe", "cooking", "poem", "poetry", "smartphone", "battery",
    "quadratic equation", "algebra", "bus timing", "train ticket", "aadhaar card",
    "weather forecast", "capital city"
]


class ScopeClassifier:
    def __init__(self):
        self.refusal_boilerplate = (
            "This request falls outside frontline health-worker protocol scope. "
            "Frontline ASHA/ANM workers provide preventive care, screening, and protocol-authorized guidance, "
            "but are not authorized to prescribe prescription drugs, alter specialized treatment regimens, "
            "or diagnose conditions outside standing national protocols. "
            "Please refer the individual to the Primary Health Centre (PHC) Medical Officer or a qualified doctor."
        )
        self.non_health_boilerplate = (
            "This question is outside the scope of the Frontline Health-Worker Companion. "
            "This system assists frontline health workers with maternal health, immunisation, child nutrition, "
            "hypertension/diabetes monitoring, and fever/dehydration protocols."
        )

    def classify(self, query: str) -> ScopeResult:
        """
        Classifies query into IN_SCOPE or one of the OUT_OF_SCOPE categories.
        """
        if not query or not query.strip():
            return ScopeResult(
                is_in_scope=False,
                scope_category="OUT_OF_SCOPE_NON_HEALTH",
                refusal_reason="Empty query",
                redirect_message=self.non_health_boilerplate,
            )

        norm_query = normalize_text(query)
        tokens = tokenize(norm_query)

        # 1. Check if asking for dose / prescription of an unapproved drug
        # e.g., "what dose of amoxicillin?", "prescribe ciprofloxacin for throat infection"
        for med in OUT_OF_SCOPE_PRESCRIPTION_TERMS:
            if med in norm_query or any(t == med for t in tokens):
                # Verify it's not a protocol authorized drug mentioned in comparison
                is_authorized = any(auth in norm_query for auth in PROTOCOL_AUTHORIZED_TERMS)
                # If they are explicitly asking to prescribe or dose an antibiotic
                if any(w in norm_query for w in ["dose", "dosage", "prescribe", "prescription", "how much", "how many mg", "can i give", "cure"]):
                    return ScopeResult(
                        is_in_scope=False,
                        scope_category="OUT_OF_SCOPE_PRESCRIPTION",
                        refusal_reason=f"Request to dose or prescribe non-protocol medication: '{med}'",
                        redirect_message=self.refusal_boilerplate,
                    )
                # Even if dose is not explicitly in text, asking about an antibiotic prescription
                return ScopeResult(
                    is_in_scope=False,
                    scope_category="OUT_OF_SCOPE_PRESCRIPTION",
                    refusal_reason=f"Query regarding non-protocol prescription medication: '{med}'",
                    redirect_message=self.refusal_boilerplate,
                )

        # 2. Check general prescription terms without approved protocol context
        has_prescribe_term = any(t in ("prescribe", "prescription") for t in tokens)
        if has_prescribe_term:
            # If not mentioning approved vitamins/minerals/ORS
            has_protocol_auth = any(auth in norm_query for auth in PROTOCOL_AUTHORIZED_TERMS)
            if not has_protocol_auth:
                return ScopeResult(
                    is_in_scope=False,
                    scope_category="OUT_OF_SCOPE_PRESCRIPTION",
                    refusal_reason="Prescription request outside paramedical authority",
                    redirect_message=self.refusal_boilerplate,
                )

        # 3. Check advanced clinical / surgical procedures
        for proc in OUT_OF_SCOPE_CLINICAL_PROCEDURES:
            if proc in norm_query:
                return ScopeResult(
                    is_in_scope=False,
                    scope_category="OUT_OF_SCOPE_CLINICAL",
                    refusal_reason=f"Advanced clinical or surgical procedure: '{proc}'",
                    redirect_message=self.refusal_boilerplate,
                )

        # 4. Check non-health questions
        for nh in OUT_OF_SCOPE_NON_HEALTH_KEYWORDS:
            if len(nh) <= 4:
                # Require whole word token match for short words (e.g. 'mp', 'mla')
                if any(t == nh for t in tokens):
                    return ScopeResult(
                        is_in_scope=False,
                        scope_category="OUT_OF_SCOPE_NON_HEALTH",
                        refusal_reason=f"Non-health inquiry: '{nh}'",
                        redirect_message=self.non_health_boilerplate,
                    )
            else:
                if nh in norm_query:
                    return ScopeResult(
                        is_in_scope=False,
                        scope_category="OUT_OF_SCOPE_NON_HEALTH",
                        refusal_reason=f"Non-health inquiry: '{nh}'",
                        redirect_message=self.non_health_boilerplate,
                    )

        # 5. Query passed all refusal checks -> IN_SCOPE
        return ScopeResult(
            is_in_scope=True,
            scope_category="IN_SCOPE",
            refusal_reason=None,
            redirect_message=None,
        )
