import os
import subprocess
from typing import Dict

RESULTS_DIR = "../../tests/data/results_json"
COMPARE_SCRIPT = "../../tests/compare_scan_results.py"

# Iterate through each subdirectory
for method in os.listdir(RESULTS_DIR):
    method_path = os.path.join(RESULTS_DIR, method)
    if not os.path.isdir(method_path):
        continue

    # Collect all file pairs
    file_pairs: Dict[str, Dict[str, str]] = {}
    for filename in os.listdir(method_path):
        if filename.endswith(".json"):
            base_name = filename.replace(".new.json", "").replace(".json", "")
            if base_name not in file_pairs:
                file_pairs[base_name] = {}
            if filename.endswith(".new.json"):
                file_pairs[base_name]["actual"] = os.path.join(method_path, filename)
            else:
                file_pairs[base_name]["expected"] = os.path.join(method_path, filename)

    # Run the comparison command on each file pair
    for base_name, files in file_pairs.items():
        if "actual" in files and "expected" in files:
            command = [
                "python",
                COMPARE_SCRIPT,
                "--actual",
                files["actual"],
                "--expected",
                files["expected"],
                "--assert",
            ]
            print(f"\n\nRunning: {' '.join(command)}")
            subprocess.check_call(command)
