# Canonical 100 m EPSG:5070 grid pipeline scaffold

GRID_SPEC := grid.json
RAW_DIR := raw
PROCESSED_DIR := processed
SCRIPTS_DIR := scripts

PYTHON ?= python3

# Elevation-specific paths
DEM_RAW_DIR := $(RAW_DIR)/dem
DEM_OUTPUT := $(PROCESSED_DIR)/dem_100m_cog.tif

.PHONY: all download-dem dem warp-dem validate-dem metadata clean

all: dem

# --- Elevation pipeline targets ------------------------------------------------

# Download raw elevation sources to raw/dem/
download-dem:
	@mkdir -p $(DEM_RAW_DIR)
		@$(PYTHON) $(SCRIPTS_DIR)/download_dem.py \
			--grid $(GRID_SPEC) \
			--raw-dir $(RAW_DIR) \
			--manifest manifest.csv \
			$(if $(DRY_RUN),--dry-run,) \
			$(if $(WORKERS),--workers $(WORKERS),)

# Generate the aligned 100 m DEM (mosaic + warp + COG conversion).
dem: $(DEM_OUTPUT)

$(DEM_OUTPUT): $(GRID_SPEC) $(SCRIPTS_DIR)/process_elevation.py
	@mkdir -p $(PROCESSED_DIR)
	@$(PYTHON) $(SCRIPTS_DIR)/process_elevation.py \
		--grid $(GRID_SPEC) \
		--raw-dir $(DEM_RAW_DIR) \
		--output $@ \
		--manifest manifest.csv

# Optional validation / QA hooks.
warp-dem: dem
	@echo "Elevation warp complete -> $(DEM_OUTPUT)"

validate-dem: dem
	@echo "TODO: run grid alignment + stats checks (e.g. python scripts/validate_grid.py)"

metadata: dem
	@echo "TODO: export GDAL metadata and update manifest.csv"

clean:
	rm -f $(DEM_OUTPUT)
