# QGIS MCP Test Plan: `hausdorff_alts` Processing Plugin

## Goal
Validate the Processing Toolbox-only algorithm:

- Provider: `hausdorff_alts`
- Algorithm: `directed_hausdorff`
- Full algorithm id: `hausdorff_alts:directed_hausdorff`

New option supported:

- `BOTH_DIRECTIONS` (Boolean): when `True`, outputs two rows/lines per pair (`A_to_B` and `B_to_A`).

This plan is designed to run directly through the QGIS MCP server (no custom plugin UI).

---

## Test Strategy
We validate:

1. Registration and discoverability in Processing
2. Directed Hausdorff correctness
3. Symmetric Hausdorff correctness
4. Relationship mode behavior (`1-1`, `1-N`, `N-1`, `N-N`)
5. Output schema and geometry validity
6. CRS validation behavior

---

## Preconditions

- Plugin folder is in the active QGIS profile plugins path.
- Plugin `Hausdorff Alts` is enabled.
- Processing provider is loaded.
- QGIS MCP server is reachable.

Optional quick check via MCP:

```text
mcp_qgis_ping
mcp_qgis_get_qgis_info
mcp_qgis_get_project_info
```

---

## Step 1: Create Test Project

Use MCP:

```text
mcp_qgis_create_new_project(path="C:/temp/hausdorff_mcp_test.qgz")
mcp_qgis_save_project(path="C:/temp/hausdorff_mcp_test.qgz")
```

Expected:

- New project exists and is active.

---

## Step 2: Build Deterministic In-Memory Test Layers

Run with `mcp_qgis_execute_code`:

```python
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsField,
)
from qgis.PyQt.QtCore import QVariant

project = QgsProject.instance()

# Source lines
src = QgsVectorLayer("LineString?crs=EPSG:3857", "src_lines", "memory")
src_dp = src.dataProvider()
src_dp.addAttributes([QgsField("name", QVariant.String)])
src.updateFields()

f1 = QgsFeature(src.fields())
f1["name"] = "line_base"
f1.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(0, 0), QgsPointXY(10, 0)]))

f2 = QgsFeature(src.fields())
f2["name"] = "line_contained"
f2.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(2, 0), QgsPointXY(8, 0)]))

src_dp.addFeatures([f1, f2])

# Target lines
tgt = QgsVectorLayer("LineString?crs=EPSG:3857", "tgt_lines", "memory")
tgt_dp = tgt.dataProvider()
tgt_dp.addAttributes([QgsField("name", QVariant.String)])
tgt.updateFields()

g1 = QgsFeature(tgt.fields())
g1["name"] = "line_offset_2"
g1.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(0, 2), QgsPointXY(10, 2)]))

g2 = QgsFeature(tgt.fields())
g2["name"] = "line_identical"
g2.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(0, 0), QgsPointXY(10, 0)]))

tgt_dp.addFeatures([g1, g2])

project.addMapLayer(src)
project.addMapLayer(tgt)

print("Created layers:", src.name(), src.featureCount(), tgt.name(), tgt.featureCount())
```

Expected:

- `src_lines` has 2 features
- `tgt_lines` has 2 features

---

## Step 3: Directed 1-1 (Known Offset = 2)

Run with `mcp_qgis_execute_code`:

```python
import processing
from qgis.core import QgsProject

src = QgsProject.instance().mapLayersByName("src_lines")[0]
tgt = QgsProject.instance().mapLayersByName("tgt_lines")[0]

params = {
    "SOURCE": src,
    "TARGET": tgt,
    "MODE": 0,              # 1-1
    "DIRECTED": True,
    "DENSIFY_STEP": 0.5,
    "MAX_NEIGHBORS": 10,
    "OUTPUT": "memory:",
}

res = processing.run("hausdorff_alts:directed_hausdorff", params)
out = res["OUTPUT"]

print("Output feature count:", out.featureCount())
for ft in out.getFeatures():
    print("distance=", ft["distance"], "direction=", ft["direction"], "mode=", ft["mode"])
```

Expected:

- One output row
- `distance` approximately `2.0` (within tolerance, e.g. `1e-6`)
- `direction` is `A_to_B`
- Output geometry is a valid line

---

## Step 4: Symmetric 1-1

Run same pair with `DIRECTED=False`:

```python
import processing
from qgis.core import QgsProject

src = QgsProject.instance().mapLayersByName("src_lines")[0]
tgt = QgsProject.instance().mapLayersByName("tgt_lines")[0]

params = {
    "SOURCE": src,
    "TARGET": tgt,
    "MODE": 0,
    "DIRECTED": False,
    "DENSIFY_STEP": 0.5,
    "MAX_NEIGHBORS": 10,
    "OUTPUT": "memory:",
}

res = processing.run("hausdorff_alts:directed_hausdorff", params)
out = res["OUTPUT"]

for ft in out.getFeatures():
    print("distance=", ft["distance"], "direction=", ft["direction"])
```

Expected:

- Symmetric distance equals max of both directions for selected first features
- For parallel equal-length offset lines, value remains about `2.0`

---

## Step 5: Relationship Modes

### Test 1-N

- Set `MODE=1`
- Expect one output row per candidate target (bounded by `MAX_NEIGHBORS`)

### Test N-1

- Set `MODE=2`
- Expect one output row per source feature

### Test N-N

- Set `MODE=3`
- Expect up to `len(source) * MAX_NEIGHBORS` rows (or full cross-product when neighbors exceed target count)

Validation snippet:

```python
def run_mode(mode):
    import processing
    from qgis.core import QgsProject
    src = QgsProject.instance().mapLayersByName("src_lines")[0]
    tgt = QgsProject.instance().mapLayersByName("tgt_lines")[0]
    params = {
        "SOURCE": src,
        "TARGET": tgt,
        "MODE": mode,
        "DIRECTED": True,
        "DENSIFY_STEP": 0.5,
        "MAX_NEIGHBORS": 10,
        "OUTPUT": "memory:",
    }
    res = processing.run("hausdorff_alts:directed_hausdorff", params)
    out = res["OUTPUT"]
    print("mode", mode, "rows", out.featureCount())

for m in [1, 2, 3]:
    run_mode(m)
```

---

## Step 5b: Both-Directions Output

Set:

- `DIRECTED=True` (or `False`, this flag is ignored when both-directions is enabled)
- `BOTH_DIRECTIONS=True`

Expected:

- Two output rows for each evaluated pair
- `direction` field contains both `A_to_B` and `B_to_A`

Quick check snippet:

```python
import processing
from qgis.core import QgsProject

src = QgsProject.instance().mapLayersByName("src_lines")[0]
tgt = QgsProject.instance().mapLayersByName("tgt_lines")[0]

params = {
    "SOURCE": src,
    "TARGET": tgt,
    "MODE": 0,
    "DIRECTED": True,
    "BOTH_DIRECTIONS": True,
    "DENSIFY_STEP": 0.5,
    "MAX_NEIGHBORS": 10,
    "OUTPUT": "memory:",
}

out = processing.run("hausdorff_alts:directed_hausdorff", params)["OUTPUT"]
rows = [(f["direction"], float(f["distance"])) for f in out.getFeatures()]
print(rows)
```

---

## Step 6: Asymmetry Check (Containment)

Use `line_base` vs `line_contained` setup to verify:

- `h(contained, base)` should be `0`
- `h(base, contained)` should be greater than `0`

Implementation note:

- Create temporary single-feature layers for each direction, run with `MODE=0`, `DIRECTED=True`, compare outputs.

---

## Step 7: CRS Validation

Create a target layer in different CRS and run algorithm.

Expected:

- Processing exception: `Source and target layers must use the same CRS`

---

## Step 8: Output Field and Geometry Validation

For any run, assert:

- Fields exist: `distance`, `source_id`, `target_id`, `direction`, `mode`
- `distance >= 0`
- Geometry type is line
- Geometry is not empty/null

Snippet:

```python
for ft in out.getFeatures():
    g = ft.geometry()
    assert g is not None and (not g.isNull()) and (not g.isEmpty())
    assert float(ft["distance"]) >= 0.0
```

---

## Pass Criteria

All are true:

- Algorithm runs from Processing (`hausdorff_alts:directed_hausdorff`)
- Directed and symmetric values match expected reference behavior
- Mode row counts are consistent with mode semantics
- Output schema and geometry are valid
- CRS mismatch is rejected cleanly

---

## Optional MCP Automation

You can run the whole sequence with repeated `mcp_qgis_execute_code` calls and store console outputs in a log markdown file for regression tracking.
