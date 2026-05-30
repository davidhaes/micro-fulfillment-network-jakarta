from __future__ import annotations

import runpy
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from micro_fulfillment_network_jakarta.logger import get_logger


def main() -> None:
    """Run the reproducible AOI generator."""
    logger = get_logger("03_download_aoi")
    script_path = PROJECT_ROOT / "AOI" / "download_aoi.py"

    if not script_path.exists():
        raise FileNotFoundError(f"AOI generator not found: {script_path}")

    logger.info(f"Executing AOI generator: {script_path}")
    runpy.run_path(str(script_path), run_name="__main__")
    logger.info("AOI generator completed.")


if __name__ == "__main__":
    main()
