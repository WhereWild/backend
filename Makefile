# Canonical 100 m EPSG:5070 grid pipeline scaffold

GRID_SPEC := grid.json
RAW_DIR := raw
PROCESSED_DIR := processed
SCRIPTS_DIR := scripts

PYTHON ?= $(if $(wildcard venv/bin/python),venv/bin/python,python3)

# Elevation-specific paths
DEM_RAW_DIR := $(RAW_DIR)/dem
DEM_OUTPUT := $(PROCESSED_DIR)/dem_100m_cog.tif
TERRAIN_STACK := $(PROCESSED_DIR)/terrain/terrain_stack.tif
LANDCOVER_RAW_DIR := $(RAW_DIR)/landcover
LANDCOVER_RAW_TIF := $(LANDCOVER_RAW_DIR)/nlcd_2019_land_cover_l48_20210604.tif
LANDCOVER_OUTPUT := $(PROCESSED_DIR)/landcover/landcover_100m_cog.tif
FEATURES_DIR := $(PROCESSED_DIR)/features

.PHONY: all download-dem download-observations download-landcover dem terrain landcover regions plots features species warp-dem validate-dem metadata clean

all: dem terrain landcover

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

download-landcover:
	@mkdir -p $(LANDCOVER_RAW_DIR)
	@$(PYTHON) $(SCRIPTS_DIR)/download_landcover.py \
		--raw-dir $(RAW_DIR) \
		--manifest manifest.csv \
		$(if $(LANDCOVER_URL),--url $(LANDCOVER_URL),) \
		$(if $(LANDCOVER_OVERWRITE),--overwrite,) \
		$(if $(DRY_RUN),--dry-run,)

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

landcover: $(LANDCOVER_OUTPUT)

$(LANDCOVER_RAW_TIF): $(SCRIPTS_DIR)/download_landcover.py
	@$(MAKE) download-landcover

$(LANDCOVER_OUTPUT): $(GRID_SPEC) $(LANDCOVER_RAW_TIF) $(SCRIPTS_DIR)/process_landcover.py
	@mkdir -p $(PROCESSED_DIR)/landcover
	@$(PYTHON) $(SCRIPTS_DIR)/process_landcover.py \
		--grid $(GRID_SPEC) \
		--source $(LANDCOVER_RAW_TIF) \
		--output $@ \
		--manifest manifest.csv

regions: $(TERRAIN_STACK)
	@$(PYTHON) $(SCRIPTS_DIR)/build_regions.py --config regions.json

plots: regions
	@$(PYTHON) $(SCRIPTS_DIR)/plot_quicklooks.py

features: regions landcover
	@mkdir -p $(FEATURES_DIR)
	@$(PYTHON) $(SCRIPTS_DIR)/build_feature_table.py \
		--processed-root $(PROCESSED_DIR) \
		--config regions.json \
		--output-dir $(FEATURES_DIR) \
		--manifest manifest.csv
	@$(PYTHON) $(SCRIPTS_DIR)/build_feature_table.py \
		--processed-root $(PROCESSED_DIR) \
		--config regions.json \
		--output-dir $(FEATURES_DIR) \
		--manifest manifest.csv \
		--include-conus

species:
	@$(PYTHON) $(SCRIPTS_DIR)/run_species_pipeline.py $(if $(slug),--slug $(slug),) $(EXTRA)

# Optional validation / QA hooks.
warp-dem: dem
	@echo "Elevation warp complete -> $(DEM_OUTPUT)"

validate-dem: dem
	@echo "TODO: run grid alignment + stats checks (e.g. python scripts/validate_grid.py)"

metadata: dem
	@echo "TODO: export GDAL metadata and update manifest.csv"

clean:
	rm -f $(DEM_OUTPUT) $(LANDCOVER_OUTPUT)
