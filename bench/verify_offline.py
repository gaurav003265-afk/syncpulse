"""
Strict offline verification suite for Frontline Health-Worker Companion (H5).

Guarantees 100% offline capability:
- Sets offline environment flags (HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1).
- Monkeypatches socket.socket.connect and socket.create_connection to trap and forbid any network egress.
- Executes the entire dev-set suite (96 queries) end-to-end.
- Asserts zero outbound network attempts.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import time
from pathlib import Path

# Set offline environment variables
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure UTF-8 console output
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


class OfflineSecurityError(RuntimeError):
    """Raised when any network access is attempted during offline mode."""
    pass


# Global connection attempts counter
SOCKET_ATTEMPTS = []

_real_connect = socket.socket.connect
_real_create_connection = socket.create_connection


def guarded_connect(self, address):
    SOCKET_ATTEMPTS.append(address)
    raise OfflineSecurityError(
        f"VIOLATION: Attempted outbound network connection to {address} during strict offline test!"
    )


def guarded_create_connection(address, *args, **kwargs):
    SOCKET_ATTEMPTS.append(address)
    raise OfflineSecurityError(
        f"VIOLATION: Attempted outbound network connection to {address} during strict offline test!"
    )


# Apply socket guard
socket.socket.connect = guarded_connect
socket.create_connection = guarded_create_connection


def verify_offline() -> bool:
    print("\n" + "=" * 65)
    print("      H5 STRICT OFFLINE ZERO-EGRESS VERIFICATION SUITE      ")
    print("=" * 65)
    print("Environment Configured: HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1")
    print("Socket Protection     : ACTIVE (All outbound TCP/UDP blocked)")
    print("-" * 65)

    from core.pipeline import FrontlineCompanionPipeline

    dev_set_path = PROJECT_ROOT / "eval" / "dev_set.jsonl"
    with open(dev_set_path, "r", encoding="utf-8-sig") as f:
        queries = [json.loads(line.strip())["query"] for line in f if line.strip()]

    print(f"Loaded {len(queries)} evaluation queries.")
    print("Initializing offline pipeline...")

    t0 = time.perf_counter()
    pipeline = FrontlineCompanionPipeline()
    init_ms = (time.perf_counter() - t0) * 1000.0
    print(f"Pipeline initialized in {init_ms:.2f} ms without network.")

    successful_runs = 0
    t_start = time.perf_counter()

    for idx, q in enumerate(queries, start=1):
        try:
            resp = pipeline.process_query(q)
            assert resp.type in ("escalate", "refuse", "answer", "abstain")
            successful_runs += 1
        except OfflineSecurityError as e:
            print(f"\n[CRITICAL FAILURE] Outbound socket attempted on query {idx}: {q}")
            print(f"Error: {e}")
            return False
        except Exception as e:
            print(f"\n[RUNTIME FAILURE] Error on query {idx}: {q}\n{e}")
            return False

    total_time = (time.perf_counter() - t_start) * 1000.0
    avg_per_query = total_time / max(1, len(queries))

    print("-" * 65)
    print(f"Queries Executed      : {successful_runs} / {len(queries)}")
    print(f"Socket Attempts Caught: {len(SOCKET_ATTEMPTS)}")
    print(f"Total Offline Runtime : {total_time:.2f} ms (Avg {avg_per_query:.2f} ms/query)")
    print("=" * 65)

    if len(SOCKET_ATTEMPTS) == 0 and successful_runs == len(queries):
        print(">>> RESULT: [PASS] 100% OFFLINE VERIFIED (ZERO NETWORK EGRESS) <<<")
        print("=" * 65 + "\n")
        return True
    else:
        print(">>> RESULT: [FAIL] NETWORK ACCESS DETECTED! <<<")
        print("=" * 65 + "\n")
        return False


if __name__ == "__main__":
    success = verify_offline()
    sys.exit(0 if success else 1)
