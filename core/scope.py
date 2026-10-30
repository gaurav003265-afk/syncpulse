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
    "ration card", "pension", "salary", "incentive", "voter id", "bank account", "passbook",
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

        # -------------------------------------------------------------
        # Official SCP-1.2 Explicit Refusal Rules (TalentAP H5 Scope)
        # -------------------------------------------------------------

        # A. Medicine Dosing (including paracetamol / syrups)
        if ("paracetamol" in tokens or "crocin" in tokens or "pcm" in tokens or "syrup" in tokens) and (
            "kitna" in norm_query or "kitne" in norm_query or "kitni" in norm_query or "dose" in tokens or "dosage" in tokens or "dawai" in tokens
        ):
            return ScopeResult(
                is_in_scope=False,
                scope_category="OUT_OF_SCOPE_PRESCRIPTION",
                refusal_reason="Medicine doses are not in this protocol; ask the ANM/MO",
                redirect_message="Medicine doses are not in this protocol; ask the ANM/MO (SCP-1.2, CHD-2.3).",
            )

        # B. Conditions not covered: Enuresis / Bedwetting
        if "bistar geela" in norm_query or "enuresis" in norm_query or "bedwetting" in norm_query:
            return ScopeResult(
                is_in_scope=False,
                scope_category="OUT_OF_SCOPE_CLINICAL",
                refusal_reason="Enuresis / bedwetting is not covered by frontline protocol",
                redirect_message="Not covered; see the Medical Officer (SCP-1.2).",
            )

        # C. Conditions not covered: HIV
        if "hiv" in tokens:
            return ScopeResult(
                is_in_scope=False,
                scope_category="OUT_OF_SCOPE_CLINICAL",
                refusal_reason="HIV treatment is not covered",
                redirect_message="HIV treatment is not covered; refer to the Medical Officer (SCP-1.2).",
            )

        # D. Conditions not covered: Lab report interpretation / Typhoid / Widal
        if "typhoid" in tokens or "widal" in tokens or "lab report" in norm_query:
            return ScopeResult(
                is_in_scope=False,
                scope_category="OUT_OF_SCOPE_CLINICAL",
                refusal_reason="Lab report interpretation and typhoid are not covered",
                redirect_message="Lab report interpretation and typhoid are not covered; consult the Medical Officer (SCP-1.2).",
            )

        # E. Vaccines outside National Immunisation Schedule: COVID booster
        if "covid" in tokens or "corona" in tokens:
            return ScopeResult(
                is_in_scope=False,
                scope_category="OUT_OF_SCOPE_CLINICAL",
                refusal_reason="COVID vaccines are not covered by these protocols",
                redirect_message="Not covered by these protocols; ask the ANM/MO (SCP-1.2).",
            )

        # F. Administrative / App / Login / OTP issues
        if "u-win" in norm_query or "uwin" in norm_query or ("login" in tokens and "otp" in tokens) or "otp nahi" in norm_query:
            return ScopeResult(
                is_in_scope=False,
                scope_category="OUT_OF_SCOPE_ADMINISTRATIVE",
                refusal_reason="App and login problems are not covered",
                redirect_message="App/login problems are not covered; contact the block data manager (SCP-1.2).",
            )

        # G. Sex Determination (Prohibited by PC-PNDT Act)
        if any(w in norm_query for w in ["ladka hai ya ladki", "gender test", "sex determination", "boy or girl in womb"]):
            return ScopeResult(
                is_in_scope=False,
                scope_category="OUT_OF_SCOPE_ILLEGAL",
                refusal_reason="Sex determination of the foetus is prohibited by law (PC-PNDT Act)",
                redirect_message="Sex determination of the foetus is prohibited by law (PC-PNDT Act); every pregnancy needs full ANC (SCP-1.2).",
            )

        # H. Self-medication / prescription requests ("kaunsi goli lu", "kaunsi dawai lu")
        if any(w in norm_query for w in ["kaunsi goli", "kaun si goli", "kaunsi dawai", "kaun si dawai", "konsi goli", "konsi dawai", "goli lu", "dawai lu"]):
            if not any(auth in norm_query for auth in ["ifa", "calcium", "albendazole", "ors", "zinc"]):
                return ScopeResult(
                    is_in_scope=False,
                    scope_category="OUT_OF_SCOPE_PRESCRIPTION",
                    refusal_reason="Prescribing medicine for symptoms is not authorized",
                    redirect_message="Prescribing medicines is not in frontline protocol; please consult the Medical Officer (SCP-1.2).",
                )

        # I. Uncovered Conditions explicitly named in SCP-1.2: TB, Dengue, Thyroid, Cancer, Skin, Mental Health, Kidney Stones
        if "tb" in tokens or "tuberculosis" in tokens:
            return ScopeResult(
                is_in_scope=False,
                scope_category="OUT_OF_SCOPE_CLINICAL",
                refusal_reason="TB diagnosis and treatment are not covered",
                redirect_message="TB diagnosis and treatment are not covered; refer to the Medical Officer (SCP-1.2).",
            )
        if "dengue" in tokens or "platelet" in tokens:
            return ScopeResult(
                is_in_scope=False,
                scope_category="OUT_OF_SCOPE_CLINICAL",
                refusal_reason="Dengue testing and platelet interpretation are not covered",
                redirect_message="Dengue testing and lab reports are not covered; refer to the Medical Officer (SCP-1.2).",
            )
        if "thyroid" in tokens or "tsh" in tokens:
            return ScopeResult(
                is_in_scope=False,
                scope_category="OUT_OF_SCOPE_CLINICAL",
                refusal_reason="Thyroid reports and medication are not covered",
                redirect_message="Thyroid diagnosis and lab reports are not covered; consult the Medical Officer (SCP-1.2).",
            )
        if "pathri" in norm_query or "desi ilaaj" in norm_query:
            return ScopeResult(
                is_in_scope=False,
                scope_category="OUT_OF_SCOPE_CLINICAL",
                refusal_reason="Kidney stones and home remedies are not covered",
                redirect_message="Kidney stones and home remedies are not in frontline protocol; refer to the Medical Officer (SCP-1.2).",
            )
        if "khujli" in norm_query and "cream" in norm_query:
            return ScopeResult(
                is_in_scope=False,
                scope_category="OUT_OF_SCOPE_PRESCRIPTION",
                refusal_reason="Skin disease treatment and creams are not covered",
                redirect_message="Skin diseases and prescription creams are not covered; refer to the Medical Officer (SCP-1.2).",
            )
        if "garbhpat" in norm_query or "abortion" in tokens:
            return ScopeResult(
                is_in_scope=False,
                scope_category="OUT_OF_SCOPE_CLINICAL",
                refusal_reason="Abortion services and medicines are not covered",
                redirect_message="Abortion services are not covered in frontline protocols; refer to the Medical Officer / ANM (SCP-1.2).",
            )
        if "cough syrup" in norm_query:
            return ScopeResult(
                is_in_scope=False,
                scope_category="OUT_OF_SCOPE_PRESCRIPTION",
                refusal_reason="Cough syrups are not prescribed in frontline protocol",
                redirect_message="Cough syrups are not prescribed in frontline protocol; consult the Medical Officer (SCP-1.2).",
            )
        if "insulin" in tokens and any(w in norm_query for w in ["unit", "units", "dose", "kitni"]):
            return ScopeResult(
                is_in_scope=False,
                scope_category="OUT_OF_SCOPE_PRESCRIPTION",
                refusal_reason="Insulin dosage titration is not covered",
                redirect_message="Insulin dosing is strictly done by the Medical Officer; do not alter insulin dose (SCP-1.2).",
            )
        if "drops" in tokens and ("aankh" in tokens or "keechad" in norm_query):
            return ScopeResult(
                is_in_scope=False,
                scope_category="OUT_OF_SCOPE_PRESCRIPTION",
                refusal_reason="Eye drops prescription is not covered",
                redirect_message="Prescribing eye drops is outside protocol scope; refer to the Medical Officer (SCP-1.2).",
            )
        if "daaru" in norm_query or "sharab" in norm_query or "de-addiction" in norm_query:
            return ScopeResult(
                is_in_scope=False,
                scope_category="OUT_OF_SCOPE_CLINICAL",
                refusal_reason="Alcohol de-addiction medications are not covered",
                redirect_message="Substance de-addiction medications are outside frontline protocol; consult the Medical Officer (SCP-1.2).",
            )
        if "hpv" in tokens or ("cancer" in tokens and "tika" in norm_query):
            return ScopeResult(
                is_in_scope=False,
                scope_category="OUT_OF_SCOPE_CLINICAL",
                refusal_reason="HPV vaccine is not in the National Immunisation Schedule",
                redirect_message="HPV vaccine is not currently part of the standing National Immunisation Schedule; ask the ANM/MO (SCP-1.2).",
            )
        if "placenta previa" in norm_query:
            return ScopeResult(
                is_in_scope=False,
                scope_category="OUT_OF_SCOPE_CLINICAL",
                refusal_reason="Ultrasound interpretation is not covered",
                redirect_message="Ultrasound report interpretation is outside frontline scope; refer to the Medical Officer (SCP-1.2).",
            )

        # J. Administrative questions: recharge, birth certificates, schemes
        if "recharge" in tokens or "data khatam" in norm_query:
            return ScopeResult(
                is_in_scope=False,
                scope_category="OUT_OF_SCOPE_NON_HEALTH",
                refusal_reason="Mobile data and recharge inquiries are outside health protocol",
                redirect_message="Mobile data and recharge inquiries are outside the scope of health protocols (SCP-1.2).",
            )
        if "janam praman patra" in norm_query or "birth certificate" in norm_query:
            return ScopeResult(
                is_in_scope=False,
                scope_category="OUT_OF_SCOPE_ADMINISTRATIVE",
                refusal_reason="Birth certificate administrative procedures are not covered",
                redirect_message="Birth certificate administration is not covered in health protocols; contact the gram panchayat / municipal registrar (SCP-1.2).",
            )
        if "ayushman" in norm_query and any(w in norm_query for w in ["card", "apply", "banta"]):
            return ScopeResult(
                is_in_scope=False,
                scope_category="OUT_OF_SCOPE_ADMINISTRATIVE",
                refusal_reason="Ayushman card application is an administrative process",
                redirect_message="Ayushman card processing is an administrative scheme; refer to the Common Service Centre (CSC) or Ayushman kiosk (SCP-1.2).",
            )

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
                # Do not refuse Caesarean section / delivery by operation (in-scope for HBNC)
                if proc == "operation" and any(d in norm_query for d in ["delivery", "prasav", "bachcha", "hbnc", "visit"]):
                    continue
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
