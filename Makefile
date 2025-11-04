# Canonical 100 m EPSG:5070 grid pipeline scaffold

GRID_SPEC := grid.json
RAW_DIR := raw
PROCESSED_DIR := processed
SCRIPTS_DIR := scripts

PYTHON ?= python3

# Elevation-specific paths
DEM_RAW_DIR := $(RAW_DIR)/dem
DEM_OUTPUT := $(PROCESSED_DIR)/dem_100m_cog.tif
TERRAIN_STACK := $(PROCESSED_DIR)/terrain/terrain_stack.tif

.PHONY: all download-dem download-observations dem terrain regions plots warp-dem validate-dem metadata clean

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

download-observations:
	@if [ -z "$(OBS_SPECIES)" ] || [ -z "$(OBS_SPECIES_ID)" ]; then \
		echo "Set OBS_SPECIES (slug, e.g. escobaria_vivipara) and OBS_SPECIES_ID before running."; \
		exit 1; \
	fi
	@$(PYTHON) $(SCRIPTS_DIR)/download_observations.py \
		--species-id $(OBS_SPECIES_ID) \
		--species-slug $(OBS_SPECIES) \
		$(if $(OBS_QUALITY_GRADE),--quality-grade $(OBS_QUALITY_GRADE),) \
		$(if $(OBS_PER_PAGE),--per-page $(OBS_PER_PAGE),) \
		$(if $(OBS_MAX_RECORDS),--max-records $(OBS_MAX_RECORDS),) \
		$(if $(OBS_START_DATE),--start-date $(OBS_START_DATE),) \
		$(if $(OBS_END_DATE),--end-date $(OBS_END_DATE),) \
		$(if $(OBS_PLACE_ID),--place-id $(OBS_PLACE_ID),) \
		$(if $(OBS_PROJECT_ID),--project-id $(OBS_PROJECT_ID),) \
		$(if $(OBS_USER_ID),--user-id $(OBS_USER_ID),) \
		$(if $(OBS_MEDIA),--media $(OBS_MEDIA),) \
		$(if $(OBS_BBOX),--bbox $(OBS_BBOX),) \
		$(if $(OBS_SLEEP),--sleep $(OBS_SLEEP),) \
		$(if $(OBS_DRY_RUN),--dry-run,)

# Generate the aligned 100 m DEM (mosaic + warp + COG conversion).
dem: $(DEM_OUTPUT)

$(DEM_OUTPUT): $(GRID_SPEC) $(SCRIPTS_DIR)/process_elevation.py
	@mkdir -p $(PROCESSED_DIR)
	@$(PYTHON) $(SCRIPTS_DIR)/process_elevation.py \
		--grid $(GRID_SPEC) \
		--raw-dir $(DEM_RAW_DIR) \
		--output $@ \
		--manifest manifest.csv

terrain: $(TERRAIN_STACK)

$(TERRAIN_STACK): $(DEM_OUTPUT) $(SCRIPTS_DIR)/derive_terrain.py
	@mkdir -p $(PROCESSED_DIR)/terrain
	@$(PYTHON) $(SCRIPTS_DIR)/derive_terrain.py \
		--dem $(DEM_OUTPUT) \
		--grid $(GRID_SPEC) \
		--output-dir $(PROCESSED_DIR)/terrain \
		--manifest manifest.csv

regions: $(TERRAIN_STACK)
	@$(PYTHON) $(SCRIPTS_DIR)/build_regions.py --config regions.json

plots: regions
	@$(PYTHON) $(SCRIPTS_DIR)/plot_quicklooks.py

# Optional validation / QA hooks.
warp-dem: dem
	@echo "Elevation warp complete -> $(DEM_OUTPUT)"

validate-dem: dem
	@echo "TODO: run grid alignment + stats checks (e.g. python scripts/validate_grid.py)"

metadata: dem
	@echo "TODO: export GDAL metadata and update manifest.csv"

clean:
	rm -f $(DEM_OUTPUT)
