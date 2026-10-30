import React, { useState, useEffect, useRef } from "react";
import {
  Search,
  AlertTriangle,
  CheckCircle,
  HelpCircle,
  ShieldAlert,
  BookOpen,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  X,
  PhoneCall,
  Info,
  Clock,
  ArrowRight,
  Globe,
  RotateCcw,
  Square,
  Edit3,
  Check,
  Save,
} from "lucide-react";
import { dataService } from "../engine/dataService";
import { PipelineTS, PipelineResponseTS } from "../engine/pipeline";
import { validateTranscriptTS } from "../engine/speech";
import { NavTab } from "./Navbar";

export type SupportedLanguage = "en" | "te" | "hi";

interface AskScreenProps {
  pipelineTS: PipelineTS;
  isOnline: boolean;
  initialQuery?: string;
  setActiveTab?: (tab: NavTab) => void;
  selectedLanguage?: SupportedLanguage;
  onSelectLanguage?: (lang: SupportedLanguage) => void;
}

type VoiceState =
  | "idle"
  | "requesting_permission"
  | "listening"
  | "transcribing"
  | "reviewing"
  | "silence"
  | "unclear_noisy"
  | "permission_denied"
  | "network_error";

const LANGUAGE_CONFIGS: Record<
  SupportedLanguage,
  {
    name: string;
    speechLang: string;
    ttsLang: string;
    chips: Array<{ label: string; text: string }>;
  }
> = {
  en: {
    name: "English",
    speechLang: "en-IN",
    ttsLang: "en-IN",
    chips: [
      { label: "🚨 3rd Tri Bleeding", text: "Woman 7 months pregnant has heavy vaginal bleeding" },
      { label: "📅 ANC Schedule", text: "What is the schedule for routine ANC visits?" },
      { label: "👶 Fast Breathing Newborn", text: "Newborn baby chest indrawing fast breathing rr >= 60" },
      { label: "💧 ORS Preparation", text: "How to prepare 1 liter of ORS solution?" },
      { label: "🚫 Amoxicillin Dose (Refusal)", text: "What dose of amoxicillin should I prescribe?" },
      { label: "🌐 Telugu Code-Mix", text: "7 nelala garbhavathi bleeding ekkuva ga undi" },
      { label: "❓ Out of Scope Query", text: "Who won the cricket world cup?" },
    ],
  },
  te: {
    name: "తెలుగు (Telugu)",
    speechLang: "te-IN",
    ttsLang: "te-IN",
    chips: [
      { label: "🚨 రక్తస్రావం (Bleeding)", text: "గర్భవతికి తీవ్రమైన రక్తస్రావం అవుతోంది" },
      { label: "⚡ ఫిట్స్ (Fits)", text: "గర్భిణీ స్త్రీకి ఫిట్స్ మరియు స్పృహ తప్పిపోయింది" },
      { label: "📅 ఏఎన్‌సీ పర్యటనలు", text: "గర్భిణీ స్త్రీకి ఎన్ని ఏఎన్‌సీ సందర్శనలు అవసరం?" },
      { label: "💧 ఓఆర్‌ఎస్ తయారీ", text: "ఒక లీటర్ ఓఆర్‌ఎస్ ద్రావణం ఎలా తయారు చేయాలి?" },
      { label: "💉 టీకాల షెడ్యూల్", text: "శిశువుకు పెంటావాలెంట్ టీకా ఎప్పుడు ఇవ్వాలి?" },
      { label: "🚫 యాంటీబయాటిక్ (Refusal)", text: "పంటి నొప్పికి అమోక్సిసిలిన్ ఎంత మోతాదు ఇవ్వాలి?" },
    ],
  },
  hi: {
    name: "हिंदी (Hindi)",
    speechLang: "hi-IN",
    ttsLang: "hi-IN",
    chips: [
      { label: "🚨 तेज रक्तस्राव (Bleeding)", text: "गर्भवती महिला को अचानक तेज रक्तस्राव हो रहा है" },
      { label: "⚡ दौरे (Fits/Eclampsia)", text: "गर्भावस्था में महिला को दौरे आ रहे हैं और सिरदर्द है" },
      { label: "👶 तेज सांस (Newborn RR)", text: "नवजात शिशु की सांस बहुत तेज चल रही है छाती धंस रही है" },
      { label: "💧 ओआरएस घोल", text: "दस्त में ओआरएस का 1 लीटर घोल कैसे तैयार करें?" },
      { label: "💉 टीकाकरण समय सारणी", text: "शिशु के लिए पेंटावेलेंट टीका कब दिया जाता है?" },
      { label: "🚫 एंटीबायोटिक खुराक (Refusal)", text: "बच्चे को एमोक्सिसिलिन की कितनी खुराक देनी चाहिए?" },
    ],
  },
};

export const AskScreen: React.FC<AskScreenProps> = ({
  pipelineTS,
  isOnline,
  initialQuery = "",
  setActiveTab,
  selectedLanguage = "en",
  onSelectLanguage,
}) => {
  const [currentLang, setCurrentLang] = useState<SupportedLanguage>(selectedLanguage);
  const [query, setQuery] = useState(initialQuery);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PipelineResponseTS | null>(null);
  const [usedEngine, setUsedEngine] = useState<string>("");

  // Voice Recognition States
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [capturedTranscript, setCapturedTranscript] = useState("");
  const [editableTranscript, setEditableTranscript] = useState("");
  const [voiceEmergencyBypass, setVoiceEmergencyBypass] = useState(false);
  const [voiceNotice, setVoiceNotice] = useState<string | null>(null);

  // Speech Synthesis (TTS) States
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [ttsSupported, setTtsSupported] = useState(false);
  const [recordedEmergencyId, setRecordedEmergencyId] = useState<string | null>(null);

  const recognitionRef = useRef<any>(null);
  const timerRef = useRef<any>(null);

  useEffect(() => {
    if (selectedLanguage) {
      setCurrentLang(selectedLanguage);
    }
  }, [selectedLanguage]);

  useEffect(() => {
    if (initialQuery) {
      setQuery(initialQuery);
      handleSearch(initialQuery);
    }
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      setTtsSupported(true);
    }
    return () => {
      stopSpeaking();
      stopRecording();
    };
  }, [initialQuery]);

  // Handle language switch
  const handleLanguageChange = (lang: SupportedLanguage) => {
    setCurrentLang(lang);
    if (onSelectLanguage) {
      onSelectLanguage(lang);
    }
    stopSpeaking();
    stopRecording();
  };

  const handleSearch = async (queryText: string) => {
    const cleanText = queryText.trim();
    if (!cleanText) return;

    setLoading(true);
    setResult(null);
    setRecordedEmergencyId(null);
    setVoiceNotice(null);
    setVoiceEmergencyBypass(false);
    stopSpeaking();

    try {
      let finalRes: any = null;
      if (!isOnline) {
        // 100% offline on-device client execution
        finalRes = pipelineTS.processQuery(cleanText);
        setResult(finalRes);
        setUsedEngine("Client TypeScript Engine (100% Offline)");
      } else {
        // Online mode with automatic fallback to client engine
        try {
          const response = await fetch("/api/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: cleanText }),
          });
          if (response.ok) {
            finalRes = await response.json();
            setResult(finalRes);
            setUsedEngine("FastAPI Local Hub (Python Core)");
          } else {
            throw new Error("Server error");
          }
        } catch {
          finalRes = pipelineTS.processQuery(cleanText);
          setResult(finalRes);
          setUsedEngine("Client TypeScript Engine (Offline Fallback)");
        }
      }

      // If danger sign escalation occurred, record event locally
      if (finalRes && finalRes.type === "escalate") {
        const primary = finalRes.matched_rules && finalRes.matched_rules[0];
        const newAlt = dataService.recordEmergencyFromEscalation(
          cleanText,
          primary ? primary.title : "Obstetric / Neonatal Danger Sign",
          finalRes.text,
          finalRes.primary_citation
        );
        setRecordedEmergencyId(newAlt.alert_id);
      }
    } catch (err: any) {
      console.error("Pipeline query execution failure:", err);
    } finally {
      setLoading(false);
    }
  };

  // Start voice recording
  const startRecording = () => {
    stopSpeaking();
    setVoiceNotice(null);
    setCapturedTranscript("");
    setEditableTranscript("");
    setVoiceEmergencyBypass(false);

    const SpeechRec =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRec) {
      setVoiceState("permission_denied");
      setVoiceNotice(
        "Offline Voice Status: Browser Speech API is not supported in this browser. Please use the text keyboard or quick symptom chips below."
      );
      return;
    }

    try {
      const recognition = new SpeechRec();
      recognitionRef.current = recognition;
      recognition.lang = LANGUAGE_CONFIGS[currentLang].speechLang;
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;

      setVoiceState("requesting_permission");

      recognition.onstart = () => {
        setVoiceState("listening");
        setRecordingSeconds(0);
        timerRef.current = setInterval(() => {
          setRecordingSeconds((prev) => prev + 1);
        }, 1000);
      };

      recognition.onresult = (event: any) => {
        clearInterval(timerRef.current);
        const transcript = event.results[0][0].transcript;
        processCapturedVoice(transcript);
      };

      recognition.onerror = (event: any) => {
        clearInterval(timerRef.current);
        console.warn("Speech recognition error:", event.error);
        if (event.error === "no-speech") {
          setVoiceState("silence");
          setVoiceNotice(
            "No audio speech detected. Please speak closer to the microphone or use the text box below."
          );
        } else if (event.error === "network") {
          setVoiceState("network_error");
          setVoiceNotice(
            "⚠️ Offline Notice: Android Chrome speech-to-text requires internet on devices without pre-downloaded offline speech packs. Please use the keyboard text input or quick chips below."
          );
        } else if (event.error === "not-allowed" || event.error === "permission-denied") {
          setVoiceState("permission_denied");
          setVoiceNotice(
            "Microphone access denied. Please allow microphone permission in your browser settings or use text entry."
          );
        } else {
          setVoiceState("unclear_noisy");
          setVoiceNotice(`Voice capture error (${event.error}). Please re-speak or type your query.`);
        }
      };

      recognition.onend = () => {
        clearInterval(timerRef.current);
        if (voiceState === "listening" || voiceState === "requesting_permission") {
          setVoiceState("idle");
        }
      };

      recognition.start();
    } catch (err: any) {
      clearInterval(timerRef.current);
      setVoiceState("permission_denied");
      setVoiceNotice("Could not access microphone. Please type your query.");
    }
  };

  const stopRecording = () => {
    clearInterval(timerRef.current);
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        // ignore already stopped
      }
      recognitionRef.current = null;
    }
  };

  const cancelRecording = () => {
    stopRecording();
    setVoiceState("idle");
    setRecordingSeconds(0);
    setVoiceNotice("Voice recording canceled.");
  };

  // STEP 3, 4, 5 of Voice Pipeline
  const processCapturedVoice = (rawTranscript: string) => {
    setVoiceState("transcribing");
    const validation = validateTranscriptTS(rawTranscript);

    if (!validation.is_understandable) {
      if (validation.status === "silence") {
        setVoiceState("silence");
      } else {
        setVoiceState("unclear_noisy");
      }
      setVoiceNotice(validation.message);
      return;
    }

    const cleanTranscript = validation.cleaned_text;
    setCapturedTranscript(cleanTranscript);
    setEditableTranscript(cleanTranscript);

    // CRITICAL SAFETY CHECK (Step 4 & 5): Check Emergency Gate BEFORE asking for confirmation!
    const escCheck = pipelineTS.checkEscalation(cleanTranscript);

    if (escCheck.escalate) {
      // DO NOT DELAY URGENT GUIDANCE!
      // Immediately bypass transcript confirmation modal and render emergency triage card
      setVoiceEmergencyBypass(true);
      setVoiceState("idle");
      setQuery(cleanTranscript);
      handleSearch(cleanTranscript);
    } else {
      // Routine inquiry: Present transcript review & correction modal to user before submission
      setVoiceState("reviewing");
    }
  };

  const handleConfirmTranscript = () => {
    const finalQuery = editableTranscript.trim() || capturedTranscript;
    setVoiceState("idle");
    setQuery(finalQuery);
    handleSearch(finalQuery);
  };

  // Offline TTS toggle
  const toggleSpeakAnswer = (textToSpeak: string) => {
    if (!ttsSupported || typeof window === "undefined") return;

    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }

    window.speechSynthesis.cancel();
    // Clean markdown symbols for natural vocalization
    const cleanText = textToSpeak
      .replace(/[*#_`•🚨📅👶💧🚫🌐❓⚡💉]/g, "")
      .replace(/Lines?\s+\d+-\d+/gi, "")
      .replace(/\s+/g, " ")
      .trim();

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = LANGUAGE_CONFIGS[currentLang].ttsLang;
    utterance.rate = 0.9; // Measured clinical comprehension speed

    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    window.speechSynthesis.speak(utterance);
    setIsSpeaking(true);
  };

  const stopSpeaking = () => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  };

  const handleClear = () => {
    setQuery("");
    setResult(null);
    setCapturedTranscript("");
    setEditableTranscript("");
    setVoiceNotice(null);
    setVoiceEmergencyBypass(false);
    stopSpeaking();
    stopRecording();
    setVoiceState("idle");
  };

  const currentConfig = LANGUAGE_CONFIGS[currentLang];

  return (
    <div className="space-y-4 pb-16 sm:pb-6">
      {/* Search Header & Input Box */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 sm:p-5 space-y-3.5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
          <div className="flex items-center space-x-2">
            <Search className="w-5 h-5 text-teal-700" />
            <div>
              <h2 className="text-base font-bold text-slate-900 leading-tight">
                Ask Sakhi — Offline Clinical Decision Support
              </h2>
              <p className="text-[11px] text-slate-500">
                100% Offline MoHFW Clinical Protocols & Deterministic Safety Gate
              </p>
            </div>
          </div>

          {/* Multilingual Selector */}
          <div className="flex items-center space-x-1.5 self-start sm:self-auto bg-slate-100 p-1 rounded-lg border border-slate-200">
            <Globe className="w-3.5 h-3.5 text-slate-500 ml-1" />
            {(["en", "te", "hi"] as SupportedLanguage[]).map((lang) => (
              <button
                key={lang}
                type="button"
                onClick={() => handleLanguageChange(lang)}
                className={`text-xs font-bold px-2 py-1 rounded transition ${
                  currentLang === lang
                    ? "bg-teal-700 text-white shadow-xs"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/60"
                }`}
                title={`Switch language to ${LANGUAGE_CONFIGS[lang].name}`}
              >
                {lang === "en" ? "EN" : lang === "te" ? "తెలుగు" : "हिंदी"}
              </button>
            ))}
          </div>
        </div>

        {/* Query Input Bar */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSearch(query);
          }}
          className="space-y-2"
        >
          <div className="relative flex items-center">
            <Search className="w-5 h-5 text-slate-400 absolute left-3.5 pointer-events-none" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={
                currentLang === "te"
                  ? "లక్షణం, ప్రమాద సంకేతం, ఏఎన్‌సీ పర్యటనలు, టీకాలు లేదా ఓఆర్‌ఎస్ అడగండి..."
                  : currentLang === "hi"
                  ? "लक्षण, खतरे के संकेत, एएनसी विजिट, टीका या ओआरएस पूछें..."
                  : "Ask symptom, danger sign, ANC schedule, immunization, ORS..."
              }
              className="w-full pl-10 pr-28 py-3 bg-slate-50 border border-slate-300 rounded-xl text-sm sm:text-base focus:outline-none focus:ring-2 focus:ring-teal-600 focus:bg-white text-slate-900 shadow-inner"
            />

            {/* Clear Button */}
            {query && (
              <button
                type="button"
                onClick={handleClear}
                className="absolute right-20 text-slate-400 hover:text-slate-600 p-1"
                title="Clear query"
              >
                <X className="w-4 h-4" />
              </button>
            )}

            {/* Mic / Voice Button */}
            <button
              type="button"
              onClick={voiceState === "listening" ? stopRecording : startRecording}
              className={`absolute right-12 p-2 rounded-lg transition ${
                voiceState === "listening"
                  ? "bg-red-600 text-white animate-pulse"
                  : voiceState === "requesting_permission"
                  ? "bg-amber-500 text-white animate-bounce"
                  : "text-slate-500 hover:bg-slate-200"
              }`}
              title={
                voiceState === "listening"
                  ? "Stop recording"
                  : `Voice Input (${currentConfig.name})`
              }
              aria-label="Voice Search"
            >
              {voiceState === "listening" ? <Square className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            </button>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="absolute right-1.5 px-3.5 py-2 bg-teal-700 hover:bg-teal-800 disabled:bg-slate-300 text-white text-xs font-bold rounded-lg shadow-sm transition"
            >
              {loading ? "Searching..." : "Ask"}
            </button>
          </div>
        </form>

        {/* ACTIVE VOICE RECORDING STATE PANEL */}
        {voiceState === "listening" && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-3 flex items-center justify-between text-xs animate-pulse">
            <div className="flex items-center space-x-2.5">
              <span className="w-3 h-3 bg-red-600 rounded-full animate-ping" />
              <span className="font-bold text-red-900">
                Listening ({currentConfig.name})... Speak clinical query
              </span>
              <span className="font-mono text-red-700 bg-red-100 px-1.5 py-0.5 rounded">
                00:{recordingSeconds < 10 ? `0${recordingSeconds}` : recordingSeconds}s
              </span>
            </div>
            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={stopRecording}
                className="bg-red-600 hover:bg-red-700 text-white px-2.5 py-1 rounded text-xs font-bold flex items-center space-x-1"
              >
                <Square className="w-3 h-3" />
                <span>Done</span>
              </button>
              <button
                type="button"
                onClick={cancelRecording}
                className="bg-slate-200 hover:bg-slate-300 text-slate-700 px-2 py-1 rounded text-xs font-semibold"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* TRANSCRIPT PRE-SUBMISSION REVIEW & CORRECTION BOX (For Routine Questions) */}
        {voiceState === "reviewing" && (
          <div className="bg-teal-50/70 border-2 border-teal-500 rounded-xl p-3.5 space-y-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-1.5 text-xs font-bold text-teal-900">
                <Edit3 className="w-4 h-4 text-teal-700" />
                <span>Review & Correct Voice Transcript Before Search:</span>
              </div>
              <span className="text-[10px] text-teal-700 font-semibold bg-teal-100 px-2 py-0.5 rounded">
                Language: {currentConfig.name}
              </span>
            </div>

            <textarea
              rows={2}
              value={editableTranscript}
              onChange={(e) => setEditableTranscript(e.target.value)}
              className="w-full bg-white border border-teal-300 rounded-lg p-2.5 text-xs font-medium text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-600"
              placeholder="Correct any misheard clinical words..."
            />

            <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
              <div className="flex items-center space-x-1 text-[11px] text-slate-500">
                <span>Check dosage numbers and symptoms before proceeding</span>
              </div>
              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={startRecording}
                  className="bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 px-2.5 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1 transition"
                >
                  <RotateCcw className="w-3.5 h-3.5 text-slate-500" />
                  <span>Re-record</span>
                </button>
                <button
                  type="button"
                  onClick={() => setVoiceState("idle")}
                  className="bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleConfirmTranscript}
                  className="bg-teal-700 hover:bg-teal-800 text-white px-3.5 py-1.5 rounded-lg text-xs font-bold flex items-center space-x-1.5 shadow-sm transition"
                >
                  <Check className="w-3.5 h-3.5" />
                  <span>Confirm & Search Protocols</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* IMMEDIATE EMERGENCY AUTO-BYPASS BADGE */}
        {voiceEmergencyBypass && (
          <div className="bg-red-600 text-white px-3 py-2 rounded-lg text-xs font-bold flex items-center space-x-2 shadow-sm animate-pulse">
            <ShieldAlert className="w-4 h-4 shrink-0" />
            <span>
              🚨 Critical emergency sign recognized from voice audio! Immediate life-safety guidance displayed without waiting for transcript confirmation.
            </span>
          </div>
        )}

        {/* VOICE ERROR / FEEDBACK NOTICES */}
        {voiceNotice && (
          <div className="flex items-start space-x-2 text-xs bg-amber-50 text-amber-900 p-2.5 rounded-lg border border-amber-300">
            <Info className="w-4 h-4 shrink-0 text-amber-700 mt-0.5" />
            <div className="space-y-1">
              <p className="font-medium">{voiceNotice}</p>
              <p className="text-[11px] text-amber-800">
                You can always type directly in the search bar above or tap one of the quick symptom chips below.
              </p>
            </div>
          </div>
        )}

        {/* Quick Suggestion Chips for Current Language */}
        <div className="pt-1">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-semibold text-slate-500">
              Verified {currentConfig.name} Clinical Scenarios:
            </span>
            <span className="text-[10px] text-slate-400">
              Tap chip to test voice-to-search parity
            </span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {currentConfig.chips.map((chip, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => {
                  setQuery(chip.text);
                  handleSearch(chip.text);
                }}
                className="text-[11px] font-medium bg-slate-100 hover:bg-teal-50 hover:text-teal-900 text-slate-700 px-2.5 py-1 rounded-full border border-slate-200 transition"
              >
                {chip.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Loading Skeleton */}
      {loading && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-3 animate-pulse">
          <div className="flex items-center space-x-2">
            <div className="w-5 h-5 bg-teal-200 rounded-full" />
            <div className="h-4 bg-slate-200 rounded w-1/3" />
          </div>
          <div className="h-3 bg-slate-100 rounded w-full" />
          <div className="h-3 bg-slate-100 rounded w-4/5" />
          <div className="h-3 bg-slate-100 rounded w-2/3" />
        </div>
      )}

      {/* RESULT CARDS: 4 DISTINCT PIPELINE OUTCOMES */}
      {result && !loading && (
        <div className="space-y-4">
          {/* 1. STAGE 1: DANGER SIGN EMERGENCY ESCALATION */}
          {result.type === "escalate" && (
            <div className="bg-red-50 border-2 border-red-500 rounded-2xl p-5 shadow-md space-y-4">
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-2 text-red-700">
                  <ShieldAlert className="w-7 h-7 shrink-0 text-red-600 animate-bounce" />
                  <div>
                    <h3 className="text-base sm:text-lg font-black tracking-tight text-red-900">
                      🚨 REFER IMMEDIATELY: Obstetric / Neonatal Emergency
                    </h3>
                    <p className="text-xs text-red-700 font-semibold">
                      Deterministic Safety Gate Triggered (Bypassed All Search)
                    </p>
                  </div>
                </div>

                {ttsSupported && (
                  <button
                    onClick={() => toggleSpeakAnswer(result.text)}
                    className="p-2 text-red-700 hover:bg-red-100 rounded-lg transition"
                    title={isSpeaking ? "Stop Speaking" : "Read Aloud"}
                  >
                    {isSpeaking ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
                  </button>
                )}
              </div>

              {/* Action Protocol Steps */}
              <div className="bg-white/90 p-4 rounded-xl border border-red-200 text-sm text-red-950 font-medium whitespace-pre-line leading-relaxed shadow-xs">
                {result.text}
              </div>

              {/* Transparent Offline Event Notice */}
              <div className="bg-white/95 border border-red-300 rounded-xl p-3 text-xs text-red-950 space-y-1.5 shadow-xs">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-1.5 font-bold text-red-900">
                    <Save className="w-3.5 h-3.5 text-red-700" />
                    <span>Emergency Event Recorded in Local Register</span>
                  </div>
                  {recordedEmergencyId && (
                    <span className="font-mono text-[10px] bg-red-100 text-red-900 px-2 py-0.5 rounded font-bold border border-red-200">
                      ID: {recordedEmergencyId}
                    </span>
                  )}
                </div>
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="bg-amber-600 text-white font-black text-[9px] px-2 py-0.5 rounded uppercase tracking-wider">
                    Saved Locally (On-Device Only)
                  </span>
                  <span className="bg-slate-200 text-slate-800 font-bold text-[9px] px-2 py-0.5 rounded">
                    Notification Service Not Configured
                  </span>
                </div>
                <p className="text-[11px] text-slate-700 leading-relaxed">
                  <strong>Transparency Notice:</strong> This clinical danger sign has been preserved safely on this device. <strong>No ambulance, hospital, or doctor has been notified automatically.</strong> Frontline workers must dial <strong>108 directly on cellular mobile</strong>.
                </p>
              </div>

              {/* Direct 108 Emergency Call Button */}
              <div className="flex flex-col sm:flex-row items-center gap-2 pt-1">
                <a
                  href="tel:108"
                  className="w-full sm:w-auto flex-1 bg-red-600 hover:bg-red-700 text-white font-bold py-2.5 px-4 rounded-xl text-center shadow-sm flex items-center justify-center space-x-2 transition"
                >
                  <PhoneCall className="w-4 h-4" />
                  <span>Call 108 Ambulance Now</span>
                </a>
                {setActiveTab && (
                  <button
                    onClick={() => setActiveTab("emergency")}
                    className="w-full sm:w-auto bg-white hover:bg-red-50 text-red-700 border border-red-300 font-bold py-2.5 px-4 rounded-xl text-xs transition"
                  >
                    Open in Emergency Desk
                  </button>
                )}
              </div>

              {/* Protocol Citation */}
              {result.primary_citation && (
                <div className="text-[11px] text-red-700 font-mono flex items-center space-x-1.5 border-t border-red-200 pt-2">
                  <BookOpen className="w-3.5 h-3.5" />
                  <span>Approved Source: {result.primary_citation}</span>
                </div>
              )}
            </div>
          )}

          {/* 2. STAGE 2: PARAMEDICAL SCOPE REFUSAL */}
          {result.type === "refuse" && (
            <div className="bg-amber-50 border-2 border-amber-500 rounded-2xl p-5 shadow-md space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-amber-800">
                  <AlertTriangle className="w-6 h-6 text-amber-600" />
                  <h3 className="text-base font-bold text-amber-900">
                    Paramedical Scope Boundary Enforced
                  </h3>
                </div>
                {ttsSupported && (
                  <button
                    onClick={() => toggleSpeakAnswer(result.text)}
                    className="p-2 text-amber-700 hover:bg-amber-100 rounded-lg transition"
                    title={isSpeaking ? "Stop Speaking" : "Read Aloud"}
                  >
                    {isSpeaking ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
                  </button>
                )}
              </div>

              <div className="bg-white/90 p-4 rounded-xl border border-amber-200 text-sm text-amber-950 font-medium leading-relaxed">
                {result.text}
              </div>

              <div className="text-xs text-amber-800 space-y-1">
                <p>
                  <strong>Legal Notice:</strong> Under MoHFW guidelines, ASHA and ANM workers may dispense approved standing remedies (ORS, Zinc, IFA, Calcium, Albendazole, Paracetamol) but must NEVER prescribe prescription antibiotics or make surgical evaluations.
                </p>
              </div>
            </div>
          )}

          {/* 3. STAGE 3/4: GROUNDED PROTOCOL GUIDANCE */}
          {result.type === "answer" && (
            <div className="bg-white border border-teal-300 rounded-2xl p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center space-x-2">
                  <CheckCircle className="w-5 h-5 text-teal-600" />
                  <div>
                    <h3 className="text-base font-bold text-slate-900">
                      Approved Protocol Guidance
                    </h3>
                    <span className="text-[11px] text-teal-700 font-medium">
                      100% Extractive Grounding • Zero Generative Drift
                    </span>
                  </div>
                </div>

                {ttsSupported && (
                  <button
                    onClick={() => toggleSpeakAnswer(result.text)}
                    className="p-2 text-teal-700 hover:bg-teal-50 rounded-lg transition"
                    title={isSpeaking ? "Stop Speaking" : "Read Aloud"}
                  >
                    {isSpeaking ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
                  </button>
                )}
              </div>

              {/* Extractive Text */}
              <div className="text-sm text-slate-800 leading-relaxed font-sans whitespace-pre-line bg-teal-50/30 p-3.5 rounded-xl border border-teal-100">
                {result.text}
              </div>

              {/* Multilingual Notice */}
              {currentLang !== "en" && (
                <div className="text-[11px] text-slate-500 italic bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                  ℹ️ <strong>Clinical Safety Note:</strong> Official clinical protocol text is cited verbatim from authoritative MoHFW/WHO guidelines to ensure medical dosage accuracy.
                </div>
              )}

              {/* Source Verification Citation */}
              {result.primary_citation && (
                <div className="bg-slate-50 border border-slate-200 p-3 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                  <div className="flex items-center space-x-2 text-teal-900 font-semibold">
                    <BookOpen className="w-4 h-4 text-teal-700" />
                    <span>Official Citation: {result.primary_citation}</span>
                  </div>
                  <span className="text-[11px] font-mono text-slate-500">
                    Confidence: {(result.confidence * 100).toFixed(0)}% • Latency: {result.latency_ms} ms
                  </span>
                </div>
              )}
            </div>
          )}

          {/* 4. PROTOCOL ABSTENTION */}
          {result.type === "abstain" && (
            <div className="bg-slate-50 border border-slate-300 rounded-2xl p-5 shadow-sm space-y-3">
              <div className="flex items-center space-x-2 text-slate-700">
                <HelpCircle className="w-5 h-5 text-slate-500" />
                <h3 className="text-base font-bold text-slate-900">
                  Topic Not Covered in Approved Protocols
                </h3>
              </div>
              <div className="text-xs text-slate-600 leading-relaxed bg-white p-3.5 rounded-xl border border-slate-200">
                {result.text}
              </div>
              <p className="text-[11px] text-slate-500">
                SyncPulse enforces strict evidence abstention: if a query cannot be verified against official MoHFW/WHO clinical documents, the system refuses to guess or hallucinate. Please refer patient to PHC Medical Officer.
              </p>
            </div>
          )}

          {/* Runtime Engine Diagnostics Badge */}
          <div className="text-[11px] text-slate-400 font-mono flex items-center justify-between px-1">
            <span>Executed via: {usedEngine}</span>
            <span>Latency: {result.latency_ms} ms</span>
          </div>
        </div>
      )}
    </div>
  );
};
