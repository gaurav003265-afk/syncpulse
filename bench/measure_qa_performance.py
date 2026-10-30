"""
Rigorous performance measurement script for SyncPulse / Sakhi FieldOS QA review.
Measures:
1. Exact file sizes of installed assets, database, knowledge pack, rules, and frontend bundle.
2. Startup latency (Pipeline, BM25 retriever, Escalation engine).
3. Memory consumption (peak RAM via tracemalloc).
4. CPU inference latency percentiles (mean, p50, p95, max) for Emergency, Refusal, and Routine queries.
5. End-to-end voice-to-answer latency pipeline.
"""

from __future__ import annotations

import os
import sys
import time
import tracemalloc
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.escalation import EscalationEngine
from core.pipeline import FrontlineCompanionPipeline
from core.retrieve import BM25Retriever
from core.speech import validate_transcript


def measure_asset_sizes():
    assets = {
        "Clinical Rules (escalation_rules.json)": PROJECT_ROOT / "data" / "escalation_rules.json",
        "Knowledge Pack Chunks (chunks.json)": PROJECT_ROOT / "data" / "knowledge_pack" / "chunks.json",
        "BM25 Inverted Index (bm25_index.json)": PROJECT_ROOT / "data" / "knowledge_pack" / "bm25_index.json",
        "Pack Manifest (manifest.json)": PROJECT_ROOT / "data" / "knowledge_pack" / "manifest.json",
        "Synthetic Register (households.json)": PROJECT_ROOT / "data" / "synthetic_register" / "households.json",
        "Local SQLite Database (register.db)": PROJECT_ROOT / "data" / "register.db",
        "Frontend Production Bundle (app.js)": PROJECT_ROOT / "web" / "dist" / "app.js",
        "Frontend HTML Shell (index.html)": PROJECT_ROOT / "web" / "dist" / "index.html",
        "PWA Service Worker (sw.js)": PROJECT_ROOT / "web" / "dist" / "sw.js",
    }

    results = {}
    total_bytes = 0
    for name, path in assets.items():
        if path.exists():
            sz = path.stat().st_size
            results[name] = sz
            total_bytes += sz
        else:
            results[name] = None
    return results, total_bytes


def measure_startup_time():
    times_pipeline = []
    times_retriever = []
    times_escalation = []

    for _ in range(15):
        t0 = time.perf_counter()
        _ = EscalationEngine()
        times_escalation.append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        _ = BM25Retriever()
        times_retriever.append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        _ = FrontlineCompanionPipeline()
        times_pipeline.append((time.perf_counter() - t0) * 1000)

    return {
        "escalation_init_ms": round(sum(times_escalation) / len(times_escalation), 3),
        "bm25_init_ms": round(sum(times_retriever) / len(times_retriever), 3),
        "full_pipeline_init_ms": round(sum(times_pipeline) / len(times_pipeline), 3),
    }


def measure_inference_and_memory():
    pipeline = FrontlineCompanionPipeline()

    emergency_queries = [
        "Woman 7 months pregnant has heavy vaginal bleeding",
        "Severe preeclampsia bp 170/115 with blurred vision",
        "Newborn baby chest indrawing fast breathing rr >= 60",
        "Child severe acute malnutrition with bilateral pitting edema",
        "High fever with stiff neck and altered consciousness",
        "Garbhavathi ki fits vachayi sudden ga",
        "Bachhe ko tez bukhar aur gardan akad gayi hai",
    ]

    refusal_queries = [
        "What dose of ciprofloxacin should I prescribe for urinary infection?",
        "Can I give metronidazole to this pregnant patient?",
        "Please diagnose if this is typhoid or malaria",
        "What is the best price for iPhone 16 in Hyderabad?",
    ]

    routine_queries = [
        "What is the schedule for routine ANC checkups during pregnancy?",
        "How to prepare 1 liter of ORS solution for child diarrhea?",
        "When should pentavalent vaccine booster be administered?",
        "What is the normal blood pressure range during antenatal visit?",
        "Pillalaki pentavalent tika eppudu ivvali?",
    ]

    # Measure memory
    tracemalloc.start()
    t0_mem = tracemalloc.get_traced_memory()

    # Latencies
    def benchmark_queries(queries: List[str]):
        latencies = []
        for q in queries:
            for _ in range(10):
                t0 = time.perf_counter()
                _ = pipeline.process_query(q)
                latencies.append((time.perf_counter() - t0) * 1000)
        latencies.sort()
        mean = sum(latencies) / len(latencies)
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]
        max_lat = latencies[-1]
        return {"mean_ms": round(mean, 3), "p50_ms": round(p50, 3), "p95_ms": round(p95, 3), "max_ms": round(max_lat, 3)}

    emg_metrics = benchmark_queries(emergency_queries)
    ref_metrics = benchmark_queries(refusal_queries)
    rou_metrics = benchmark_queries(routine_queries)

    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Measure Voice-to-Answer pipeline (Speech validation + Pipeline execution)
    voice_latencies = []
    for q in emergency_queries + routine_queries:
        for _ in range(10):
            t0 = time.perf_counter()
            val = validate_transcript(q)
            if val.is_understandable:
                _ = pipeline.process_query(val.cleaned_text)
            voice_latencies.append((time.perf_counter() - t0) * 1000)
    voice_latencies.sort()

    voice_metrics = {
        "mean_ms": round(sum(voice_latencies) / len(voice_latencies), 3),
        "p50_ms": round(voice_latencies[len(voice_latencies) // 2], 3),
        "p95_ms": round(voice_latencies[int(len(voice_latencies) * 0.95)], 3),
        "max_ms": round(voice_latencies[-1], 3),
    }

    return {
        "emergency": emg_metrics,
        "refusal": ref_metrics,
        "routine": rou_metrics,
        "voice_to_answer": voice_metrics,
        "peak_ram_kb": round(peak_mem / 1024, 2),
        "current_ram_kb": round(current_mem / 1024, 2),
    }


def main():
    print("=" * 65)
    print("  SYNCPULSE RIGOROUS PERFORMANCE & FOOTPRINT MEASUREMENTS")
    print("=" * 65)

    sizes, total = measure_asset_sizes()
    print("\n1. ASSET FOOTPRINT ON DISK:")
    for name, sz in sizes.items():
        if sz is not None:
            print(f"   - {name:<42}: {sz / 1024:>8.2f} KB ({sz:>9,} bytes)")
        else:
            print(f"   - {name:<42}: NOT FOUND")
    print(f"   --> Total Core Assets: {total / (1024 * 1024):.2f} MB ({total:,} bytes)")

    startup = measure_startup_time()
    print("\n2. COLD STARTUP LATENCY (15-run average):")
    print(f"   - Escalation Engine Init    : {startup['escalation_init_ms']} ms")
    print(f"   - BM25 Retriever Init       : {startup['bm25_init_ms']} ms")
    print(f"   - Full Pipeline Cold Startup: {startup['full_pipeline_init_ms']} ms")

    inf = measure_inference_and_memory()
    print("\n3. INFERENCE LATENCY & MEMORY (CPU Execution):")
    print(f"   - Emergency Safety Gate (Stage 1) : mean={inf['emergency']['mean_ms']} ms | p50={inf['emergency']['p50_ms']} ms | p95={inf['emergency']['p95_ms']} ms")
    print(f"   - Scope / Refusal Gate (Stage 2)  : mean={inf['refusal']['mean_ms']} ms | p50={inf['refusal']['p50_ms']} ms | p95={inf['refusal']['p95_ms']} ms")
    print(f"   - Routine In-Scope Search (Stage 4): mean={inf['routine']['mean_ms']} ms | p50={inf['routine']['p50_ms']} ms | p95={inf['routine']['p95_ms']} ms")
    print(f"   - Voice-to-Answer Pipeline Latency : mean={inf['voice_to_answer']['mean_ms']} ms | p50={inf['voice_to_answer']['p50_ms']} ms | p95={inf['voice_to_answer']['p95_ms']} ms")
    print(f"   - Peak RAM Consumption During Run  : {inf['peak_ram_kb']:.2f} KB ({inf['peak_ram_kb'] / 1024:.2f} MB)")
    print("=" * 65)


if __name__ == "__main__":
    main()
