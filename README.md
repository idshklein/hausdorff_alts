# Hausdorff Alts (QGIS Processing Plugin)

Processing-only QGIS plugin for **discrete Hausdorff distance** between vector geometries.

It provides:

- Directed Hausdorff distance (`A -> B`)
- Symmetric Hausdorff distance (`max(h(A,B), h(B,A))`)
- Optional both-directions output (`A -> B` and `B -> A` as two lines)
- Relationship modes: `1-1`, `1-N`, `N-1`, `N-N`
- Deviation line geometry showing where the distance is realized

## Version

Current release: **0.1.0**

## Algorithm

- Provider id: `hausdorff_alts`
- Algorithm id: `hausdorff_alts:directed_hausdorff`
- Display name: `Directed/Symmetric Hausdorff (Discrete)`

## Parameters

- `SOURCE`: source vector layer
- `TARGET`: target vector layer
- `MODE`: `1-1`, `1-N`, `N-1`, `N-N`
- `DIRECTED`: directed mode when checked; symmetric max when unchecked
- `BOTH_DIRECTIONS`: output both directed results (`A_to_B`, `B_to_A`) as two rows/lines
- `DENSIFY_STEP`: densification distance for sampling
- `MAX_NEIGHBORS`: candidate targets for `1-N` and `N-N`

Validation rules:

- Source/target CRS must match
- `DENSIFY_STEP > 0`
- `BOTH_DIRECTIONS=True` requires `DIRECTED=True`

## Output

Line output with fields:

- `distance`
- `source_id`
- `target_id`
- `direction` (`A_to_B` or `B_to_A`)
- `mode`

## Install

### From release ZIP

1. Download `hausdorff_alts-0.1.0-qgis-plugin.zip` from Releases.
2. In QGIS: `Plugins` -> `Manage and Install Plugins...` -> `Install from ZIP`.
3. Select the ZIP file and install.
4. Open Processing Toolbox and search for `Directed/Symmetric Hausdorff (Discrete)`.

Release page:

- https://github.com/idshklein/hausdorff_alts/releases/tag/v0.1.0

## Development

Plugin entry files:

- `__init__.py`
- `hausdorff_alts_plugin.py`
- `processing_provider.py`
- `algorithms/directed_hausdorff_algorithm.py`

## Testing

MCP-based test docs:

- `qgis_mcp_test_plan.md`
- `qgis_mcp_test_results.md`

## Notes

This plugin computes a **discrete approximation** of Hausdorff distance based on densified samples, not the exact continuous optimum.
