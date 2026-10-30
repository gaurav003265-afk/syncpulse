/**
 * Text normalization and linguistic preprocessing for TypeScript client engine.
 */

export function normalizeText(text: string): string {
  if (!text) return "";

  // NFKD decomposition
  let norm = text.normalize("NFKD");

  // Replace curly quotes & dashes
  norm = norm.replace(/[’‘]/g, "'").replace(/[“”]/g, '"');
  norm = norm.replace(/[—–]/g, "-");

  // Lowercase
  norm = norm.toLowerCase();

  // Collapse repeated characters (3+ occurrences down to 2)
  norm = norm.replace(/([a-z])\1{2,}/g, "$1$1");

  // Collapse multiple spaces
  norm = norm.replace(/\s+/g, " ").trim();
  return norm;
}

export function tokenize(text: string): string[] {
  const norm = normalizeText(text);
  // Match Latin, Telugu (\u0c00-\u0c7f), Devanagari (\u0900-\u097f), and numbers
  const tokens = norm.match(/[\u0c00-\u0c7fa-z0-9\u0900-\u097f]+/g);
  return tokens || [];
}

export interface ExtractedVitals {
  bp: [number, number] | null;
  muac_mm: number | null;
  temp_c: number | null;
  fever_days: number | null;
  respiratory_rate: number | null;
}

export function extractVitals(text: string): ExtractedVitals {
  const norm = normalizeText(text);
  const vitals: ExtractedVitals = {
    bp: null,
    muac_mm: null,
    temp_c: null,
    fever_days: null,
    respiratory_rate: null,
  };

  // 1. Blood Pressure: e.g. "180/110", "190 by 115"
  const bpMatch = norm.match(/\b(?:bp|b\.p\.|blood pressure)?\s*(\d{2,3})\s*(?:[\/]|by)\s*(\d{2,3})\b/);
  if (bpMatch) {
    vitals.bp = [parseFloat(bpMatch[1]), parseFloat(bpMatch[2])];
  }

  // 2. MUAC: e.g. "muac 108 mm", "muac 11.2 cm"
  const muacMatch = norm.match(/\b(?:muac|arm circumference)\s*(?:is|=|:)?\s*(\d+(?:\.\d+)?)\s*(mm|cm)?\b/);
  if (muacMatch) {
    const val = parseFloat(muacMatch[1]);
    const unit = muacMatch[2];
    vitals.muac_mm = (unit === "cm" || val < 30) ? val * 10 : val;
  }

  // 3. Temperature: requires unit or keyword
  let tempMatch = norm.match(/\b(?:temp|temperature)\s*(?:is|=|:)?\s*(\d{2,3}(?:\.\d+)?)\s*(?:°|deg|degrees)?\s*([fc]|fahrenheit|celsius)?\b/);
  if (!tempMatch) {
    tempMatch = norm.match(/\b(\d{2,3}(?:\.\d+)?)\s*(?:°|deg|degrees)\s*([fc]|fahrenheit|celsius)?\b/);
  }
  if (!tempMatch) {
    tempMatch = norm.match(/\b(\d{2,3}(?:\.\d+)?)\s*([fc]|fahrenheit|celsius)\b/);
  }
  if (tempMatch) {
    const val = parseFloat(tempMatch[1]);
    const unit = tempMatch[2];
    if (unit === "c" || unit === "celsius" || (val < 45 && val > 30)) {
      vitals.temp_c = val;
    } else if (unit === "f" || unit === "fahrenheit" || (val >= 90 && val <= 115)) {
      vitals.temp_c = Math.round(((val - 32) * 5 / 9) * 10) / 10;
    }
  }

  // 4. Fever Days
  let feverMatch = norm.match(/\b(?:fever|jwaram|bukhar)\s*(?:for|since|past|lasting)?\s*(\d+)\s*days\b/);
  if (!feverMatch) {
    feverMatch = norm.match(/\b(\d+)\s*days\s*(?:of\s*)?(?:fever|jwaram|bukhar)\b/);
  }
  if (!feverMatch) {
    const feverWMatch = norm.match(/\b(\d+)\s*weeks?\s*(?:of\s*)?(?:fever|jwaram|bukhar)\b/);
    if (feverWMatch) {
      vitals.fever_days = parseFloat(feverWMatch[1]) * 7;
    }
  } else {
    vitals.fever_days = parseFloat(feverMatch[1]);
  }

  // 5. Respiratory Rate
  let rrMatch = norm.match(/\b(?:respiratory rate|breathing rate|breaths per min(?:ute)?|rr)\s*(?:is|=|:)?\s*(\d{2,3})\b/);
  if (!rrMatch) {
    rrMatch = norm.match(/\b(\d{2,3})\s*(?:breaths|breaths\/min|breaths per minute)\b/);
  }
  if (rrMatch) {
    vitals.respiratory_rate = parseFloat(rrMatch[1]);
  }

  return vitals;
}
