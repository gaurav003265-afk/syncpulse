"""
Quick command-line interface for Frontline Health-Worker Companion (H5).

Usage:
  # 1. Ask a question directly:
  python ask.py "woman in 8th month pregnancy has bleeding"

  # 2. Start interactive session:
  python ask.py

  # 3. Test code-mixed Telugu or Hindi:
  python ask.py "garbhavathi ki raktham vasthondi"
  python ask.py "bacha doodh nahi pee raha"
"""

import sys
import time
from pathlib import Path

# Ensure UTF-8 console output for Windows PowerShell / CMD
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core.pipeline import FrontlineCompanionPipeline


def display_result(query: str, pipeline: FrontlineCompanionPipeline):
    print("\n" + "=" * 65)
    print(f"QUERY: {query}")
    print("-" * 65)

    resp = pipeline.process_query(query)

    if resp.type == "escalate":
        print(resp.text)
    elif resp.type == "refuse":
        print("⚠️ [OUTSIDE FRONTLINE PROTOCOL SCOPE — REFUSAL]")
        print(f"Guidance: {resp.text}")
    elif resp.type == "answer":
        print("📖 [PROTOCOL-GROUNDED GUIDANCE]")
        print(resp.text)
        print(f"Confidence : {resp.confidence * 100:.1f}%")
    elif resp.type == "abstain":
        print("ℹ️ [ABSTENTION: INFORMATION NOT IN PROTOCOL]")
        print(resp.text)

    print(f"Latency    : {resp.latency_ms:.2f} ms (CPU proxy)")
    print("=" * 65 + "\n")


def main():
    pipeline = FrontlineCompanionPipeline()

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        display_result(query, pipeline)
    else:
        print("\n" + "=" * 65)
        print("🏥 Frontline Health-Worker Companion (H5) — Interactive CLI")
        print("Type a query in English, Telugu, Hindi, or Code-Mixed text.")
        print("Type 'exit' or 'quit' to stop.")
        print("=" * 65)

        sample_prompts = [
            "1. 7th month pregnant lady has bleeding from vagina",
            "2. Garbhavathi ki raktham vasthondi sudden ga",
            "3. Newborn baby has respiratory rate 65 per minute",
            "4. 2 year old child has bilateral pitting edema in both feet",
            "5. Patient ka BP 190 by 115 pahunch gaya hai",
            "6. How many minimum ANC visits should a pregnant woman have?",
        ]
        print("\nTry queries like:")
        for sp in sample_prompts:
            print(f"  {sp}")
        print()

        while True:
            try:
                user_input = input("Enter query > ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ("exit", "quit", "q"):
                    print("Exiting. Stay safe!")
                    break
                display_result(user_input, engine)
            except (KeyboardInterrupt, EOFError):
                print("\nExiting.")
                break


if __name__ == "__main__":
    main()
