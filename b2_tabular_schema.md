# B2 Tabular Schema Sample

- Generated UTC: 2026-02-16T12:35:12.688983+00:00
- Remote: `wherewild-localdev-reader:wherewild-data`
- Candidates considered: 20
- Profiles generated: 13
- Skipped files: 1
- Failed files: 6

## Profiled Files

### File 1

- Path:

  ```text
  data/gis/catalog.json
  ```

- Status: `failed`
- Extension: `json`
- Size bytes: 8,449
- Error: unhashable type: 'list'

### File 2

- Path:

  ```text
  data/gis/legends/aspect_legend.json
  ```

- Status: `failed`
- Extension: `json`
- Size bytes: 576
- Error: unhashable type: 'list'

### File 3

- Path:

  ```text
  data/gis/legends/koppen_geiger_legend.json
  ```

- Status: `failed`
- Extension: `json`
- Size bytes: 5,652
- Error: unhashable type: 'list'

### File 4

- Path:

  ```text
  data/gis/legends/landcover_legend.json
  ```

- Status: `failed`
- Extension: `json`
- Size bytes: 4,442
- Error: unhashable type: 'list'

### File 5

- Path:

  ```text
  data/gis/legends/weather_code_simple_avg_1h_legend.json
  ```

- Status: `failed`
- Extension: `json`
- Size bytes: 2,710
- Error: unhashable type: 'list'

### File 6

- Path:

  ```text
  data/gis/legends/weather_code_simple_legend.json
  ```

- Status: `failed`
- Extension: `json`
- Size bytes: 2,710
- Error: unhashable type: 'list'

### File 7

- Path:

  ```text
  data/gis/locations/gbif_regions.csv
  ```

- Status: `profiled`
- Extension: `csv`
- Size bytes: 85
- Rows sampled: 7

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `gbifRegion` | `object` | 0.00 | 7 |

### File 8

- Path:

  ```text
  data/gis/locations/hierarchy.csv
  ```

- Status: `profiled`
- Extension: `csv`
- Size bytes: 1,707,995
- Rows sampled: 50,000

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `level` | `int64` | 0.00 | 3 |
| `gid` | `object` | 0.01 | 49,869 |
| `name` | `object` | 0.04 | 44,342 |
| `parent_gid` | `object` | 0.57 | 3,028 |

### File 9

- Path:

  ```text
  data/gis/locations/level0.csv
  ```

- Status: `profiled`
- Extension: `csv`
- Size bytes: 4,247
- Rows sampled: 263

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `gid` | `object` | 0.00 | 263 |
| `name` | `object` | 0.00 | 263 |

### File 10

- Path:

  ```text
  data/gis/locations/level1.csv
  ```

- Status: `profiled`
- Extension: `csv`
- Size bytes: 72,241
- Rows sampled: 3,669

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `gid` | `object` | 0.11 | 3,661 |
| `name` | `object` | 0.03 | 3,534 |

### File 11

- Path:

  ```text
  data/gis/locations/level2.csv
  ```

- Status: `profiled`
- Extension: `csv`
- Size bytes: 1,104,328
- Rows sampled: 47,339

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `gid` | `object` | 0.00 | 47,217 |
| `name` | `object` | 0.04 | 42,692 |

### File 12

- Path:

  ```text
  data/gis/locations/location_taxa.parquet
  ```

- Status: `skipped`
- Extension: `parquet`
- Size bytes: 88,199,658
- Notes: File exceeds --max-download-bytes; increase limit to include

### File 13

- Path:

  ```text
  data/species/taxonomy/Animalia_1/Acanthocephala_67/Archiacanthocephala_253/Oligacanthorhynchida_469/
  Oligacanthorhynchidae_3537/Macracanthorhynchus_2499622/Macracanthorhynchus_hirudinaceus_2499627/
  occurrence.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 64,771
- Rows sampled: 1

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `decimalLatitude` | `double` | n/a | n/a |
| `decimalLongitude` | `double` | n/a | n/a |
| `catalogNumber` | `large_string` | n/a | n/a |
| `tileId` | `large_string` | n/a | n/a |
| `eventTimestamp` | `int64` | n/a | n/a |
| `coordinateUncertaintyInMeters` | `double` | n/a | n/a |
| `obscured` | `large_string` | n/a | n/a |
| `gbifRegion` | `large_string` | n/a | n/a |
| `level0Gid` | `large_string` | n/a | n/a |
| `level1Gid` | `large_string` | n/a | n/a |
| `level2Gid` | `large_string` | n/a | n/a |
| `dp` | `large_string` | n/a | n/a |
| `sex` | `large_string` | n/a | n/a |
| `lifeStage` | `large_string` | n/a | n/a |
| `rcs` | `large_string` | n/a | n/a |
| `vitality` | `large_string` | n/a | n/a |
| `gall` | `large_string` | n/a | n/a |
| `bio_1` | `double` | n/a | n/a |
| `bio_2` | `double` | n/a | n/a |
| `bio_3` | `double` | n/a | n/a |
| `bio_4` | `double` | n/a | n/a |
| `bio_5` | `double` | n/a | n/a |
| `bio_6` | `double` | n/a | n/a |
| `bio_7` | `double` | n/a | n/a |
| `bio_8` | `double` | n/a | n/a |
| `bio_9` | `double` | n/a | n/a |
| `bio_10` | `double` | n/a | n/a |
| `bio_11` | `double` | n/a | n/a |
| `bio_12` | `double` | n/a | n/a |
| `bio_13` | `double` | n/a | n/a |
| `bio_14` | `double` | n/a | n/a |
| `bio_15` | `double` | n/a | n/a |
| `bio_16` | `double` | n/a | n/a |
| `bio_17` | `double` | n/a | n/a |
| `bio_18` | `double` | n/a | n/a |
| `bio_19` | `double` | n/a | n/a |
| `landcover` | `double` | n/a | n/a |
| `koppen_geiger` | `double` | n/a | n/a |
| `slope` | `double` | n/a | n/a |
| `aspect` | `double` | n/a | n/a |
| `aspect_deg` | `double` | n/a | n/a |
| `elevation` | `double` | n/a | n/a |
| `cloud_cover_avg_1h` | `double` | n/a | n/a |
| `cloud_cover_avg_8h` | `double` | n/a | n/a |
| `cloud_cover_avg_24h` | `double` | n/a | n/a |
| `cloud_cover_avg_72h` | `double` | n/a | n/a |
| `cloud_cover_avg_168h` | `double` | n/a | n/a |
| `cloud_cover_avg_720h` | `double` | n/a | n/a |
| `cloud_cover_avg_2160h` | `double` | n/a | n/a |
| `snowfall_water_equivalent_sum_1h` | `double` | n/a | n/a |
| `snowfall_water_equivalent_sum_8h` | `double` | n/a | n/a |
| `snowfall_water_equivalent_sum_24h` | `double` | n/a | n/a |
| `snowfall_water_equivalent_sum_72h` | `double` | n/a | n/a |
| `snowfall_water_equivalent_sum_168h` | `double` | n/a | n/a |
| `snowfall_water_equivalent_sum_720h` | `double` | n/a | n/a |
| `snowfall_water_equivalent_sum_2160h` | `double` | n/a | n/a |
| `precipitation_sum_1h` | `double` | n/a | n/a |
| `precipitation_sum_8h` | `double` | n/a | n/a |
| `precipitation_sum_24h` | `double` | n/a | n/a |
| `precipitation_sum_72h` | `double` | n/a | n/a |
| `precipitation_sum_168h` | `double` | n/a | n/a |
| `precipitation_sum_720h` | `double` | n/a | n/a |
| `precipitation_sum_2160h` | `double` | n/a | n/a |
| `dew_point_2m_avg_1h` | `double` | n/a | n/a |
| `dew_point_2m_avg_8h` | `double` | n/a | n/a |
| `dew_point_2m_avg_24h` | `double` | n/a | n/a |
| `dew_point_2m_avg_72h` | `double` | n/a | n/a |
| `dew_point_2m_avg_168h` | `double` | n/a | n/a |
| `dew_point_2m_avg_720h` | `double` | n/a | n/a |
| `dew_point_2m_avg_2160h` | `double` | n/a | n/a |
| `vapor_pressure_deficit_avg_1h` | `double` | n/a | n/a |
| `vapor_pressure_deficit_avg_8h` | `double` | n/a | n/a |
| `vapor_pressure_deficit_avg_24h` | `double` | n/a | n/a |
| `vapor_pressure_deficit_avg_72h` | `double` | n/a | n/a |
| `vapor_pressure_deficit_avg_168h` | `double` | n/a | n/a |
| `vapor_pressure_deficit_avg_720h` | `double` | n/a | n/a |
| `vapor_pressure_deficit_avg_2160h` | `double` | n/a | n/a |
| `soil_moisture_0_to_7cm_avg_1h` | `double` | n/a | n/a |
| `soil_moisture_0_to_7cm_avg_8h` | `double` | n/a | n/a |
| `soil_moisture_0_to_7cm_avg_24h` | `double` | n/a | n/a |
| `soil_moisture_0_to_7cm_avg_72h` | `double` | n/a | n/a |
| `soil_moisture_0_to_7cm_avg_168h` | `double` | n/a | n/a |
| `soil_moisture_0_to_7cm_avg_720h` | `double` | n/a | n/a |
| `soil_moisture_0_to_7cm_avg_2160h` | `double` | n/a | n/a |
| `soil_temperature_0_to_7cm_avg_1h` | `double` | n/a | n/a |
| `soil_temperature_0_to_7cm_avg_8h` | `double` | n/a | n/a |
| `soil_temperature_0_to_7cm_avg_24h` | `double` | n/a | n/a |
| `soil_temperature_0_to_7cm_avg_72h` | `double` | n/a | n/a |
| `soil_temperature_0_to_7cm_avg_168h` | `double` | n/a | n/a |
| `soil_temperature_0_to_7cm_avg_720h` | `double` | n/a | n/a |
| `soil_temperature_0_to_7cm_avg_2160h` | `double` | n/a | n/a |
| `temperature_2m_avg_1h` | `double` | n/a | n/a |
| `temperature_2m_avg_8h` | `double` | n/a | n/a |
| `temperature_2m_avg_24h` | `double` | n/a | n/a |
| `temperature_2m_avg_72h` | `double` | n/a | n/a |
| `temperature_2m_avg_168h` | `double` | n/a | n/a |
| `temperature_2m_avg_720h` | `double` | n/a | n/a |
| `temperature_2m_avg_2160h` | `double` | n/a | n/a |
| `snow_depth_avg_1h` | `double` | n/a | n/a |
| `weather_code_simple` | `int64` | n/a | n/a |

### File 14

- Path:

  ```text
  data/species/taxonomy/Animalia_1/Acanthocephala_67/Archiacanthocephala_253/Oligacanthorhynchida_469/
  Oligacanthorhynchidae_3537/Macracanthorhynchus_2499622/Macracanthorhynchus_hirudinaceus_2499627/
  occurrence_index.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 21,081
- Rows sampled: 1

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `bio_1` | `struct<catalogNumber: string,…` | n/a | n/a |
| `bio_2` | `struct<catalogNumber: string,…` | n/a | n/a |
| `bio_3` | `struct<catalogNumber: string,…` | n/a | n/a |
| `bio_4` | `struct<catalogNumber: string,…` | n/a | n/a |
| `bio_5` | `struct<catalogNumber: string,…` | n/a | n/a |
| `bio_6` | `struct<catalogNumber: string,…` | n/a | n/a |
| `bio_7` | `struct<catalogNumber: string,…` | n/a | n/a |
| `bio_8` | `struct<catalogNumber: string,…` | n/a | n/a |
| `bio_9` | `struct<catalogNumber: string,…` | n/a | n/a |
| `bio_10` | `struct<catalogNumber: string,…` | n/a | n/a |
| `bio_11` | `struct<catalogNumber: string,…` | n/a | n/a |
| `bio_12` | `struct<catalogNumber: string,…` | n/a | n/a |
| `bio_13` | `struct<catalogNumber: string,…` | n/a | n/a |
| `bio_14` | `struct<catalogNumber: string,…` | n/a | n/a |
| `bio_15` | `struct<catalogNumber: string,…` | n/a | n/a |
| `bio_16` | `struct<catalogNumber: string,…` | n/a | n/a |
| `bio_17` | `struct<catalogNumber: string,…` | n/a | n/a |
| `bio_18` | `struct<catalogNumber: string,…` | n/a | n/a |
| `bio_19` | `struct<catalogNumber: string,…` | n/a | n/a |
| `landcover` | `struct<catalogNumber: string,…` | n/a | n/a |
| `koppen_geiger` | `struct<catalogNumber: string,…` | n/a | n/a |

### File 15

- Path:

  ```text
  data/species/taxonomy/Animalia_1/Acanthocephala_67/Archiacanthocephala_253/Oligacanthorhynchida_469/
  Oligacanthorhynchidae_3537/Macracanthorhynchus_2499622/Macracanthorhynchus_hirudinaceus_2499627/
  summary_stats.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 7,740
- Rows sampled: 79

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `variable` | `large_string` | n/a | n/a |
| `count` | `int64` | n/a | n/a |
| `min` | `double` | n/a | n/a |
| `10th percentile` | `double` | n/a | n/a |
| `25th percentile` | `double` | n/a | n/a |
| `median` | `double` | n/a | n/a |
| `75th percentile` | `double` | n/a | n/a |
| `90th percentile` | `double` | n/a | n/a |
| `max` | `double` | n/a | n/a |
| `mean` | `double` | n/a | n/a |
| `std` | `double` | n/a | n/a |
| `10-90 range` | `double` | n/a | n/a |
| `range` | `double` | n/a | n/a |

### File 16

- Path:

  ```text
  data/species/taxonomy/Animalia_1/Acanthocephala_67/Archiacanthocephala_253/Oligacanthorhynchida_469/
  Oligacanthorhynchidae_3537/Macracanthorhynchus_2499622/species.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 1,800
- Rows sampled: 1

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `taxon_key` | `string` | n/a | n/a |
| `sample_count` | `int64` | n/a | n/a |

### File 17

- Path:

  ```text
  data/species/taxonomy/Animalia_1/Acanthocephala_67/Archiacanthocephala_253/Oligacanthorhynchida_469/
  Oligacanthorhynchidae_3537/genus.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 1,800
- Rows sampled: 1

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `taxon_key` | `string` | n/a | n/a |
| `sample_count` | `int64` | n/a | n/a |

### File 18

- Path:

  ```text
  data/species/taxonomy/Animalia_1/Acanthocephala_67/Archiacanthocephala_253/Oligacanthorhynchida_469/
  Oligacanthorhynchidae_3537/species.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 1,800
- Rows sampled: 1

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `taxon_key` | `string` | n/a | n/a |
| `sample_count` | `int64` | n/a | n/a |

### File 19

- Path:

  ```text
  data/species/taxonomy/Animalia_1/Acanthocephala_67/Archiacanthocephala_253/Oligacanthorhynchida_469/
  family.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 1,785
- Rows sampled: 1

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `taxon_key` | `string` | n/a | n/a |
| `sample_count` | `int64` | n/a | n/a |

### File 20

- Path:

  ```text
  data/species/taxonomy/Animalia_1/Acanthocephala_67/Archiacanthocephala_253/Oligacanthorhynchida_469/
  genus.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 1,800
- Rows sampled: 1

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `taxon_key` | `string` | n/a | n/a |
| `sample_count` | `int64` | n/a | n/a |
