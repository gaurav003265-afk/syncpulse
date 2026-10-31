/**
 * SyncPulse Offline Telephony & Emergency Signal Engine
 * Zero-bandwidth GSM SMS intent encoding, clipboard payload formatting,
 * native telephony dialer links, and zero-asset Web Audio emergency siren.
 */

export interface EmergencyPayload {
  recipient?: string;
  patientName: string;
  village: string;
  symptoms: string;
  phone?: string;
  lat?: number | null;
  lon?: number | null;
  severity?: "CRITICAL" | "URGENT" | "ROUTINE";
  triageCategory?: string;
}

/**
 * Formats a concise standard 140-character emergency payload for SMS transmission.
 */
export function formatEmergencyTextPayload(data: EmergencyPayload): string {
  const parts: string[] = [
    `🚨 EMERGENCY [108]: ${data.patientName || "Unknown Patient"}`,
    `Vill: ${data.village || "Unknown"}`,
    `Issue: ${data.symptoms || "Critical Condition"}`,
  ];

  if (data.phone) {
    parts.push(`Ph: ${data.phone}`);
  }

  if (typeof data.lat === "number" && typeof data.lon === "number") {
    parts.push(`GPS: ${data.lat.toFixed(5)},${data.lon.toFixed(5)}`);
  }

  return parts.join(" | ");
}

/**
 * Formats a cross-platform GSM SMS URI for native mobile messaging apps.
 * Handles iOS (which requires '&body=') and Android/RFC (which uses '?body=').
 */
export function formatGsmSmsUri(data: EmergencyPayload): string {
  const recipient = data.recipient || "108";
  const bodyText = formatEmergencyTextPayload(data);
  const encodedBody = encodeURIComponent(bodyText);

  const isIOS =
    typeof navigator !== "undefined" &&
    /iPad|iPhone|iPod/.test(navigator.userAgent || "");

  const separator = isIOS ? "&body=" : "?body=";
  return `sms:${recipient}${separator}${encodedBody}`;
}

/**
 * Dispatches the emergency SMS intent via native browser navigation.
 */
export function dispatchGsmSms(data: EmergencyPayload): boolean {
  try {
    const uri = formatGsmSmsUri(data);
    if (typeof window !== "undefined") {
      window.location.href = uri;
      return true;
    }
  } catch (err) {
    console.warn("SMS intent navigation note:", err);
  }
  return false;
}

/**
 * Copies the emergency triage payload to the device clipboard.
 */
export async function copyEmergencyPayloadToClipboard(data: EmergencyPayload): Promise<boolean> {
  const text = formatEmergencyTextPayload(data);
  try {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch (err) {
    console.warn("Clipboard write failed, fallback:", err);
  }

  // Fallback for older browsers
  try {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    textArea.style.left = "-9999px";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    const success = document.execCommand("copy");
    document.body.removeChild(textArea);
    return success;
  } catch (err) {
    return false;
  }
}

/**
 * Triggers native 108 (General Emergency Ambulance) phone call.
 */
export function callEmergency108(): void {
  if (typeof window !== "undefined") {
    window.location.href = "tel:108";
  }
}

/**
 * Triggers native 102 (Maternal & Infant Ambulance) phone call.
 */
export function callMaternal102(): void {
  if (typeof window !== "undefined") {
    window.location.href = "tel:102";
  }
}

/**
 * Synthesizes an emergency alert siren using the HTML5 Web Audio API.
 * Requires 0 KB audio assets, 0 network, runs 100% on CPU/DSP.
 * Alternates between 880 Hz (A5) and 1240 Hz (D#6).
 * Returns a cancellation callback function.
 */
let activeAudioContext: AudioContext | null = null;
let activeOscillator: OscillatorNode | null = null;

export function playEmergencySiren(durationSeconds: number = 6): () => void {
  try {
    const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    if (!AudioCtx) return () => {};

    // Stop any existing siren first
    stopEmergencySiren();

    const ctx = new AudioCtx();
    activeAudioContext = ctx;

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = "sawtooth";
    gain.gain.setValueAtTime(0.12, ctx.currentTime);

    const now = ctx.currentTime;
    const stepDuration = 0.35; // 350ms tone alternation
    const steps = Math.floor(durationSeconds / stepDuration);

    for (let i = 0; i < steps; i++) {
      const freq = i % 2 === 0 ? 880 : 1240;
      osc.frequency.setValueAtTime(freq, now + i * stepDuration);
    }

    // Soft fade-out at the end
    gain.gain.setValueAtTime(0.12, now + durationSeconds - 0.2);
    gain.gain.linearRampToValueAtTime(0.001, now + durationSeconds);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(now);
    osc.stop(now + durationSeconds);
    activeOscillator = osc;

    osc.onended = () => {
      stopEmergencySiren();
    };

    return stopEmergencySiren;
  } catch (err) {
    console.warn("Web Audio API siren not permitted in this context:", err);
    return () => {};
  }
}

export function stopEmergencySiren(): void {
  try {
    if (activeOscillator) {
      activeOscillator.stop();
      activeOscillator.disconnect();
      activeOscillator = null;
    }
    if (activeAudioContext && activeAudioContext.state !== "closed") {
      activeAudioContext.close();
      activeAudioContext = null;
    }
  } catch {
    // Ignore cleanup errors
  }
}

