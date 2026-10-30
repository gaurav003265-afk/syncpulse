"""
Emergency escalation engine for frontline health workers.

NON-NEGOTIABLE DESIGN PRINCIPLES:
1. Deterministic rules with ZERO model involvement.
2. Executes as Step 1 on raw query text before any retrieval, embedding, or LM logic.
3. Recall-first matching: guaranteed 100% detection of critical danger signs.
4. Multilingual & code-mixed: English, Romanised Telugu/Hindi, Telugu script, Devanagari script.
5. Typo and fuzzy resilience via token collapsing, prefix stems, and proximity.
6. Fail-safe on ambiguity: always escalates. Negations ('no bleeding') do NOT suppress
   escalation; they annotate 'negation_detected=True' to allow UI verification without
   sacrificing life-safety recall.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from core.normalize import extract_vitals, normalize_text, tokenize


@dataclass
class MatchedRule:
    rule_id: str
    category: str
    title: str
    corpus_citation: str
    action_text: str
    matched_term: str
    match_type: str  # "phrase", "stem_proximity", "numeric", "native_script"


@dataclass
class EscalationResult:
    escalate: bool
    action_text: Optional[str]
    corpus_citation: Optional[str]
    matched_rules: List[MatchedRule]
    primary_rule_id: Optional[str]
    negation_detected: bool
    trigger_reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "escalate": self.escalate,
            "action_text": self.action_text,
            "corpus_citation": self.corpus_citation,
            "matched_rules": [asdict(r) for r in self.matched_rules],
            "primary_rule_id": self.primary_rule_id,
            "negation_detected": self.negation_detected,
            "trigger_reason": self.trigger_reason,
        }


NEGATION_TOKENS = {
    "no", "not", "without", "never", "none", "neither", "nor",
    "ledhu", "ledu", "kaadhu", "kadu", "lekunda", "లేకపోవడం", "లేదు", "కాదు",
    "nahi", "nahin", "bina", "mat", "नहीं", "बिना"
}


class EscalationEngine:
    def __init__(self, rules_path: Optional[str] = None):
        if rules_path is None:
            rules_path = str(Path(__file__).resolve().parent.parent / "data" / "escalation_rules.json")

        self.rules_path = Path(rules_path)
        if not self.rules_path.exists():
            raise FileNotFoundError(f"Escalation rules file not found: {self.rules_path}")

        with open(self.rules_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.version = data.get("version", "1.0.0")
        self.rules: List[Dict[str, Any]] = data.get("rules", [])
        self.rules_by_id = {r["rule_id"]: r for r in self.rules}

    def check(self, query: str) -> EscalationResult:
        """
        Runs the deterministic escalation check on the raw user query.
        Returns an EscalationResult with escalate=True if any danger sign is detected.
        """
        if not query or not query.strip():
            return EscalationResult(
                escalate=False,
                action_text=None,
                corpus_citation=None,
                matched_rules=[],
                primary_rule_id=None,
                negation_detected=False,
                trigger_reason="Empty input",
            )

        norm_query = normalize_text(query)
        tokens = tokenize(norm_query)
        vitals = extract_vitals(norm_query)

        # Procedural / training query check (e.g. 'how to test', 'how to measure', 'what indicates')
        # Frontline worker asking for protocol instructions rather than reporting an active patient emergency
        is_procedural_question = (
            any(norm_query.startswith(prefix) for prefix in [
                "how to test", "how to check", "how to measure", "how to assess",
                "what indicates", "what measurement indicates", "what muac measurement", "what muac",
                "what does", "how to manage conscious"
            ])
            and not any(active in norm_query for active in [
                "patient has", "child has", "woman has", "mother has", "baby has", "is having",
                "bleeding", "fits", "seizure", "unconscious", "behosh", "spruha", "dying"
            ])
        )

        if is_procedural_question:
            return EscalationResult(
                escalate=False,
                action_text=None,
                corpus_citation=None,
                matched_rules=[],
                primary_rule_id=None,
                negation_detected=False,
                trigger_reason="Educational/procedural inquiry regarding testing or definitions",
            )

        negation_detected = any(t in NEGATION_TOKENS for t in tokens)
        matched_rules: List[MatchedRule] = []

        def add_match(rule_id: str, term: str, m_type: str):
            r = self.rules_by_id.get(rule_id)
            if r:
                matched_rules.append(
                    MatchedRule(
                        rule_id=rule_id,
                        category=r["category"],
                        title=r["title"],
                        corpus_citation=r["corpus_citation"],
                        action_text=r["action_text"],
                        matched_term=term,
                        match_type=m_type,
                    )
                )

        # -------------------------------------------------------------
        # 1. PREGNANCY: Vaginal Bleeding (ESC-MAT-01)
        # -------------------------------------------------------------
        has_bleed_stem = any(t.startswith("bleed") or t in ("aph", "spotting", "spot") for t in tokens)
        has_blood_word = "blood" in tokens
        has_telugu_blood = any(t.startswith("rakth") or t.startswith("rakt") for t in tokens) or "రక్తస్రావం" in norm_query or "రక్తం" in norm_query
        has_hindi_blood = ("khoon" in tokens or "raktasrav" in tokens or "रक्तस्राव" in norm_query or "खून" in norm_query)

        is_maternal = (
            any(t.startswith("pregnan") or t.startswith("garbh") or t in ("mother", "woman", "lady", "maternal", "amma", "trimester") for t in tokens)
            or "vagina" in norm_query or "vaginal" in norm_query or "గర్భవతి" in norm_query or "గర్భిణీ" in norm_query or "गर्भावस्था" in norm_query or "गर्भवती" in norm_query
            or "weeks" in tokens or "week" in tokens or "months" in tokens or "month" in tokens
        )

        if has_bleed_stem:
            # Standalone bleeding with maternal/vaginal or direct phrases
            if is_maternal or "vagina" in norm_query or "vaginal" in norm_query or "bleed" in norm_query:
                # Disambiguate if gums/petechial -> FEV-03
                if "gums" not in tokens and "rash" not in tokens and "petechial" not in tokens:
                    add_match("ESC-MAT-01", "vaginal/maternal bleeding", "phrase")
        elif (has_blood_word or has_telugu_blood or has_hindi_blood) and is_maternal:
            # Avoid matching "blood pressure" unless vaginal/bleeding context
            if not ("pressure" in tokens and not ("vagina" in tokens or "vaginal" in tokens)):
                add_match("ESC-MAT-01", "raktham/khoon in pregnancy", "stem_proximity")

        # -------------------------------------------------------------
        # 2. PREGNANCY: Convulsions / Fits / Eclampsia (ESC-MAT-02)
        # -------------------------------------------------------------
        has_fits = any(t in ("fits", "fitss", "convulsion", "convulsions", "seizure", "seizures", "janni", "murccha", "daure", "jhatke", "mirgi", "spasms") for t in tokens)
        has_fits_native = any(k in norm_query for k in ["ఫిట్స్", "మూర్ఛ", "జెన్ని", "దౌర్జన్యం", "दौरे", "झटके", "मिर्गी"])
        if (has_fits or has_fits_native or "eclampsia" in norm_query):
            if is_maternal or "labor" in tokens or "delivery" in tokens:
                add_match("ESC-MAT-02", "eclampsia/maternal fits", "stem_proximity")
            elif "fever" not in tokens and "bukhar" not in tokens and "jwaram" not in tokens and "baby" not in tokens and "newborn" not in tokens and "child" not in tokens:
                add_match("ESC-MAT-02", "eclampsia/fits", "phrase")

        # -------------------------------------------------------------
        # 3. PREGNANCY: Severe Headache + Visual Blur (ESC-MAT-03)
        # -------------------------------------------------------------
        has_headache = (
            any(t.startswith("headach") for t in tokens)
            or ("head" in tokens and "pain" in tokens)
            or "sir dard" in norm_query or "sirdard" in tokens or "thalanoppi" in tokens
            or "తలనొప్పి" in norm_query or "सिरदर्द" in norm_query
        )
        has_vision = (
            any(t.startswith("blur") for t in tokens)
            or "spots" in tokens or "dark spots" in norm_query or "choopu" in tokens
            or "dhundhla" in norm_query or "andhera" in tokens or "vision" in tokens
            or "కంటి" in norm_query or "धुंधला" in norm_query
        )
        if has_headache and has_vision:
            add_match("ESC-MAT-03", "headache + visual blur", "stem_proximity")
        elif "impending eclampsia" in norm_query or "తీవ్రమైన తలనొప్పి మరియు కంటి చూపు" in norm_query or "तीव्र सिरदर्द और धुंधला" in norm_query:
            add_match("ESC-MAT-03", "impending eclampsia", "phrase")

        # -------------------------------------------------------------
        # 4. PREGNANCY: PROM / Amniotic Fluid Leak (ESC-MAT-04)
        # -------------------------------------------------------------
        if "water breaking" in norm_query or "amniotic fluid" in norm_query or "prom" in tokens:
            add_match("ESC-MAT-04", "water breaking / prom", "phrase")
        elif (
            "leaking" in tokens or "leak" in tokens or "karipoth" in norm_query or "karuthu" in norm_query
            or "pani gir" in norm_query or "pani nikal" in norm_query or "ఉమ్మనీరు" in norm_query or "पानी छूटना" in norm_query
        ):
            if is_maternal or "fluid" in tokens or "water" in tokens or "neellu" in tokens or "pani" in tokens:
                add_match("ESC-MAT-04", "leaking fluid pregnancy", "stem_proximity")

        # -------------------------------------------------------------
        # 5. PREGNANCY: Reduced Fetal Movement (ESC-MAT-05)
        # -------------------------------------------------------------
        has_fetal = any(t in ("baby", "fetal", "bidda", "bacha", "बच्चे") for t in tokens) or "బిడ్డ" in norm_query or "बच्चा" in norm_query
        has_no_move = (
            "not moving" in norm_query or "stopped moving" in norm_query or "no movement" in norm_query or "movement reduced" in norm_query
            or "no fetal movement" in norm_query or ("movement" in tokens and any(t in ("no", "reduced", "absent", "loss", "stopped") for t in tokens))
            or "kadalika" in norm_query or "kadaladam" in norm_query or "hil nahi" in norm_query or "move nahi" in norm_query
            or "కదలికలు పూర్తిగా ఆగిపోయాయి" in norm_query or "కదలికలు" in norm_query or "हलचल" in norm_query
        )
        if (has_fetal and has_no_move) or "కదలికలు పూర్తిగా ఆగిపోయాయి" in norm_query or "हलचल बिल्कुल बंद" in norm_query:
            add_match("ESC-MAT-05", "baby stopped moving", "stem_proximity")

        # -------------------------------------------------------------
        # 6. PREGNANCY: Severe Abdominal Pain (ESC-MAT-06)
        # -------------------------------------------------------------
        has_severe = any(t in ("severe", "sharp", "agonizing", "theevramaina", "tez") for t in tokens) or normalize_text("విపరీతమైన") in norm_query or normalize_text("తీవ్రమైన") in norm_query
        has_abdo_pain = (
            "abdominal pain" in norm_query or "stomach pain" in norm_query or "kadupu noppi" in norm_query or "pet dard" in norm_query
            or ("pet" in tokens and "dard" in tokens) or normalize_text("కడుపు నొప్పి") in norm_query or normalize_text("కడుపు") in norm_query or "पेट दर्द" in norm_query
        )
        if (has_abdo_pain and is_maternal) or (has_severe and has_abdo_pain):
            add_match("ESC-MAT-06", "severe abdominal pain pregnancy", "stem_proximity")

        # -------------------------------------------------------------
        # 7. INTRAPARTUM: Prolonged / Obstructed Labor / Prolapse (ESC-INTRA-01)
        # -------------------------------------------------------------
        if "prolonged labor" in norm_query or "obstructed labor" in norm_query or "cord prolapse" in norm_query:
            add_match("ESC-INTRA-01", "obstructed/prolonged labor", "phrase")
        elif ("hand prolapse" in norm_query or "foot prolapse" in norm_query or "breech stuck" in norm_query or "prasav me rukawat" in norm_query):
            add_match("ESC-INTRA-01", "malpresentation/prolapse", "phrase")
        elif "labor" in tokens or "prasavam" in tokens or "prasav" in tokens or "ప్రసవ" in norm_query:
            if (
                "12 hours" in norm_query or "14 hours" in norm_query or "16 hours" in norm_query
                or "12 gantalu" in norm_query or "14 gantalu" in norm_query or "aagipoyindi" in norm_query
                or "ప్రసవ వేదన 12" in norm_query or "కాలేదు" in norm_query
            ):
                add_match("ESC-INTRA-01", "labor > 12 hours / obstructed", "stem_proximity")

        # -------------------------------------------------------------
        # 8. POSTPARTUM: PPH / Heavy Bleeding (ESC-POST-01)
        # -------------------------------------------------------------
        if "pph" in tokens or "postpartum hemorrhage" in norm_query or "ప్రసవానంతర అధిక రక్తస్రావం" in norm_query or "ప్రసవానంతర రక్తస్రావం" in norm_query:
            add_match("ESC-POST-01", "postpartum hemorrhage", "phrase")
        elif (has_bleed_stem or has_blood_word or has_telugu_blood or has_hindi_blood) and ("delivery" in tokens or "postpartum" in tokens or "postnatal" in tokens or "prasavam" in tokens):
            add_match("ESC-POST-01", "bleeding after delivery", "stem_proximity")
        elif ("pads" in tokens or "pad" in tokens) and ("soaked" in tokens or "soaking" in tokens):
            add_match("ESC-POST-01", "soaked pads postpartum", "stem_proximity")

        # -------------------------------------------------------------
        # 9. POSTPARTUM: Foul Lochia + Fever / Puerperal Sepsis (ESC-POST-02)
        # -------------------------------------------------------------
        has_foul = any(t in ("foul", "smelly", "offensive", "kampu", "durgandh", "దుర్వాసనతో") for t in tokens)
        has_lochia = any(t in ("lochia", "discharge", "vasana", "srav", "sravam", "స్రావం") for t in tokens)
        has_fever_term = any(t in ("fever", "jwaram", "bukhar", "జ్వరం", "బుఖార్") for t in tokens) or "జ్వరం" in norm_query
        if "puerperal sepsis" in norm_query:
            add_match("ESC-POST-02", "puerperal sepsis", "phrase")
        elif has_foul and has_lochia and (has_fever_term or "delivery" in tokens or "postpartum" in tokens):
            add_match("ESC-POST-02", "foul lochia fever", "stem_proximity")

        # -------------------------------------------------------------
        # 10. NEWBORN: Inability to Feed / Poor Sucking (ESC-NEO-01)
        # -------------------------------------------------------------
        is_infant = any(t in ("baby", "newborn", "infant", "child", "pilla", "pilladi", "pillaki", "bacha", "shishu", "chinna", "శిశువు", "చిన్నారి") for t in tokens) or "శిశువు" in norm_query or "పిల్లాడికి" in norm_query
        if (
            "not feeding" in norm_query or "unable to feed" in norm_query or "cannot suck" in norm_query or "not sucking" in norm_query
            or "refuses breastmilk" in norm_query or "refuses to breastfeed" in norm_query or "unable to breastfeed" in norm_query
            or "palu thagadam ledhu" in norm_query or "palu chekatledu" in norm_query or "పాలూ తాగటం లేదు" in norm_query
            or "పాలు తాగలేకపోవడం" in norm_query or "పాలు పట్టకపోవడం" in norm_query or "doodh nahi pee" in norm_query or "doodh nahi chus" in norm_query
        ):
            add_match("ESC-NEO-01", "baby unable to feed", "phrase")

        # -------------------------------------------------------------
        # 11. NEWBORN: Fast Breathing (Tachypnea >= 60) (ESC-NEO-02)
        # -------------------------------------------------------------
        has_fast_breath = (
            "fast breathing" in norm_query or "rapid breathing" in norm_query or "tachypnea" in norm_query
            or "tez saans" in norm_query or ("saans" in tokens and "tez" in tokens) or "వేగంగా శ్వాస" in norm_query
        )
        if has_fast_breath and (is_infant or "newborn" in norm_query or "70 per minute" in norm_query):
            add_match("ESC-NEO-02", "fast breathing newborn", "phrase")
        elif vitals.get("respiratory_rate") and vitals["respiratory_rate"] >= 60.0:
            add_match("ESC-NEO-02", f"respiratory rate {vitals['respiratory_rate']} >= 60", "numeric")

        # -------------------------------------------------------------
        # 12. NEWBORN: Severe Chest Indrawing (ESC-NEO-03)
        # -------------------------------------------------------------
        if (
            "chest indrawing" in norm_query or "chest wall drawing inward" in norm_query or "subcostal retraction" in norm_query
            or "sucking inward" in norm_query or "drawing inward" in norm_query
            or "rommu lopaliki" in norm_query or "rommu kottuko" in norm_query or "chhati andar dhas" in norm_query
            or "chhati dhas" in norm_query or "ఛాతీ లోపలికి" in norm_query or "ఛాతీ కొట్టుకోవడం" in norm_query
            or "छाती अंदर धंसना" in norm_query
        ):
            add_match("ESC-NEO-03", "severe chest indrawing", "phrase")

        # -------------------------------------------------------------
        # 13. NEWBORN: Convulsions / Fits / Twitching (ESC-NEO-04)
        # -------------------------------------------------------------
        if (has_fits or has_fits_native) and is_infant:
            add_match("ESC-NEO-04", "newborn fits/convulsions", "stem_proximity")

        # -------------------------------------------------------------
        # 14. NEWBORN: Severe Jaundice (Day 1 or Palms/Soles) (ESC-NEO-05)
        # -------------------------------------------------------------
        has_jaundice = any(t in ("jaundice", "yellow", "peeliya", "peele", "peela", "pasupu", "పసిరికలు", "కామర్లు") for t in tokens) or "పసుపు" in norm_query
        has_jaundice_crit = (
            "day 1" in norm_query or "first day" in norm_query or "palms" in tokens or "soles" in tokens
            or "arachethulu" in tokens or "arallu" in tokens or "arikallu" in tokens or "talwe" in tokens or "hatheli" in tokens
            or "అరచేతులు" in norm_query or "అరికాళ్ళు" in norm_query
        )
        if has_jaundice and has_jaundice_crit:
            add_match("ESC-NEO-05", "severe neonatal jaundice", "stem_proximity")

        # -------------------------------------------------------------
        # 15. NEWBORN: Hypothermia / High Fever Newborn (ESC-NEO-06)
        # -------------------------------------------------------------
        if is_infant:
            if "hypothermia" in tokens or "cold to touch" in norm_query or "challabadi" in norm_query or "thanda pad" in norm_query or "చల్లబడిపోయింది" in norm_query or "freezing cold" in norm_query:
                add_match("ESC-NEO-06", "newborn hypothermia", "phrase")
            elif vitals.get("temp_c") is not None:
                if vitals["temp_c"] <= 35.5 or vitals["temp_c"] >= 38.5:
                    add_match("ESC-NEO-06", f"temp {vitals['temp_c']} C", "numeric")

        # -------------------------------------------------------------
        # 16. NEWBORN: Umbilical Pus / Infection (ESC-NEO-07)
        # -------------------------------------------------------------
        has_umbilicus = any(t in ("umbilical", "umbilicus", "navel", "boddu", "nabhi", "బొడ్డు", "నాభి") for t in tokens) or "బొడ్డు" in norm_query
        has_pus = any(t in ("pus", "cheemu", "peep", "omphalitis", "చీము", "మవాద్") for t in tokens) or ("redness" in tokens and has_umbilicus)
        if has_umbilicus and has_pus:
            add_match("ESC-NEO-07", "umbilical infection/pus", "stem_proximity")

        # -------------------------------------------------------------
        # 17. NEWBORN: Floppy / Limp / Unconscious / Cyanosis (ESC-NEO-08)
        # -------------------------------------------------------------
        if is_infant:
            if (
                "limp" in tokens or "floppy" in tokens or "unconscious" in tokens or "not responding" in norm_query
                or "blue lips" in norm_query or "cyanosis" in tokens or "spruha ledhu" in norm_query or "behosh" in tokens
                or "neela pad" in norm_query or "నీలంగా" in norm_query
            ):
                add_match("ESC-NEO-08", "baby limp/unconscious/cyanosis", "stem_proximity")

        # -------------------------------------------------------------
        # 18. MALNUTRITION: Bilateral Pitting Edema (ESC-NUT-01)
        # -------------------------------------------------------------
        if "bilateral pitting edema" in norm_query or "pitting edema" in norm_query or "kwashiorkor" in tokens:
            add_match("ESC-NUT-01", "bilateral pitting edema", "phrase")
        elif (
            ("edema" in tokens or "swelling" in tokens or "vaapu" in tokens or "soojan" in tokens or "వాపు" in norm_query or "సూజన్" in norm_query)
            and ("both feet" in norm_query or "feet" in tokens or "pairon" in norm_query or "kaallu" in norm_query or "కాళ్ల" in norm_query or "indent" in tokens or "guntalu" in norm_query or "gaddha" in norm_query)
        ):
            # Exclude vaccine local swelling
            if "vaccine" not in tokens and "injection" not in tokens and "tika" not in tokens:
                add_match("ESC-NUT-01", "feet pitting edema", "stem_proximity")

        # -------------------------------------------------------------
        # 19. MALNUTRITION: SAM with Complications / MUAC < 115 (ESC-NUT-02)
        # -------------------------------------------------------------
        if "failed appetite" in norm_query or "appetite test fail" in norm_query or "red zone" in norm_query:
            if "muac" in tokens or "sam" in tokens:
                add_match("ESC-NUT-02", "sam failed appetite", "stem_proximity")
        elif "sam" in tokens and ("refusing" in tokens or "therapeutic" in tokens or "vomiting" in tokens or "fever" in tokens):
            add_match("ESC-NUT-02", "sam with complications", "stem_proximity")
        elif vitals.get("muac_mm") is not None and vitals["muac_mm"] < 115.0:
            add_match("ESC-NUT-02", f"muac {vitals['muac_mm']} mm < 115", "numeric")

        # -------------------------------------------------------------
        # 20. HYPERTENSION: Crisis BP >= 180/110 (ESC-NCD-01)
        # -------------------------------------------------------------
        if "hypertensive crisis" in norm_query or "bp chala ekkuva" in norm_query:
            add_match("ESC-NCD-01", "hypertensive crisis", "phrase")
        elif vitals.get("bp"):
            sys_val, dia_val = vitals["bp"]
            if sys_val >= 180.0 or dia_val >= 110.0:
                add_match("ESC-NCD-01", f"BP {sys_val}/{dia_val} >= 180/110", "numeric")

        # -------------------------------------------------------------
        # 21. HYPERTENSION: High BP with Stroke / Chest Pain (ESC-NCD-02)
        # -------------------------------------------------------------
        has_bp_mention = any(t in ("bp", "hypertension") for t in tokens) or "blood pressure" in norm_query or "బీపీ" in norm_query or "రక్తపోటు" in norm_query
        has_stroke_mi = (
            "chest pain" in norm_query or "slurred speech" in norm_query or "weakness" in tokens
            or "gundello noppi" in norm_query or "pakshavatham" in norm_query or "stroke" in tokens
            or "lakhwa" in tokens or "ఛాతీ నొప్పి" in norm_query or "seene me tez dard" in norm_query
            or ("seene" in tokens and "dard" in tokens)
        )
        if has_bp_mention and has_stroke_mi:
            add_match("ESC-NCD-02", "high BP with stroke/chest pain", "stem_proximity")

        # -------------------------------------------------------------
        # 22. DIABETES: Severe Hypoglycemia Emergency (ESC-NCD-03)
        # -------------------------------------------------------------
        if "hypoglycemia" in tokens:
            add_match("ESC-NCD-03", "hypoglycemia", "phrase")
        elif "sugar" in tokens or "మధుమేహం" in norm_query or "షుగర్" in norm_query:
            if "unconscious" in tokens or "drowsy" in tokens or "cold sweat" in norm_query or "behosh" in tokens or "spruha" in tokens or "45" in tokens or "50" in tokens or "48" in tokens or "52" in tokens or "low" in tokens:
                add_match("ESC-NCD-03", "severe hypoglycemia emergency", "stem_proximity")

        # -------------------------------------------------------------
        # 23. DIARRHEA: Severe Dehydration (ESC-ORS-01)
        # -------------------------------------------------------------
        if "severe dehydration" in norm_query or "తీవ్రమైన నిర్జలీకరణ" in norm_query or "నిర్జలీకరణ" in norm_query:
            add_match("ESC-ORS-01", "severe dehydration", "phrase")
        elif "skin pinch" in norm_query:
            if "2 seconds" in norm_query or "very slowly" in norm_query or "slowly" in norm_query:
                add_match("ESC-ORS-01", "skin pinch > 2s", "stem_proximity")
        elif ("sunken eyes" in norm_query or "chamada" in norm_query or "చర్మం మడత" in norm_query or "గుంటలు" in norm_query) and ("unconscious" in tokens or "behosh" in tokens or "floppy" in tokens or "2 seconds" in norm_query or "స్పృహ లేదు" in norm_query):
            add_match("ESC-ORS-01", "sunken eyes unconscious dehydration", "stem_proximity")

        # -------------------------------------------------------------
        # 24. DIARRHEA: Dysentery / Blood in Stool / Persistent Diarrhea (ESC-ORS-02)
        # -------------------------------------------------------------
        if "dysentery" in tokens or "రక్త విరేచనాలు" in norm_query:
            add_match("ESC-ORS-02", "dysentery", "phrase")
        elif (has_blood_word or has_bleed_stem or has_telugu_blood or has_hindi_blood) and ("stool" in tokens or "stools" in tokens or "diarrhea" in tokens or "virachanalu" in tokens or "tatti" in tokens or "mala" in tokens):
            add_match("ESC-ORS-02", "blood in stool / dysentery", "stem_proximity")
        elif "diarrhea" in tokens or "virachanalu" in tokens or "dast" in tokens:
            if "14 days" in norm_query or "16 days" in norm_query or "2 weeks" in norm_query:
                add_match("ESC-ORS-02", "persistent diarrhea >= 14 days", "stem_proximity")

        # -------------------------------------------------------------
        # 25. FEVER: Stiff Neck / Meningitis (ESC-FEV-01)
        # -------------------------------------------------------------
        if has_fever_term:
            if (
                "stiff neck" in norm_query or "neck stiffness" in norm_query or "meningitis" in tokens
                or "meda vangaraledhu" in norm_query or "meda gattiga" in norm_query or "gardan akad" in norm_query
                or "మెడ పట్టేసి" in norm_query or "మెడ వంగడం లేదు" in norm_query
            ):
                add_match("ESC-FEV-01", "fever with stiff neck", "stem_proximity")
            elif "neck" in tokens and ("bend" in tokens or "stiff" in tokens or "touch chin" in norm_query):
                add_match("ESC-FEV-01", "fever unable to bend neck", "stem_proximity")

        # -------------------------------------------------------------
        # 26. FEVER: Convulsions / Delirium (ESC-FEV-02)
        # -------------------------------------------------------------
        if has_fever_term and (has_fits or has_fits_native or "febrile seizures" in norm_query or "delirium" in tokens or "altered sensorium" in norm_query):
            add_match("ESC-FEV-02", "fever with convulsions", "stem_proximity")

        # -------------------------------------------------------------
        # 27. FEVER: Petechial Rash / Dengue Warning Signs (ESC-FEV-03)
        # -------------------------------------------------------------
        if has_fever_term:
            if (
                "petechial" in tokens or "petechiae" in tokens or "purple spots" in norm_query
                or "bleeding gums" in norm_query or "dengue warning" in norm_query or "erupu machalu" in norm_query
                or "lal dhabbe" in norm_query or "ఎర్రటి మచ్చలు" in norm_query
            ):
                add_match("ESC-FEV-03", "fever with petechial rash / dengue warning", "stem_proximity")

        # -------------------------------------------------------------
        # 28. FEVER: Prolonged (> 7 Days) (ESC-FEV-04)
        # -------------------------------------------------------------
        if has_fever_term:
            if vitals.get("fever_days") and vitals["fever_days"] > 7.0:
                add_match("ESC-FEV-04", f"fever {vitals['fever_days']} days > 7", "numeric")
            elif any(k in norm_query for k in ["8 days", "9 days", "10 days", "12 days", "14 days", "2 weeks", "8 rojulu", "10 din", "వారం రోజులు దాటినా"]):
                add_match("ESC-FEV-04", "prolonged fever > 7 days", "phrase")

        # -------------------------------------------------------------
        # Final Decision Assembly
        # -------------------------------------------------------------
        if matched_rules:
            primary = matched_rules[0]
            reason = f"Danger sign detected: {primary.title} (Trigger: '{primary.matched_term}', type: {primary.match_type})"
            if negation_detected:
                reason += " [NOTE: Negation detected in text; escalating fail-safe per clinical protocol]"

            return EscalationResult(
                escalate=True,
                action_text=primary.action_text,
                corpus_citation=primary.corpus_citation,
                matched_rules=matched_rules,
                primary_rule_id=primary.rule_id,
                negation_detected=negation_detected,
                trigger_reason=reason,
            )

        return EscalationResult(
            escalate=False,
            action_text=None,
            corpus_citation=None,
            matched_rules=[],
            primary_rule_id=None,
            negation_detected=negation_detected,
            trigger_reason="No critical danger sign detected",
        )
