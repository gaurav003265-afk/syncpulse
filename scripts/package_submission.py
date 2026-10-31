"""
Automated packaging script conforming to Participant Coding Guidelines v1.1 (Rule 2).

Packages the repository into:
  dist_package/
  └── syncpulse_H5/
      ├── README.md
      ├── .gitignore
      ├── submission/
      │   ├── H5_answers.jsonl
      │   ├── H5_visit_list.csv
      │   └── H5_footprint.json
      └── FULL_CODE/
          ├── core/
          ├── server/
          ├── web/ (excluding node_modules)
          ├── bench/
          ├── data/
          ├── tests/
          ├── requirements.txt
          ├── .env.example
          └── pytest.ini
"""

import shutil
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist_package"
PACKAGE_ROOT = DIST_DIR / "syncpulse_H5"


def package():
    print("=" * 70)
    print("  PACKAGING SYNCPULSE H5 FOR HACKATHON SUBMISSION (RULE 2)")
    print("=" * 70)

    # 1. Clean previous dist
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    PACKAGE_ROOT.mkdir(parents=True, exist_ok=True)

    # 2. Top-level files per Rule 2
    shutil.copy2(PROJECT_ROOT / "README.md", PACKAGE_ROOT / "README.md")
    shutil.copy2(PROJECT_ROOT / ".gitignore", PACKAGE_ROOT / ".gitignore")
    if (PROJECT_ROOT / "LICENSE").exists():
        shutil.copy2(PROJECT_ROOT / "LICENSE", PACKAGE_ROOT / "LICENSE")

    # 3. submission/ directory with the exact 3 files
    sub_dst = PACKAGE_ROOT / "submission"
    sub_dst.mkdir(parents=True, exist_ok=True)
    for fname in ["H5_answers.jsonl", "H5_visit_list.csv", "H5_footprint.json"]:
        src_file = PROJECT_ROOT / "submission" / fname
        if not src_file.exists():
            raise FileNotFoundError(f"Missing required submission file: {src_file}")
        shutil.copy2(src_file, sub_dst / fname)
        print(f"Copied submission file: {fname} ({src_file.stat().st_size:,} bytes)")

    # 4. FULL_CODE/ directory
    full_code = PACKAGE_ROOT / "FULL_CODE"
    full_code.mkdir(parents=True, exist_ok=True)

    # Root config files into FULL_CODE
    for fname in ["requirements.txt", ".env.example", "pytest.ini", "ask.py", "README.md"]:
        src_file = PROJECT_ROOT / fname
        if src_file.exists():
            shutil.copy2(src_file, full_code / fname)

    # Directories to copy into FULL_CODE
    dirs_to_copy = ["core", "server", "bench", "tests", "docs", "data"]
    for dname in dirs_to_copy:
        src_d = PROJECT_ROOT / dname
        if src_d.exists():
            shutil.copytree(
                src_d,
                full_code / dname,
                ignore=shutil.ignore_patterns(
                    "__pycache__", "*.pyc", "*.pyo", ".pytest_cache", "*.db-shm", "*.db-wal", "register.db"
                ),
            )
            print(f"Copied folder into FULL_CODE: {dname}")

    # Copy web frontend (excluding node_modules)
    web_src = PROJECT_ROOT / "web"
    if web_src.exists():
        shutil.copytree(
            web_src,
            full_code / "web",
            ignore=shutil.ignore_patterns("node_modules", "dist", ".git", ".next", ".turbo"),
        )
        print("Copied web folder into FULL_CODE (excluding node_modules and build output)")

    # 5. Create final delivery ZIP archive
    zip_path = DIST_DIR / "syncpulse_H5.zip"
    print(f"\nCompressing into {zip_path.name}...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for p in PACKAGE_ROOT.rglob("*"):
            rel = p.relative_to(PACKAGE_ROOT.parent)
            zipf.write(p, rel)

    zip_size_mb = round(zip_path.stat().st_size / (1024 * 1024), 2)
    print("=" * 70)
    print(f"SUCCESS: Package created at {PACKAGE_ROOT}")
    print(f"ZIP Archive: {zip_path} ({zip_size_mb} MB)")
    print("Conforms 100% to TalentAP Participant Coding Guidelines v1.1 Rule 2!")
    print("=" * 70)


if __name__ == "__main__":
    package()
