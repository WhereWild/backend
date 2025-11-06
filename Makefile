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
SOIL_TEXTURE_RAW_DIR := $(RAW_DIR)/soil_texture
SOIL_TEXTURE_SAND := $(SOIL_TEXTURE_RAW_DIR)/sand.tif
SOIL_TEXTURE_SILT := $(SOIL_TEXTURE_RAW_DIR)/silt.tif
SOIL_TEXTURE_CLAY := $(SOIL_TEXTURE_RAW_DIR)/clay.tif
SOIL_TEXTURE_OUTPUT := $(PROCESSED_DIR)/soil_texture/soil_texture_100m_cog.tif
SOIL_PROPERTY_NAMES := cfvo phh2o nitrogen soc
SOIL_PROPERTY_OUTPUTS := $(addprefix $(PROCESSED_DIR)/soil/,$(addsuffix _100m.tif,$(SOIL_PROPERTY_NAMES)))
SOIL_PROPERTY_RAW_FILES := $(addprefix $(SOIL_TEXTURE_RAW_DIR)/,$(addsuffix .tif,$(SOIL_PROPERTY_NAMES)))
FEATURES_DIR := $(PROCESSED_DIR)/features

.PHONY: all download-dem download-observations download-landcover dem terrain landcover soil-texture soil-properties regions plots features species predict warp-dem validate-dem metadata clean
.PHONY: predict-heatmap-region predict-heatmap-conus

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

soil-texture: $(SOIL_TEXTURE_OUTPUT)

$(SOIL_TEXTURE_OUTPUT): $(GRID_SPEC) $(SCRIPTS_DIR)/process_soil_texture.py $(SOIL_TEXTURE_SAND) $(SOIL_TEXTURE_SILT) $(SOIL_TEXTURE_CLAY)
	@mkdir -p $(PROCESSED_DIR)/soil_texture
	@$(PYTHON) $(SCRIPTS_DIR)/process_soil_texture.py \
		--grid $(GRID_SPEC) \
		--sand $(SOIL_TEXTURE_SAND) \
		--silt $(SOIL_TEXTURE_SILT) \
		--clay $(SOIL_TEXTURE_CLAY) \
		--output $@ \
		--manifest manifest.csv

soil-properties: $(SOIL_PROPERTY_OUTPUTS)

$(PROCESSED_DIR)/soil/%_100m.tif: $(GRID_SPEC) $(SCRIPTS_DIR)/process_soil_properties.py $(SOIL_TEXTURE_RAW_DIR)/%.tif
	@mkdir -p $(PROCESSED_DIR)/soil
	@$(PYTHON) $(SCRIPTS_DIR)/process_soil_properties.py \
		--grid $(GRID_SPEC) \
		--properties $* \
		--manifest manifest.csv

regions: $(TERRAIN_STACK)
	@$(PYTHON) $(SCRIPTS_DIR)/build_regions.py --config regions.json

plots: regions
	@$(PYTHON) $(SCRIPTS_DIR)/plot_quicklooks.py

features: regions landcover soil-properties
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

predict:
	@if [ -z "$(FEATURES)" ] || [ -z "$(BACKGROUND)" ] || [ -z "$(OUT)" ]; then \
		echo "Usage: make predict FEATURES=path/to/species_features.csv.gz BACKGROUND=processed/features/<region>.parquet OUT=models [slug=<name>] [sample=<n>]"; \
		exit 1; \
	fi
	@$(PYTHON) $(SCRIPTS_DIR)/model_species_presence.py \
		--features $(FEATURES) \
		--background $(BACKGROUND) \
		--output-dir $(OUT) \
		$(if $(slug),--species $(slug),) \
		$(if $(sample),--background-sample $(sample),) \
		$(PREDICT_EXTRA)

predict-heatmap-region:
	@if [ -z "$(MODEL_DIR)" ]; then \
		echo "Usage: make predict-heatmap-region MODEL_DIR=models/<slug> [TITLE='My Title'] [OUT=figures/predictions/<slug>_region.png]"; \
		exit 1; \
	fi
	@$(PYTHON) $(SCRIPTS_DIR)/plot_prediction_heatmap.py \
		--predictions $(MODEL_DIR)/predictions.parquet \
		--grid $(GRID_SPEC) \
		--output $(if $(OUT),$(OUT),figures/predictions/$(notdir $(MODEL_DIR))_region.png) \
		--crop \
		--stride 1 \
		$(if $(TITLE),--title "$(TITLE)",)

predict-heatmap-conus:
	@if [ -z "$(MODEL_DIR)" ]; then \
		echo "Usage: make predict-heatmap-conus MODEL_DIR=models/<slug> [TITLE='My Title'] [OUT=figures/predictions/<slug>_conus.png] [STRIDE=5]"; \
		exit 1; \
	fi
	@$(PYTHON) $(SCRIPTS_DIR)/plot_prediction_heatmap.py \
		--predictions $(MODEL_DIR)/predictions.parquet \
		--grid $(GRID_SPEC) \
		--output $(if $(OUT),$(OUT),figures/predictions/$(notdir $(MODEL_DIR))_conus.png) \
		--stride $(if $(STRIDE),$(STRIDE),5) \
		$(if $(TITLE),--title "$(TITLE)",)

# Optional validation / QA hooks.
warp-dem: dem
	@echo "Elevation warp complete -> $(DEM_OUTPUT)"

validate-dem: dem
	@echo "TODO: run grid alignment + stats checks (e.g. python scripts/validate_grid.py)"

metadata: dem
	@echo "TODO: export GDAL metadata and update manifest.csv"

clean:
	rm -f $(DEM_OUTPUT) $(LANDCOVER_OUTPUT)
