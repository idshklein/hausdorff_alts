# QGIS MCP Test Results: `hausdorff_alts`

## Execution Status
Completed via QGIS MCP server against QGIS `3.40.11-Bratislava`.

- Date: 2026-03-09
- Algorithm: `hausdorff_alts:directed_hausdorff`
- Project: `C:/temp/hausdorff_mcp_test.qgz`

## Summary

- Total tests: `9`
- Passed: `9`
- Failed: `0`

## Test Outcomes

1. `plugin_load`: PASS (`active=True`)
2. `algorithm_registration`: PASS (`registered`)
3. `dataset_setup`: PASS (`src=2, tgt=2`)
4. `directed_1_1_offset`: PASS (`rows=1, distance=2.0`)
5. `symmetric_1_1_offset`: PASS (`rows=1, distance=2.0`)
6. `modes_row_counts`: PASS (`1-N=2, N-1=2, N-N=4`)
7. `asymmetry_containment`: PASS (`contained->base=8.881784197001252e-16, base->contained=2.0`)
8. `crs_mismatch_validation`: PASS (`Source and target layers must use the same CRS`)
9. `output_schema_geometry`: PASS (`schema_ok=True, geom_ok=True, dist_ok=True`)

## Compatibility Fixes Applied During Execution

Two runtime compatibility issues were detected and fixed, then tests were rerun:

1. Spatial index construction:
   - Changed from `QgsSpatialIndex(target_features)` to creating an empty index and adding features with `addFeature(...)`.
2. Nearest-point API usage:
   - Changed from `geom.closestPoint(point_geom)` to `geom.nearestPoint(point_geom)` for this QGIS build.

## Result

The processing-only plugin is validated end-to-end through MCP with all planned tests passing.
