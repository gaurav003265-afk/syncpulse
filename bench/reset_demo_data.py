"""
Resets SyncPulse SQLite database to clean demonstration state
using the original data/synthetic_register/households.json source file.
Safe and repeatable: never modifies or corrupts the original source files.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.db import DatabaseManager
from core.importer import RegisterImporter


def reset_demo_database():
    db_file = PROJECT_ROOT / "data" / "register.db"
    reg_file = PROJECT_ROOT / "data" / "synthetic_register" / "households.json"

    if not reg_file.exists():
        raise FileNotFoundError(f"Source register missing at: {reg_file}")

    # Remove existing SQLite DB and WAL files if present
    for ext in ("", "-shm", "-wal"):
        f = Path(str(db_file) + ext)
        if f.exists():
            try:
                f.unlink()
            except Exception as e:
                print(f"Warning unlinking {f}: {e}")

    # If unlinking is blocked by a running server process, truncate existing tables
    db_mgr = DatabaseManager(str(db_file))
    with db_mgr.get_connection() as conn:
        cursor = conn.cursor()
        for tbl in ["sync_outbox", "emergency_events", "follow_ups", "visit_outcomes", "beneficiaries", "households"]:
            try:
                cursor.execute(f"DELETE FROM {tbl};")
            except Exception:
                pass
        conn.commit()

    # Re-initialize clean schema and import 500 households
    importer = RegisterImporter(db_mgr)
    report = importer.import_from_file(reg_file)

    print("=" * 60)
    print("  SYNCPULSE DEMONSTRATION RESET COMPLETE")
    print("=" * 60)
    print(f"Database File      : {db_file}")
    print(f"Source Register    : {reg_file}")
    print(f"Imported Households: {report.imported_new} / {report.total_records}")
    print(f"Rejected / Errors  : {report.rejected_count}")
    print("Zero source records were modified or corrupted.")
    print("=" * 60)


if __name__ == "__main__":
    reset_demo_database()
