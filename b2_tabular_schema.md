# B2 Tabular Schema Sample

- Generated UTC: 2026-02-26T06:48:29.535270+00:00
- Source: `local:/home/kelly/Softwares/wherewild/data`
- Candidates considered: 50
- Profiles generated: 46
- Skipped files: 1
- Failed files: 3

## Profiled Files

### File 1

- Path:

  ```text
  species/taxonomy/Fungi_5/genus.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 31,941
- Rows sampled: 3,249

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `taxon_key` | `large_string` | n/a | n/a |
| `sample_count` | `int64` | n/a | n/a |

### File 2

- Path:

  ```text
  species/taxonomy/Animalia_1/phylum_index.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 503,675
- Rows sampled: 27

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `bio_1::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::impervious_surfaces` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_deciduous_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::herbaceous_cover_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_evergreen_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::sparse_vegetation` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::deciduous_shrubland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_mixed_leaf_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::rainfed_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_evergreen_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::water_body` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::grassland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::shrubland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfb_humid_continental_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cfb_humid_subtropical_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csb_mediterranean_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfc_humid_continental_with_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::et_polar_tundra_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cfa_humid_subtropical_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dwb_continental_with_dry_winters_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dwc_continental_with_dry_winters_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csa_mediterranean_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_evergreen_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::wetlands` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::aw_tropical_savannah_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::af_tropical_rainforest_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cwa_temperate_with_dry_winters_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::am_tropical_monsoon_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bsk_cold_semi_arid_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bsh_hot_semi_arid_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::tree_or_shrub_cover_cropland_orchard` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_deciduous_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfa_humid_continental_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::bare_areas` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::sparse_herbaceous` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_mixed_leaf_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::permanent_ice_and_snow` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::irrigated_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::consolidated_bare_areas` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_evergreen_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::evergreen_shrubland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::lichens_and_mosses` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_deciduous_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bwh_hot_desert_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bwk_cold_desert_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dsc_continental_with_dry_summers_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cfc_humid_oceanic_with_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dsb_continental_with_dry_summers_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cwb_temperate_with_dry_winters_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dwa_continental_with_dry_winters_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dsa_continental_with_dry_summers_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_deciduous_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::unconsolidated_bare_areas` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::sparse_shrubland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_60` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_50` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::filled_value` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cwc_temperate_with_dry_winters_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csc_mediterranean_with_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfd_humid_continental_with_severe_winters` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dwd_continental_with_dry_winters_severe_winters` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::ef_polar_frost_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::e` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::n` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::s` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::nw` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::se` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::sw` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::ne` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::w` | `struct<taxonKey: string, valu…` | n/a | n/a |

### File 3

- Path:

  ```text
  species/taxonomy/Animalia_1/categorical_stats.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 4,403
- Rows sampled: 93

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `variable` | `large_string` | n/a | n/a |
| `metric` | `large_string` | n/a | n/a |
| `value` | `double` | n/a | n/a |

### File 4

- Path:

  ```text
  species/taxonomy/Bacteria_3/family_index.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 689,887
- Rows sampled: 73

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `bio_1::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::herbaceous_cover_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::water_body` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_deciduous_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::impervious_surfaces` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_evergreen_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::wetlands` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::tree_or_shrub_cover_cropland_orchard` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_mixed_leaf_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::shrubland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::irrigated_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_evergreen_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cfa_humid_subtropical_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cfb_humid_subtropical_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfb_humid_continental_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfa_humid_continental_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bsk_cold_semi_arid_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::et_polar_tundra_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfc_humid_continental_with_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bwh_hot_desert_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csa_mediterranean_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csb_mediterranean_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bsh_hot_semi_arid_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::af_tropical_rainforest_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::grassland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::rainfed_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_deciduous_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::bare_areas` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_deciduous_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_evergreen_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_deciduous_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::sparse_vegetation` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cwa_temperate_with_dry_winters_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::aw_tropical_savannah_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cwb_temperate_with_dry_winters_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::am_tropical_monsoon_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dsb_continental_with_dry_summers_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dwb_continental_with_dry_winters_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bwk_cold_desert_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::lichens_and_mosses` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::deciduous_shrubland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_mixed_leaf_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::permanent_ice_and_snow` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_evergreen_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dsc_continental_with_dry_summers_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dwc_continental_with_dry_winters_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cfc_humid_oceanic_with_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dwa_continental_with_dry_winters_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::n` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::nw` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::w` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::e` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::sw` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::se` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::ne` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::s` | `struct<taxonKey: string, valu…` | n/a | n/a |

### File 5

- Path:

  ```text
  species/taxonomy/Plantae_6/order_index.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 1,460,055
- Rows sampled: 194

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `bio_1::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_52` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_15` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_16` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::class_7` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::class_3` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::class_8` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::class_1` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::class_5` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_62` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_120` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_72` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_12` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_130` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_20` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_11` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_61` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_190` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_10` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_92` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_210` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_150` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_82` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_180` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_122` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_51` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_71` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_200` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_140` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_220` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_81` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_91` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_153` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_121` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_8` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_9` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_14` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_7` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_6` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_5` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_12` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_1` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_2` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_3` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_29` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_27` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_11` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_26` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_25` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_18` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_19` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_22` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_21` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_23` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_4` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_17` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_10` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::class_4` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::class_2` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::class_6` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_201` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_152` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_250` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_13` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_202` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_28` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_24` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_30` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_20` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_50` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_60` | `struct<taxonKey: string, valu…` | n/a | n/a |

### File 6

- Path:

  ```text
  species/taxonomy/Plantae_6/class_index.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 551,927
- Rows sampled: 34

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `bio_1::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_52` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_62` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_120` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_72` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_12` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_130` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_20` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_11` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_61` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_190` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_10` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_92` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_210` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_150` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_82` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_180` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_122` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_51` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_71` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_200` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_140` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_220` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_81` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_91` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_153` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_121` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_15` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_16` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_8` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_9` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_14` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_7` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_6` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_5` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_12` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_1` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_2` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_3` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_29` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_27` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_11` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_26` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_25` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_18` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_19` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_22` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_21` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_23` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_4` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_17` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_10` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::class_7` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::class_3` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::class_8` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::class_1` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::class_5` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::class_4` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::class_2` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::class_6` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_201` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_152` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_13` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_24` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_28` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_202` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_50` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_60` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_250` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_30` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_20` | `struct<taxonKey: string, valu…` | n/a | n/a |

### File 7

- Path:

  ```text
  species/taxonomy/Archaea_2/phylum.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 1,825
- Rows sampled: 2

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `taxon_key` | `string` | n/a | n/a |
| `sample_count` | `int64` | n/a | n/a |

### File 8

- Path:

  ```text
  species/taxonomy/Archaea_2/species.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 1,842
- Rows sampled: 4

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `taxon_key` | `string` | n/a | n/a |
| `sample_count` | `int64` | n/a | n/a |

### File 9

- Path:

  ```text
  gis/locations/level0.csv
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
  species/taxonomy/Animalia_1/phylum.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 2,085
- Rows sampled: 27

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `taxon_key` | `string` | n/a | n/a |
| `sample_count` | `int64` | n/a | n/a |

### File 11

- Path:

  ```text
  species/taxonomy/Fungi_5/order.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 3,672
- Rows sampled: 175

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `taxon_key` | `large_string` | n/a | n/a |
| `sample_count` | `int64` | n/a | n/a |

### File 12

- Path:

  ```text
  gis/legends/landcover_legend.json
  ```

- Status: `failed`
- Extension: `json`
- Size bytes: 4,442
- Error: unhashable type: 'list'

### File 13

- Path:

  ```text
  species/taxonomy/Chromista_4/summary_stats.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 15,580
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

### File 14

- Path:

  ```text
  species/taxonomy/Animalia_1/order.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 6,752
- Rows sampled: 455

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `taxon_key` | `string` | n/a | n/a |
| `sample_count` | `int64` | n/a | n/a |

### File 15

- Path:

  ```text
  species/taxonomy/Chromista_4/class.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 2,218
- Rows sampled: 34

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `taxon_key` | `string` | n/a | n/a |
| `sample_count` | `int64` | n/a | n/a |

### File 16

- Path:

  ```text
  species/taxonomy/Viruses_8/summary_stats.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 15,567
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

### File 17

- Path:

  ```text
  species/taxonomy/Animalia_1/family_index.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 18,511,780
- Rows sampled: 4,153

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `bio_1::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cfa_humid_subtropical_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::water_body` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::wetlands` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfa_humid_continental_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_evergreen_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::impervious_surfaces` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_deciduous_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::herbaceous_cover_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::rainfed_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::shrubland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_deciduous_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::grassland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::irrigated_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_deciduous_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csb_mediterranean_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bsk_cold_semi_arid_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::aw_tropical_savannah_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csa_mediterranean_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bsh_hot_semi_arid_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cwa_temperate_with_dry_winters_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::am_tropical_monsoon_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cfb_humid_subtropical_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfc_humid_continental_with_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cwb_temperate_with_dry_winters_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cfc_humid_oceanic_with_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::et_polar_tundra_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_mixed_leaf_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_evergreen_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::af_tropical_rainforest_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_evergreen_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfb_humid_continental_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::bare_areas` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_evergreen_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dsc_continental_with_dry_summers_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::tree_or_shrub_cover_cropland_orchard` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::sparse_vegetation` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bwh_hot_desert_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bwk_cold_desert_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::deciduous_shrubland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dsb_continental_with_dry_summers_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dwa_continental_with_dry_winters_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::sparse_herbaceous` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_mixed_leaf_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::lichens_and_mosses` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::permanent_ice_and_snow` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::consolidated_bare_areas` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_deciduous_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dsa_continental_with_dry_summers_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::unconsolidated_bare_areas` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dwb_continental_with_dry_winters_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::evergreen_shrubland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dwc_continental_with_dry_winters_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csc_mediterranean_with_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::sparse_shrubland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_50` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cwc_temperate_with_dry_winters_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfd_humid_continental_with_severe_winters` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dwd_continental_with_dry_winters_severe_winters` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::ef_polar_frost_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::filled_value` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_60` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::n` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::nw` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::ne` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::sw` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::s` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::e` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::w` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::se` | `struct<taxonKey: string, valu…` | n/a | n/a |

### File 18

- Path:

  ```text
  gis/locations/gbif_regions.csv
  ```

- Status: `profiled`
- Extension: `csv`
- Size bytes: 85
- Rows sampled: 7

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `gbifRegion` | `object` | 0.00 | 7 |

### File 19

- Path:

  ```text
  species/taxonomy/Bacteria_3/order_index.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 522,195
- Rows sampled: 35

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `bio_1::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::impervious_surfaces` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::water_body` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cfa_humid_subtropical_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_evergreen_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bsk_cold_semi_arid_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfb_humid_continental_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cfb_humid_subtropical_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csb_mediterranean_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::wetlands` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bsh_hot_semi_arid_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::af_tropical_rainforest_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_deciduous_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_evergreen_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::herbaceous_cover_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_mixed_leaf_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::shrubland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_deciduous_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::grassland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfa_humid_continental_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bwk_cold_desert_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csa_mediterranean_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::irrigated_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::bare_areas` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_evergreen_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::sparse_vegetation` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cwa_temperate_with_dry_winters_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfc_humid_continental_with_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bwh_hot_desert_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cwb_temperate_with_dry_winters_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::aw_tropical_savannah_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::rainfed_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::am_tropical_monsoon_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::tree_or_shrub_cover_cropland_orchard` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::deciduous_shrubland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_deciduous_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_mixed_leaf_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dsb_continental_with_dry_summers_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dwb_continental_with_dry_winters_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dwc_continental_with_dry_winters_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dwa_continental_with_dry_winters_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_deciduous_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dsc_continental_with_dry_summers_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::lichens_and_mosses` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::permanent_ice_and_snow` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_evergreen_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::et_polar_tundra_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cfc_humid_oceanic_with_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::n` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::w` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::nw` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::ne` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::sw` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::se` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::e` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::s` | `struct<taxonKey: string, valu…` | n/a | n/a |

### File 20

- Path:

  ```text
  species/taxonomy/Archaea_2/species_index.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 316,516
- Rows sampled: 3

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `bio_1::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::herbaceous_cover_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::bare_areas` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::shrubland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_evergreen_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfb_humid_continental_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfc_humid_continental_with_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::impervious_surfaces` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::water_body` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_deciduous_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csb_mediterranean_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csa_mediterranean_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::aw_tropical_savannah_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bwk_cold_desert_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bsk_cold_semi_arid_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::w` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::s` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::n` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::se` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::ne` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::nw` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::sw` | `struct<taxonKey: string, valu…` | n/a | n/a |

### File 21

- Path:

  ```text
  species/taxonomy/Archaea_2/phylum_index.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 312,556
- Rows sampled: 2

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `bio_1::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::impervious_surfaces` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::bare_areas` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::water_body` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::shrubland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_deciduous_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::herbaceous_cover_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csb_mediterranean_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csa_mediterranean_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::aw_tropical_savannah_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bwk_cold_desert_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bsk_cold_semi_arid_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_evergreen_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfb_humid_continental_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfc_humid_continental_with_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::nw` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::n` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::w` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::sw` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::s` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::se` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::ne` | `struct<taxonKey: string, valu…` | n/a | n/a |

### File 22

- Path:

  ```text
  species/taxonomy/Chromista_4/family_index.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 1,697,320
- Rows sampled: 333

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `bio_1::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::herbaceous_cover_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::water_body` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::wetlands` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::grassland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::impervious_surfaces` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_deciduous_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cfa_humid_subtropical_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfb_humid_continental_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::af_tropical_rainforest_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cfb_humid_subtropical_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cwb_temperate_with_dry_winters_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfa_humid_continental_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csb_mediterranean_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_evergreen_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::rainfed_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_mixed_leaf_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::irrigated_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csa_mediterranean_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfc_humid_continental_with_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bsk_cold_semi_arid_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_evergreen_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::aw_tropical_savannah_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bsh_hot_semi_arid_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_deciduous_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dwc_continental_with_dry_winters_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dwb_continental_with_dry_winters_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::bare_areas` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::am_tropical_monsoon_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cwa_temperate_with_dry_winters_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::tree_or_shrub_cover_cropland_orchard` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::shrubland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_evergreen_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::sparse_vegetation` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bwh_hot_desert_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bwk_cold_desert_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::et_polar_tundra_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::evergreen_shrubland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dsb_continental_with_dry_summers_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cfc_humid_oceanic_with_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_deciduous_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_evergreen_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dwa_continental_with_dry_winters_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dsc_continental_with_dry_summers_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::consolidated_bare_areas` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::permanent_ice_and_snow` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::sparse_herbaceous` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::deciduous_shrubland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_mixed_leaf_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::lichens_and_mosses` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_deciduous_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::n` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::ne` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::w` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::e` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::nw` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::sw` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::se` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::s` | `struct<taxonKey: string, valu…` | n/a | n/a |

### File 23

- Path:

  ```text
  species/taxonomy/Fungi_5/species.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 159,530
- Rows sampled: 18,528

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `taxon_key` | `large_string` | n/a | n/a |
| `sample_count` | `int64` | n/a | n/a |

### File 24

- Path:

  ```text
  species/taxonomy/Bacteria_3/class_index.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 418,199
- Rows sampled: 14

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `bio_1::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::grassland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_evergreen_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_deciduous_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::impervious_surfaces` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_mixed_leaf_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::herbaceous_cover_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::rainfed_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::wetlands` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::shrubland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::water_body` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::irrigated_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_deciduous_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_evergreen_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::tree_or_shrub_cover_cropland_orchard` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_evergreen_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_deciduous_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::sparse_vegetation` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_deciduous_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bsh_hot_semi_arid_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cfa_humid_subtropical_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfb_humid_continental_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bsk_cold_semi_arid_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csb_mediterranean_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cfb_humid_subtropical_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfa_humid_continental_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfc_humid_continental_with_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csa_mediterranean_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dwb_continental_with_dry_winters_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bwh_hot_desert_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::am_tropical_monsoon_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cwa_temperate_with_dry_winters_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cwb_temperate_with_dry_winters_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::aw_tropical_savannah_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dsb_continental_with_dry_summers_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::af_tropical_rainforest_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dsc_continental_with_dry_summers_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bwk_cold_desert_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dwc_continental_with_dry_winters_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::bare_areas` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::deciduous_shrubland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_mixed_leaf_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dwa_continental_with_dry_winters_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cfc_humid_oceanic_with_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::lichens_and_mosses` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::permanent_ice_and_snow` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_evergreen_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::et_polar_tundra_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::nw` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::sw` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::n` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::s` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::ne` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::e` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::w` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::se` | `struct<taxonKey: string, valu…` | n/a | n/a |

### File 25

- Path:

  ```text
  species/taxonomy/Chromista_4/order.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 3,332
- Rows sampled: 143

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `taxon_key` | `string` | n/a | n/a |
| `sample_count` | `int64` | n/a | n/a |

### File 26

- Path:

  ```text
  species/taxonomy/Archaea_2/density_graph.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 26,431
- Rows sampled: 79

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `variable` | `string` | n/a | n/a |
| `count` | `int64` | n/a | n/a |
| `sampleCount` | `int64` | n/a | n/a |
| `pointCount` | `int64` | n/a | n/a |
| `points` | `list<element: double>` | n/a | n/a |
| `density` | `list<element: double>` | n/a | n/a |
| `min` | `double` | n/a | n/a |
| `max` | `double` | n/a | n/a |
| `bandwidth` | `double` | n/a | n/a |

### File 27

- Path:

  ```text
  species/taxonomy/Bacteria_3/genus.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 3,626
- Rows sampled: 206

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `taxon_key` | `string` | n/a | n/a |
| `sample_count` | `int64` | n/a | n/a |

### File 28

- Path:

  ```text
  species/taxonomy/Viruses_8/family.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 2,000
- Rows sampled: 20

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `taxon_key` | `string` | n/a | n/a |
| `sample_count` | `int64` | n/a | n/a |

### File 29

- Path:

  ```text
  gis/legends/weather_code_simple_avg_1h_legend.json
  ```

- Status: `failed`
- Extension: `json`
- Size bytes: 2,710
- Error: unhashable type: 'list'

### File 30

- Path:

  ```text
  species/taxonomy/Viruses_8/species_index.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 465,189
- Rows sampled: 31

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `bio_1::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::sparse_vegetation` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bsk_cold_semi_arid_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::impervious_surfaces` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cfa_humid_subtropical_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cfb_humid_subtropical_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_evergreen_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfb_humid_continental_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_mixed_leaf_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_deciduous_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::rainfed_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cwb_temperate_with_dry_winters_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::herbaceous_cover_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfa_humid_continental_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::grassland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::wetlands` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dsb_continental_with_dry_summers_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfc_humid_continental_with_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::water_body` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bsh_hot_semi_arid_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csb_mediterranean_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bwh_hot_desert_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csa_mediterranean_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_evergreen_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::aw_tropical_savannah_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_evergreen_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::tree_or_shrub_cover_cropland_orchard` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dwa_continental_with_dry_winters_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::et_polar_tundra_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::irrigated_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::shrubland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_deciduous_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::bare_areas` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::sw` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::se` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::w` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::ne` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::n` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::s` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::e` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::nw` | `struct<taxonKey: string, valu…` | n/a | n/a |

### File 31

- Path:

  ```text
  species/taxonomy/Bacteria_3/genus_index.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 933,445
- Rows sampled: 132

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `bio_1::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_evergreen_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cfa_humid_subtropical_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::impervious_surfaces` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::herbaceous_cover_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cfb_humid_subtropical_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfb_humid_continental_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::shrubland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfc_humid_continental_with_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::water_body` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_evergreen_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_deciduous_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::bare_areas` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::sparse_vegetation` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::grassland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_evergreen_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_mixed_leaf_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::rainfed_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfa_humid_continental_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csb_mediterranean_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bsk_cold_semi_arid_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::aw_tropical_savannah_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::af_tropical_rainforest_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csa_mediterranean_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bwk_cold_desert_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cwa_temperate_with_dry_winters_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_deciduous_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dwb_continental_with_dry_winters_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::wetlands` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dsb_continental_with_dry_summers_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cwb_temperate_with_dry_winters_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bsh_hot_semi_arid_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::tree_or_shrub_cover_cropland_orchard` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::am_tropical_monsoon_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::irrigated_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_deciduous_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_deciduous_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bwh_hot_desert_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::lichens_and_mosses` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::deciduous_shrubland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_mixed_leaf_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::permanent_ice_and_snow` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_evergreen_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dsc_continental_with_dry_summers_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::et_polar_tundra_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dwc_continental_with_dry_winters_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cfc_humid_oceanic_with_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dwa_continental_with_dry_winters_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::ne` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::n` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::e` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::nw` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::sw` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::se` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::w` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::s` | `struct<taxonKey: string, valu…` | n/a | n/a |

### File 32

- Path:

  ```text
  gis/locations/level1.csv
  ```

- Status: `profiled`
- Extension: `csv`
- Size bytes: 72,241
- Rows sampled: 3,669

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `gid` | `object` | 0.11 | 3,661 |
| `name` | `object` | 0.03 | 3,534 |

### File 33

- Path:

  ```text
  gis/catalog.json
  ```

- Status: `failed`
- Extension: `json`
- Size bytes: 8,449
- Error: unhashable type: 'list'

### File 34

- Path:

  ```text
  species/taxonomy/Archaea_2/order_index.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 303,798
- Rows sampled: 2

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `bio_1::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::herbaceous_cover_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::bare_areas` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::shrubland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_evergreen_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfb_humid_continental_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfc_humid_continental_with_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::impervious_surfaces` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::water_body` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_deciduous_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csb_mediterranean_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csa_mediterranean_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::aw_tropical_savannah_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bwk_cold_desert_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bsk_cold_semi_arid_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::w` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::s` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::n` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::se` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::ne` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::sw` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::nw` | `struct<taxonKey: string, valu…` | n/a | n/a |

### File 35

- Path:

  ```text
  species/taxonomy/Bacteria_3/categorical_stats.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 4,113
- Rows sampled: 79

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `variable` | `large_string` | n/a | n/a |
| `metric` | `large_string` | n/a | n/a |
| `value` | `double` | n/a | n/a |

### File 36

- Path:

  ```text
  species/taxonomy/Plantae_6/phylum.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 857
- Rows sampled: 8

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `taxon_key` | `string` | n/a | n/a |
| `sample_count` | `int64` | n/a | n/a |

### File 37

- Path:

  ```text
  species/taxonomy/Bacteria_3/family.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 2,779
- Rows sampled: 104

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `taxon_key` | `string` | n/a | n/a |
| `sample_count` | `int64` | n/a | n/a |

### File 38

- Path:

  ```text
  species/taxonomy/Archaea_2/family_index.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 305,550
- Rows sampled: 2

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `bio_1::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::impervious_surfaces` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::bare_areas` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::water_body` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::shrubland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_deciduous_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::herbaceous_cover_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csb_mediterranean_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csa_mediterranean_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::aw_tropical_savannah_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bwk_cold_desert_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bsk_cold_semi_arid_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_evergreen_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfb_humid_continental_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfc_humid_continental_with_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::nw` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::n` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::w` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::sw` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::s` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::se` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::ne` | `struct<taxonKey: string, valu…` | n/a | n/a |

### File 39

- Path:

  ```text
  species/taxonomy/Fungi_5/phylum_index.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 402,051
- Rows sampled: 8

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `bio_1::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_evergreen_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::rainfed_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_mixed_leaf_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::am_tropical_monsoon_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cfb_humid_subtropical_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_evergreen_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::impervious_surfaces` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::herbaceous_cover_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_deciduous_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::sparse_vegetation` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::shrubland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::grassland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_evergreen_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::closed_deciduous_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_mixed_leaf_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::irrigated_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::bare_areas` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::tree_or_shrub_cover_cropland_orchard` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_evergreen_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::water_body` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::wetlands` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::deciduous_shrubland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::permanent_ice_and_snow` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_deciduous_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_deciduous_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::sparse_herbaceous` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::evergreen_shrubland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::lichens_and_mosses` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::consolidated_bare_areas` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::sparse_shrubland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_50` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::unconsolidated_bare_areas` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_60` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfb_humid_continental_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bsh_hot_semi_arid_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csa_mediterranean_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csb_mediterranean_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bsk_cold_semi_arid_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bwk_cold_desert_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bwh_hot_desert_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dsb_continental_with_dry_summers_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cfa_humid_subtropical_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfc_humid_continental_with_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfa_humid_continental_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::aw_tropical_savannah_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cwb_temperate_with_dry_winters_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cwa_temperate_with_dry_winters_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dwa_continental_with_dry_winters_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::af_tropical_rainforest_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dwb_continental_with_dry_winters_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::et_polar_tundra_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dsc_continental_with_dry_summers_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cfc_humid_oceanic_with_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dsa_continental_with_dry_summers_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csc_mediterranean_with_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dwc_continental_with_dry_winters_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::cwc_temperate_with_dry_winters_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::ef_polar_frost_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfd_humid_continental_with_severe_winters` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::filled_value` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::s` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::w` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::sw` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::nw` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::ne` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::n` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::se` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::e` | `struct<taxonKey: string, valu…` | n/a | n/a |

### File 40

- Path:

  ```text
  species/taxonomy/Chromista_4/phylum.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 1,909
- Rows sampled: 10

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `taxon_key` | `string` | n/a | n/a |
| `sample_count` | `int64` | n/a | n/a |

### File 41

- Path:

  ```text
  species/taxonomy/Bacteria_3/summary_stats.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 15,689
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

### File 42

- Path:

  ```text
  species/taxonomy/Fungi_5/class.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 2,312
- Rows sampled: 45

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `taxon_key` | `large_string` | n/a | n/a |
| `sample_count` | `int64` | n/a | n/a |

### File 43

- Path:

  ```text
  species/taxonomy/Viruses_8/categorical_stats.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 3,656
- Rows sampled: 63

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `variable` | `large_string` | n/a | n/a |
| `metric` | `large_string` | n/a | n/a |
| `value` | `double` | n/a | n/a |

### File 44

- Path:

  ```text
  species/taxonomy/Animalia_1/species_index.parquet
  ```

- Status: `skipped`
- Extension: `parquet`
- Size bytes: 653,556,761
- Notes: File exceeds --max-download-bytes; increase limit to include

### File 45

- Path:

  ```text
  species/taxonomy/Plantae_6/class.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 1,197
- Rows sampled: 34

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `taxon_key` | `string` | n/a | n/a |
| `sample_count` | `int64` | n/a | n/a |

### File 46

- Path:

  ```text
  species/taxonomy/Plantae_6/phylum_index.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 389,298
- Rows sampled: 8

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `bio_1::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_52` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_62` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_120` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_72` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_12` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_130` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_20` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_11` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_61` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_190` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_10` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_92` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_210` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_150` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_82` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_180` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_122` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_51` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_71` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_200` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_140` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_220` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_81` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_91` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_153` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_121` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_15` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_16` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_8` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_9` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_14` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_7` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_6` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_5` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_12` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_1` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_2` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_3` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_29` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_27` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_11` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_26` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_25` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_18` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_19` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_22` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_21` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_23` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_4` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_17` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_10` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::class_7` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::class_3` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::class_8` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::class_1` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::class_5` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::class_4` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::class_2` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::class_6` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_201` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_152` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_13` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_30` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_202` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_50` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_250` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::class_60` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_28` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_24` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::class_20` | `struct<taxonKey: string, valu…` | n/a | n/a |

### File 47

- Path:

  ```text
  species/taxonomy/Plantae_6/family.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 10,340
- Rows sampled: 873

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `taxon_key` | `string` | n/a | n/a |
| `sample_count` | `int64` | n/a | n/a |

### File 48

- Path:

  ```text
  species/taxonomy/Archaea_2/class_index.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 308,140
- Rows sampled: 2

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `bio_1::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_1::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_2::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_3::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_4::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_5::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_6::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_7::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_8::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_9::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_10::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_11::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_12::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_13::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_14::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_15::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_16::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_17::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_18::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `bio_19::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::impervious_surfaces` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::bare_areas` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::water_body` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::shrubland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_deciduous_broadleaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::herbaceous_cover_cropland` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csb_mediterranean_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::csa_mediterranean_with_hot_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::aw_tropical_savannah_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bwk_cold_desert_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::bsk_cold_semi_arid_climate` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `landcover::open_evergreen_needle_leaved_forest` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfb_humid_continental_with_warm_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `koppen_geiger::dfc_humid_continental_with_cool_summers` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `slope::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect_deg::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::count` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::min` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::25th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::median` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::75th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::90th percentile` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::max` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::mean` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::std` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::10-90 range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `elevation::range` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::total_samples` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::significant_unique_classes` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::nw` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::n` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::w` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::sw` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::s` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::se` | `struct<taxonKey: string, valu…` | n/a | n/a |
| `aspect::ne` | `struct<taxonKey: string, valu…` | n/a | n/a |

### File 49

- Path:

  ```text
  species/taxonomy/Viruses_8/genus.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 2,070
- Rows sampled: 24

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `taxon_key` | `string` | n/a | n/a |
| `sample_count` | `int64` | n/a | n/a |

### File 50

- Path:

  ```text
  species/taxonomy/Animalia_1/species.parquet
  ```

- Status: `profiled`
- Extension: `parquet`
- Size bytes: 1,755,570
- Rows sampled: 259,039

| Column | Dtype | Null% | Distinct(sample) |
| --- | --- | ---: | ---: |
| `taxon_key` | `string` | n/a | n/a |
| `sample_count` | `int64` | n/a | n/a |
