"""Tiny helper that runs raster sampling inside the GDAL container."""

from __future__ import annotations

import subprocess
from pathlib import Path

# Edit these values as you iterate.
RASTER_RELATIVE_PATH = Path("data/dem_100m_cog.tif")
BASE_LON_MIN = -125.0
BASE_LAT_MIN = 24.0
BASE_LON_MAX = -66.0
BASE_LAT_MAX = 49.0
SHRINK_PERCENT = 0.05
SHRINK_SCHEDULE = "0.2:5,0.1:5,0.05:10,0.03:*"
STEPS = 1000
MIN_OVERVIEW_INDEX = 2
DROP_MIN_OVERVIEW_EVERY = 2
INCLUDE_BASE_AFTER = 20  # step index (0-based) to begin sampling the raw band; set to None to disable
PLOT_DIR = Path("benchmark_plots")


def main() -> None:
    raster_in_container = Path("/workspace") / RASTER_RELATIVE_PATH
    cmd = [
        "docker",
        "compose",
        "run",
        "--rm",
        "gdal",
        "python",
        "dynamic_res_test.py",
        raster_in_container.as_posix(),
        "--lon-min",
        str(BASE_LON_MIN),
        "--lat-min",
        str(BASE_LAT_MIN),
        "--lon-max",
        str(BASE_LON_MAX),
        "--lat-max",
        str(BASE_LAT_MAX),
        "--steps",
        str(STEPS),
        "--shrink-percent",
        str(SHRINK_PERCENT),
        "--shrink-schedule",
        SHRINK_SCHEDULE,
        "--payload-cap-mb",
        "5",
        "--plot-dir",
        (Path("/workspace") / PLOT_DIR).as_posix(),
        "--include-base-after",
        str(INCLUDE_BASE_AFTER if INCLUDE_BASE_AFTER is not None else -1),
    ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
