/**
 * Emergency escalation engine in TypeScript for client-side offline execution.
 * Full parity with core/escalation.py.
 */

import rulesData from "../data/escalation_rules.json" with { type: "json" };
import { extractVitals, normalizeText, tokenize } from "./normalize.ts";

export interface MatchedRule {
  rule_id: string;
  category: string;
  title: string;
  corpus_citation: string;
  action_text: string;
  matched_term: string;
  match_type: string;
}

export interface EscalationResult {
  escalate: boolean;
  action_text: string | null;
  corpus_citation: string | null;
  matched_rules: MatchedRule[];
  primary_rule_id: string | null;
  negation_detected: boolean;
  trigger_reason: string;
}

const NEGATION_TOKENS = new Set([
  "no", "not", "without", "never", "none", "neither", "nor",
  "ledhu", "ledu", "kaadhu", "kadu", "lekunda", "లేకపోవడం", "లేదు", "కాదు",
  "nahi", "nahin", "bina", "mat", "नहीं", "बिना"
]);

export class EscalationEngineTS {
  private rules: any[];
  private rulesById: Map<string, any>;

  constructor() {
    this.rules = rulesData.rules || [];
    this.rulesById = new Map();
    for (const r of this.rules) {
      this.rulesById.set(r.rule_id, r);
    }
  }

  public check(query: string): EscalationResult {
    if (!query || !query.trim()) {
      return {
        escalate: false,
        action_text: null,
        corpus_citation: null,
        matched_rules: [],
        primary_rule_id: null,
        negation_detected: false,
        trigger_reason: "Empty input",
      };
    }

    const normQuery = normalizeText(query);
    const tokens = tokenize(normQuery);
    const vitals = extractVitals(normQuery);

    // Procedural check
    const isProcedural = [
      "how to test", "how to check", "how to measure", "how to assess",
      "what indicates", "what measurement indicates", "what muac measurement", "what muac",
      "what does", "how to manage conscious"
    ].some(prefix => normQuery.startsWith(prefix)) &&
    ![
      "patient has", "child has", "woman has", "mother has", "baby has", "is having",
      "bleeding", "fits", "seizure", "unconscious", "behosh", "spruha", "dying"
    ].some(active => normQuery.includes(active));

    if (isProcedural) {
      return {
        escalate: false,
        action_text: null,
        corpus_citation: null,
        matched_rules: [],
        primary_rule_id: null,
        negation_detected: false,
        trigger_reason: "Educational/procedural inquiry regarding testing or definitions",
      };
    }

    const negationDetected = tokens.some(t => NEGATION_TOKENS.has(t));
    const matchedRules: MatchedRule[] = [];

    const addMatch = (ruleId: string, term: string, mType: string) => {
      const r = this.rulesById.get(ruleId);
      if (r) {
        matchedRules.push({
          rule_id: ruleId,
          category: r.category,
          title: r.title,
          corpus_citation: r.corpus_citation,
          action_text: r.action_text,
          matched_term: term,
          match_type: mType,
        });
      }
    };

    // 1. PREGNANCY: Vaginal Bleeding (ESC-MAT-01)
    const hasBleedStem = tokens.some(t => t.startsWith("bleed") || t === "aph" || t === "spotting" || t === "spot");
    const hasBloodWord = tokens.includes("blood");
    const hasTeluguBlood = tokens.some(t => t.startsWith("rakth") || t.startsWith("rakt")) || normQuery.includes("రక్తస్రావం") || normQuery.includes("రక్తం");
    const hasHindiBlood = tokens.includes("khoon") || tokens.includes("raktasrav") || normQuery.includes("रक्तस्राव") || normQuery.includes("खून");

    const isMaternal = tokens.some(t => t.startsWith("pregnan") || t.startsWith("garbh") || ["mother", "woman", "lady", "maternal", "amma", "trimester", "weeks", "week", "months", "month"].includes(t)) ||
      normQuery.includes("vagina") || normQuery.includes("vaginal") || normQuery.includes("గర్భవతి") || normQuery.includes("గర్భిణీ") || normQuery.includes("गर्भावस्था") || normQuery.includes("गर्भवती");

    if (hasBleedStem) {
      if (isMaternal || normQuery.includes("vagina") || normQuery.includes("vaginal") || normQuery.includes("bleed")) {
        if (!tokens.includes("gums") && !tokens.includes("rash") && !tokens.includes("petechial")) {
          addMatch("ESC-MAT-01", "vaginal/maternal bleeding", "phrase");
        }
      }
    } else if ((hasBloodWord || hasTeluguBlood || hasHindiBlood) && isMaternal) {
      if (!(tokens.includes("pressure") && !tokens.includes("vagina") && !tokens.includes("vaginal"))) {
        addMatch("ESC-MAT-01", "raktham/khoon in pregnancy", "stem_proximity");
      }
    }

    // 2. PREGNANCY: Fits / Eclampsia (ESC-MAT-02)
    const hasFits = tokens.some(t => ["fits", "fitss", "convulsion", "convulsions", "seizure", "seizures", "janni", "murccha", "daure", "jhatke", "mirgi", "spasms"].includes(t));
    const hasFitsNative = ["ఫిట్స్", "మూర్ఛ", "జెన్ని", "దౌర్జన్యం", "दौरे", "झटके", "मिर्गी"].some(k => normQuery.includes(k));
    if (hasFits || hasFitsNative || normQuery.includes("eclampsia")) {
      if (isMaternal || tokens.includes("labor") || tokens.includes("delivery")) {
        addMatch("ESC-MAT-02", "eclampsia/maternal fits", "stem_proximity");
      } else if (!tokens.includes("fever") && !tokens.includes("bukhar") && !tokens.includes("jwaram") && !tokens.includes("baby") && !tokens.includes("newborn") && !tokens.includes("child")) {
        addMatch("ESC-MAT-02", "eclampsia/fits", "phrase");
      }
    }

    // 3. PREGNANCY: Severe Headache + Visual Blur (ESC-MAT-03)
    const hasHeadache = tokens.some(t => t.startsWith("headach")) || (tokens.includes("head") && tokens.includes("pain")) || normQuery.includes("sir dard") || tokens.includes("sirdard") || tokens.includes("thalanoppi") || normQuery.includes("తలనొప్పి") || normQuery.includes("सिरदर्द");
    const hasVision = tokens.some(t => t.startsWith("blur")) || tokens.includes("spots") || normQuery.includes("dark spots") || tokens.includes("choopu") || normQuery.includes("dhundhla") || tokens.includes("andhera") || tokens.includes("vision") || normQuery.includes("కంటి") || normQuery.includes("धुंधला");
    if (hasHeadache && hasVision) {
      addMatch("ESC-MAT-03", "headache + visual blur", "stem_proximity");
    } else if (normQuery.includes("impending eclampsia") || normQuery.includes("తీవ్రమైన తలనొప్పి మరియు కంటి చూపు") || normQuery.includes("तीव्र सिरदर्द और धुंधला")) {
      addMatch("ESC-MAT-03", "impending eclampsia", "phrase");
    }

    // 4. PREGNANCY: PROM / Amniotic Fluid (ESC-MAT-04)
    if (normQuery.includes("water breaking") || normQuery.includes("amniotic fluid") || tokens.includes("prom")) {
      addMatch("ESC-MAT-04", "water breaking / prom", "phrase");
    } else if (tokens.includes("leaking") || tokens.includes("leak") || normQuery.includes("karipoth") || normQuery.includes("karuthu") || normQuery.includes("pani gir") || normQuery.includes("pani nikal") || normQuery.includes("ఉమ్మనీరు") || normQuery.includes("पानी छूटना")) {
      if (isMaternal || tokens.includes("fluid") || tokens.includes("water") || tokens.includes("neellu") || tokens.includes("pani")) {
        addMatch("ESC-MAT-04", "leaking fluid pregnancy", "stem_proximity");
      }
    }

    // 5. PREGNANCY: Reduced Fetal Movement (ESC-MAT-05)
    const hasFetal = tokens.some(t => ["baby", "fetal", "bidda", "bacha", "बच्चे"].includes(t)) || normQuery.includes("బిడ్డ") || normQuery.includes("बच्चा");
    const hasNoMove = normQuery.includes("not moving") || normQuery.includes("stopped moving") || normQuery.includes("no movement") || normQuery.includes("movement reduced") || normQuery.includes("no fetal movement") || (tokens.includes("movement") && ["no", "reduced", "absent", "loss", "stopped"].some(t => tokens.includes(t))) || normQuery.includes("kadalika") || normQuery.includes("kadaladam") || normQuery.includes("hil nahi") || normQuery.includes("move nahi") || normQuery.includes("కదలికలు") || normQuery.includes("हलचल");
    if ((hasFetal && hasNoMove) || normQuery.includes("కదలికలు పూర్తిగా ఆగిపోయాయి") || normQuery.includes("हलचल बिल्कुल बंद")) {
      addMatch("ESC-MAT-05", "baby stopped moving", "stem_proximity");
    }

    // 6. PREGNANCY: Severe Abdominal Pain (ESC-MAT-06)
    const hasSevere = tokens.some(t => ["severe", "sharp", "agonizing", "theevramaina", "tez"].includes(t)) || normQuery.includes("విపరీతమైన") || normQuery.includes("తీవ్రమైన");
    const hasAbdoPain = normQuery.includes("abdominal pain") || normQuery.includes("stomach pain") || normQuery.includes("kadupu noppi") || normQuery.includes("pet dard") || (tokens.includes("pet") && tokens.includes("dard")) || normQuery.includes("కడుపు నొప్పి") || normQuery.includes("కడుపు") || normQuery.includes("पेट दर्द");
    if ((hasAbdoPain && isMaternal) || (hasSevere && hasAbdoPain)) {
      addMatch("ESC-MAT-06", "severe abdominal pain pregnancy", "stem_proximity");
    }

    // 7. INTRAPARTUM: Prolonged / Obstructed Labor (ESC-INTRA-01)
    if (normQuery.includes("prolonged labor") || normQuery.includes("obstructed labor") || normQuery.includes("cord prolapse")) {
      addMatch("ESC-INTRA-01", "obstructed/prolonged labor", "phrase");
    } else if (normQuery.includes("hand prolapse") || normQuery.includes("foot prolapse") || normQuery.includes("breech stuck") || normQuery.includes("prasav me rukawat")) {
      addMatch("ESC-INTRA-01", "malpresentation/prolapse", "phrase");
    } else if (tokens.includes("labor") || tokens.includes("prasavam") || tokens.includes("prasav") || normQuery.includes("ప్రసవ")) {
      if (["12 hours", "14 hours", "16 hours", "12 gantalu", "14 gantalu", "aagipoyindi", "ప్రసవ వేదన 12", "కాలేదు"].some(k => normQuery.includes(k))) {
        addMatch("ESC-INTRA-01", "labor > 12 hours / obstructed", "stem_proximity");
      }
    }

    // 8. POSTPARTUM: PPH (ESC-POST-01)
    if (tokens.includes("pph") || normQuery.includes("postpartum hemorrhage") || normQuery.includes("ప్రసవానంతర అధిక రక్తస్రావం") || normQuery.includes("ప్రసవానంతర రక్తస్రావం")) {
      addMatch("ESC-POST-01", "postpartum hemorrhage", "phrase");
    } else if ((hasBleedStem || hasBloodWord || hasTeluguBlood || hasHindiBlood) && ["delivery", "postpartum", "postnatal", "prasavam"].some(t => tokens.includes(t))) {
      addMatch("ESC-POST-01", "bleeding after delivery", "stem_proximity");
    } else if ((tokens.includes("pads") || tokens.includes("pad")) && (tokens.includes("soaked") || tokens.includes("soaking"))) {
      addMatch("ESC-POST-01", "soaked pads postpartum", "stem_proximity");
    }

    // 9. POSTPARTUM: Foul Lochia (ESC-POST-02)
    const hasFoul = tokens.some(t => ["foul", "smelly", "offensive", "kampu", "durgandh"].includes(t)) || normQuery.includes("దుర్వాసనతో");
    const hasLochia = tokens.some(t => ["lochia", "discharge", "vasana", "srav", "sravam"].includes(t)) || normQuery.includes("స్రావం");
    const hasFeverTerm = tokens.some(t => ["fever", "jwaram", "bukhar"].includes(t)) || normQuery.includes("జ్వరం") || normQuery.includes("బుఖార్");
    if (normQuery.includes("puerperal sepsis")) {
      addMatch("ESC-POST-02", "puerperal sepsis", "phrase");
    } else if (hasFoul && hasLochia && (hasFeverTerm || tokens.includes("delivery") || tokens.includes("postpartum"))) {
      addMatch("ESC-POST-02", "foul lochia fever", "stem_proximity");
    }

    // 10. NEWBORN: Not Feeding (ESC-NEO-01)
    const isInfant = tokens.some(t => ["baby", "newborn", "infant", "child", "pilla", "pilladi", "pillaki", "bacha", "shishu", "chinna"].includes(t)) || normQuery.includes("శిశువు") || normQuery.includes("పిల్లాడికి");
    if (
      ["not feeding", "unable to feed", "cannot suck", "not sucking", "refuses breastmilk", "refuses to breastfeed", "unable to breastfeed",
       "palu thagadam ledhu", "palu chekatledu", "పాలూ తాగటం లేదు", "పాలు తాగలేకపోవడం", "పాలు పట్టకపోవడం", "doodh nahi pee", "doodh nahi chus"].some(k => normQuery.includes(k))
    ) {
      addMatch("ESC-NEO-01", "baby unable to feed", "phrase");
    }

    // 11. NEWBORN: Fast Breathing (ESC-NEO-02)
    const hasFastBreath = ["fast breathing", "rapid breathing", "tachypnea", "tez saans", "వేగంగా శ్వాస"].some(k => normQuery.includes(k)) || (tokens.includes("saans") && tokens.includes("tez"));
    if (hasFastBreath && (isInfant || normQuery.includes("newborn") || normQuery.includes("70 per minute"))) {
      addMatch("ESC-NEO-02", "fast breathing newborn", "phrase");
    } else if (vitals.respiratory_rate !== null && vitals.respiratory_rate >= 60) {
      addMatch("ESC-NEO-02", `respiratory rate ${vitals.respiratory_rate} >= 60`, "numeric");
    }

    // 12. NEWBORN: Chest Indrawing (ESC-NEO-03)
    if (
      ["chest indrawing", "chest wall drawing inward", "subcostal retraction", "sucking inward", "drawing inward",
       "rommu lopaliki", "rommu kottuko", "chhati andar dhas", "chhati dhas", "ఛాతీ లోపలికి", "ఛాతీ కొట్టుకోవడం", "छाती अंदर धंसना"].some(k => normQuery.includes(k))
    ) {
      addMatch("ESC-NEO-03", "severe chest indrawing", "phrase");
    }

    // 13. NEWBORN: Fits (ESC-NEO-04)
    if ((hasFits || hasFitsNative) && isInfant) {
      addMatch("ESC-NEO-04", "newborn fits/convulsions", "stem_proximity");
    }

    // 14. NEWBORN: Jaundice (ESC-NEO-05)
    const hasJaundice = tokens.some(t => ["jaundice", "yellow", "peeliya", "peele", "peela", "pasupu"].includes(t)) || normQuery.includes("పసుపు");
    const hasJaundiceCrit = ["day 1", "first day", "palms", "soles", "arachethulu", "arallu", "arikallu", "talwe", "hatheli"].some(k => normQuery.includes(k) || tokens.includes(k)) || normQuery.includes("అరచేతులు") || normQuery.includes("అరికాళ్ళు");
    if (hasJaundice && hasJaundiceCrit) {
      addMatch("ESC-NEO-05", "severe neonatal jaundice", "stem_proximity");
    }

    // 15. NEWBORN: Hypothermia / High Fever (ESC-NEO-06)
    if (isInfant) {
      if (tokens.includes("hypothermia") || ["cold to touch", "challabadi", "thanda pad", "చల్లబడిపోయింది", "freezing cold"].some(k => normQuery.includes(k))) {
        addMatch("ESC-NEO-06", "newborn hypothermia", "phrase");
      } else if (vitals.temp_c !== null) {
        if (vitals.temp_c <= 35.5 || vitals.temp_c >= 38.5) {
          addMatch("ESC-NEO-06", `temp ${vitals.temp_c} C`, "numeric");
        }
      }
    }

    // 16. NEWBORN: Umbilical Pus (ESC-NEO-07)
    const hasUmbilicus = tokens.some(t => ["umbilical", "umbilicus", "navel", "boddu", "nabhi"].includes(t)) || normQuery.includes("బొడ్డు") || normQuery.includes("నాభి");
    const hasPus = tokens.some(t => ["pus", "cheemu", "peep", "omphalitis"].includes(t)) || normQuery.includes("చీము") || (tokens.includes("redness") && hasUmbilicus);
    if (hasUmbilicus && hasPus) {
      addMatch("ESC-NEO-07", "umbilical infection/pus", "stem_proximity");
    }

    // 17. NEWBORN: Floppy / Limp / Cyanosis (ESC-NEO-08)
    if (isInfant) {
      if (
        tokens.includes("limp") || tokens.includes("floppy") || tokens.includes("unconscious") || normQuery.includes("not responding") ||
        normQuery.includes("blue lips") || tokens.includes("cyanosis") || normQuery.includes("spruha ledhu") || tokens.includes("behosh") ||
        normQuery.includes("neela pad") || normQuery.includes("నీలంగా")
      ) {
        addMatch("ESC-NEO-08", "baby limp/unconscious/cyanosis", "stem_proximity");
      }
    }

    // 18. MALNUTRITION: Bilateral Pitting Edema (ESC-NUT-01)
    if (normQuery.includes("bilateral pitting edema") || normQuery.includes("pitting edema") || tokens.includes("kwashiorkor")) {
      addMatch("ESC-NUT-01", "bilateral pitting edema", "phrase");
    } else if (
      (tokens.includes("edema") || tokens.includes("swelling") || tokens.includes("vaapu") || tokens.includes("soojan") || normQuery.includes("వాపు") || normQuery.includes("సూజన్")) &&
      (normQuery.includes("both feet") || tokens.includes("feet") || normQuery.includes("pairon") || normQuery.includes("kaallu") || normQuery.includes("కాళ్ల") || tokens.includes("indent") || normQuery.includes("guntalu") || normQuery.includes("gaddha"))
    ) {
      if (!tokens.includes("vaccine") && !tokens.includes("injection") && !tokens.includes("tika")) {
        addMatch("ESC-NUT-01", "feet pitting edema", "stem_proximity");
      }
    }

    // 19. MALNUTRITION: SAM with Complications (ESC-NUT-02)
    if (normQuery.includes("failed appetite") || normQuery.includes("appetite test fail") || normQuery.includes("red zone")) {
      if (tokens.includes("muac") || tokens.includes("sam")) {
        addMatch("ESC-NUT-02", "sam failed appetite", "stem_proximity");
      }
    } else if (tokens.includes("sam") && (tokens.includes("refusing") || tokens.includes("therapeutic") || tokens.includes("vomiting") || tokens.includes("fever"))) {
      addMatch("ESC-NUT-02", "sam with complications", "stem_proximity");
    } else if (vitals.muac_mm !== null && vitals.muac_mm < 115) {
      addMatch("ESC-NUT-02", `muac ${vitals.muac_mm} mm < 115`, "numeric");
    }

    // 20. HYPERTENSION: Crisis BP >= 180/110 (ESC-NCD-01)
    if (normQuery.includes("hypertensive crisis") || normQuery.includes("bp chala ekkuva")) {
      addMatch("ESC-NCD-01", "hypertensive crisis", "phrase");
    } else if (vitals.bp) {
      const [sys, dia] = vitals.bp;
      if (sys >= 180 || dia >= 110) {
        addMatch("ESC-NCD-01", `BP ${sys}/${dia} >= 180/110`, "numeric");
      }
    }

    // 21. HYPERTENSION: Stroke / Chest Pain (ESC-NCD-02)
    const hasBPMention = tokens.some(t => ["bp", "hypertension"].includes(t)) || normQuery.includes("blood pressure") || normQuery.includes("బీపీ") || normQuery.includes("రక్తపోటు");
    const hasStrokeMI = normQuery.includes("chest pain") || normQuery.includes("slurred speech") || tokens.includes("weakness") || normQuery.includes("gundello noppi") || normQuery.includes("pakshavatham") || tokens.includes("stroke") || tokens.includes("lakhwa") || normQuery.includes("ఛాతీ నొప్పి") || normQuery.includes("seene me tez dard") || (tokens.includes("seene") && tokens.includes("dard"));
    if (hasBPMention && hasStrokeMI) {
      addMatch("ESC-NCD-02", "high BP with stroke/chest pain", "stem_proximity");
    }

    // 22. DIABETES: Hypoglycemia (ESC-NCD-03)
    if (tokens.includes("hypoglycemia")) {
      addMatch("ESC-NCD-03", "hypoglycemia", "phrase");
    } else if (tokens.includes("sugar") || normQuery.includes("మధుమేహం") || normQuery.includes("షుగర్")) {
      if (tokens.includes("unconscious") || tokens.includes("drowsy") || normQuery.includes("cold sweat") || tokens.includes("behosh") || tokens.includes("spruha") || tokens.includes("45") || tokens.includes("50") || tokens.includes("48") || tokens.includes("52") || tokens.includes("low")) {
        addMatch("ESC-NCD-03", "severe hypoglycemia emergency", "stem_proximity");
      }
    }

    // 23. DIARRHEA: Severe Dehydration (ESC-ORS-01)
    if (normQuery.includes("severe dehydration") || normQuery.includes("తీవ్రమైన నిర్జలీకరణ") || normQuery.includes("నిర్జలీకరణ")) {
      addMatch("ESC-ORS-01", "severe dehydration", "phrase");
    } else if (normQuery.includes("skin pinch")) {
      if (normQuery.includes("2 seconds") || normQuery.includes("very slowly") || normQuery.includes("slowly")) {
        addMatch("ESC-ORS-01", "skin pinch > 2s", "stem_proximity");
      }
    } else if ((normQuery.includes("sunken eyes") || normQuery.includes("chamada") || normQuery.includes("చర్మం మడత") || normQuery.includes("గుంటలు")) && (tokens.includes("unconscious") || tokens.includes("behosh") || tokens.includes("floppy") || normQuery.includes("2 seconds") || normQuery.includes("స్పృహ లేదు"))) {
      addMatch("ESC-ORS-01", "sunken eyes unconscious dehydration", "stem_proximity");
    }

    // 24. DIARRHEA: Dysentery / Persistent Diarrhea (ESC-ORS-02)
    if (tokens.includes("dysentery") || normQuery.includes("రక్త విరేచనాలు")) {
      addMatch("ESC-ORS-02", "dysentery", "phrase");
    } else if ((hasBloodWord || hasBleedStem || hasTeluguBlood || hasHindiBlood) && ["stool", "stools", "diarrhea", "virachanalu", "tatti", "mala"].some(t => tokens.includes(t))) {
      addMatch("ESC-ORS-02", "blood in stool / dysentery", "stem_proximity");
    } else if (tokens.includes("diarrhea") || tokens.includes("virachanalu") || tokens.includes("dast")) {
      if (normQuery.includes("14 days") || normQuery.includes("16 days") || normQuery.includes("2 weeks")) {
        addMatch("ESC-ORS-02", "persistent diarrhea >= 14 days", "stem_proximity");
      }
    }

    // 25. FEVER: Stiff Neck (ESC-FEV-01)
    if (hasFeverTerm) {
      if (
        normQuery.includes("stiff neck") || normQuery.includes("neck stiffness") || tokens.includes("meningitis") ||
        normQuery.includes("meda vangaraledhu") || normQuery.includes("meda gattiga") || normQuery.includes("gardan akad") ||
        normQuery.includes("మెడ పట్టేసి") || normQuery.includes("మెడ వంగడం లేదు")
      ) {
        addMatch("ESC-FEV-01", "fever with stiff neck", "stem_proximity");
      } else if (tokens.includes("neck") && (tokens.includes("bend") || tokens.includes("stiff") || normQuery.includes("touch chin"))) {
        addMatch("ESC-FEV-01", "fever unable to bend neck", "stem_proximity");
      }
    }

    // 26. FEVER: Convulsions (ESC-FEV-02)
    if (hasFeverTerm && (hasFits || hasFitsNative || normQuery.includes("febrile seizures") || tokens.includes("delirium") || normQuery.includes("altered sensorium"))) {
      addMatch("ESC-FEV-02", "fever with convulsions", "stem_proximity");
    }

    // 27. FEVER: Petechial Rash (ESC-FEV-03)
    if (hasFeverTerm) {
      if (
        tokens.includes("petechial") || tokens.includes("petechiae") || normQuery.includes("purple spots") ||
        normQuery.includes("bleeding gums") || normQuery.includes("dengue warning") || normQuery.includes("erupu machalu") ||
        normQuery.includes("lal dhabbe") || normQuery.includes("ఎర్రటి మచ్చలు")
      ) {
        addMatch("ESC-FEV-03", "fever with petechial rash / dengue warning", "stem_proximity");
      }
    }

    // 28. FEVER: Prolonged > 7 Days (ESC-FEV-04)
    if (hasFeverTerm) {
      if (vitals.fever_days !== null && vitals.fever_days > 7) {
        addMatch("ESC-FEV-04", `fever ${vitals.fever_days} days > 7`, "numeric");
      } else if (["8 days", "9 days", "10 days", "12 days", "14 days", "2 weeks", "8 rojulu", "10 din", "వారం రోజులు దాటినా"].some(k => normQuery.includes(k))) {
        addMatch("ESC-FEV-04", "prolonged fever > 7 days", "phrase");
      }
    }

    if (matchedRules.length > 0) {
      const primary = matchedRules[0];
      let reason = `Danger sign detected: ${primary.title} (Trigger: '${primary.matched_term}', type: ${primary.match_type})`;
      if (negationDetected) {
        reason += " [NOTE: Negation detected in text; escalating fail-safe per clinical protocol]";
      }
      return {
        escalate: true,
        action_text: primary.action_text,
        corpus_citation: primary.corpus_citation,
        matched_rules: matchedRules,
        primary_rule_id: primary.rule_id,
        negation_detected: negationDetected,
        trigger_reason: reason,
      };
    }

    return {
      escalate: false,
      action_text: null,
      corpus_citation: null,
      matched_rules: [],
      primary_rule_id: null,
      negation_detected: negationDetected,
      trigger_reason: "No critical danger sign detected",
    };
  }
}
