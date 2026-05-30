from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from micro_fulfillment_network_jakarta.logger import get_logger


PIPELINE_SCRIPTS = [
    "01_setup_gee_auth.py",
    "02_bootstrap_folders.py",
    "03_download_aoi.py",
    "04_fetch_worldpop.py",
    "05_fetch_viirs.py",
    "06_fetch_dynamic_world.py",
    "07_fetch_osm_network.py",
    "08_build_raw_manifest.py",
    "09_build_demand_index.py",
    "10_optimize_mfc_network.py",
    "11_compute_emission_scenarios.py",
    "12_spatial_autocorrelation.py",
    "13_clustering_analysis.py",
    "14_temporal_trend.py",
    "15_validation_crosscheck.py",
    "16_generate_static_maps.py",
    "17_generate_charts.py",
    "18_generate_interactive_maps.py",
    "19_build_reports.py",
    "20_generate_public_brief.py",
]


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run the full Greater Jakarta micro-fulfillment pipeline.")
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue running remaining scripts even if one script fails.",
    )
    parser.add_argument(
        "--skip-gee-auth",
        action="store_true",
        help="Skip script 01 GEE authentication validation.",
    )
    parser.add_argument(
        "--start-at",
        type=str,
        default=None,
        help="Start pipeline at a specific script filename, for example 09_build_demand_index.py.",
    )
    return parser.parse_args()


def run_script(script_path: Path) -> int:
    """Run one Python script as a subprocess."""
    command = [sys.executable, str(script_path)]
    result = subprocess.run(command, cwd=str(PROJECT_ROOT), text=True)
    return int(result.returncode)


def main() -> None:
    """Run all pipeline scripts in order."""
    args = parse_args()
    logger = get_logger("21_run_pipeline")

    scripts = PIPELINE_SCRIPTS.copy()

    if args.skip_gee_auth:
        scripts = [script for script in scripts if script != "01_setup_gee_auth.py"]

    if args.start_at:
        if args.start_at not in scripts:
            raise ValueError(f"Unknown start script: {args.start_at}")
        start_index = scripts.index(args.start_at)
        scripts = scripts[start_index:]

    logger.info("Starting full reproducible pipeline.")
    logger.info(f"Project root: {PROJECT_ROOT}")
    logger.info(f"Continue on error: {args.continue_on_error}")

    failed: list[str] = []
    started = time.time()

    for script_name in scripts:
        script_path = PROJECT_ROOT / "scripts" / script_name

        if not script_path.exists():
            message = f"Pipeline script not found: {script_path}"
            logger.error(message)
            failed.append(script_name)
            if not args.continue_on_error:
                raise FileNotFoundError(message)
            continue

        logger.info(f"Running pipeline step: {script_name}")
        step_started = time.time()
        return_code = run_script(script_path)
        elapsed = time.time() - step_started

        if return_code == 0:
            logger.info(f"Completed {script_name} in {elapsed:.1f} seconds.")
        else:
            logger.error(f"Failed {script_name} with return code {return_code} after {elapsed:.1f} seconds.")
            failed.append(script_name)
            if not args.continue_on_error:
                raise RuntimeError(f"Pipeline stopped at {script_name}")

    total_elapsed = time.time() - started

    if failed:
        logger.error(f"Pipeline completed with failures: {failed}")
        print("Pipeline completed with failures:")
        for item in failed:`
            print(f"* {item}")
        sys.exit(1)

    logger.info(f"Pipeline completed successfully in {total_elapsed:.1f} seconds.")
    print(f"Pipeline completed successfully in {total_elapsed:.1f} seconds.")


if __name__ == "__main__":
    main()