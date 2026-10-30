# Third-Party Dependencies & Open-Source Licenses
**Talent AP Mega Hackathon 2026 — Problem H5**

In adherence to the minimal dependency principle, the core decision-support engine has **zero external package dependencies** (runs purely on Python standard library modules `re`, `json`, `math`, `sqlite3`, `pathlib`, `dataclasses`).

External dependencies are restricted to the local API server, testing, and benchmarking:

---

## 1. Runtime Dependencies

| Package | Version | License | Justification & Architectural Role |
|---|---|---|---|
| **fastapi** | `^0.115.0` | MIT License | Provides a thin, high-performance REST API layer over the core engine for `/api/ask`, `/api/visits`, and `/api/sync`. |
| **uvicorn** | `^0.34.0` | BSD-3-Clause | Lightweight ASGI web server for local on-device hosting of FastAPI and static PWA assets. |
| **pydantic** | `^2.10.0` | MIT License | Strict request/response payload schema validation for frontline API endpoints. |

---

## 2. Testing & Benchmark Dependencies

| Package | Version | License | Justification & Architectural Role |
|---|---|---|---|
| **psutil** | `^7.0.0` | BSD-3-Clause | Required by `bench/benchmark.py` and `bench/scale_test.py` to measure real OS process RSS RAM, heap allocation, and peak footprint honestly. |
| **pytest** | `^9.1.0` | MIT License | Automated unit and integration testing framework across 36 tests. |
| **httpx** | `^0.28.0` | BSD-3-Clause | Used by `TestClient` in `tests/test_server.py` for headless API verification. |

---

## 3. Node.js & Web Assets

| Package / Tool | Version | License | Justification & Architectural Role |
|---|---|---|---|
| **Node.js runtime** | `v26.5.1` | MIT License | Used during development to run the TypeScript parity test (`node --experimental-strip-types`). **NOT required at runtime for the demo**, as `web/dist` is pre-built and served directly by Python. |
| **PWA Service Worker** | Standard Web API | W3C / WHATWG | Enables browser asset caching and zero-network execution on mobile devices. |

---

## 4. Why Heavier Libraries Were Excluded

- **No PyTorch / Transformers / HuggingFace:** Avoided 500 MB – 2 GB binary overhead. Our BM25 and deterministic rule engine fits in **188 KB** and executes in **< 1 ms** on any low-end CPU.
- **No MongoDB / Firebase / PostgreSQL:** Frontline rural health work requires on-device zero-dependency databases; local **SQLite** and **IndexedDB** are built-in and require no cloud setup.
- **No LangChain / LlamaIndex:** Full transparency: pipeline stages are written in plain, readable Python and TypeScript so students can explain every line.
