# QGIS Directed Hausdorff Plugin – Development Guide

## Overview

This document describes how to develop a **QGIS Processing plugin** that computes:

* **Directed Hausdorff distance**
* **Symmetric Hausdorff distance**

between geometries using **discrete sampling (densification)**.

The plugin will also return the **location geometry of the Hausdorff distance** (the pair of points realizing the maximum deviation).

The implementation relies **only on core QGIS libraries and GEOS**.

---

# Actionable Development Steps

Use this section as the build checklist. Each step has a concrete output and a completion condition.

## Step 1: Create Plugin Skeleton

Create the base plugin files and package structure.

Target files:

* `__init__.py`
* `metadata.txt`
* `hausdorff_alts_plugin.py`
* `processing_provider.py`
* `algorithms/directed_hausdorff_algorithm.py`
* `resources.qrc` (optional at first pass)

Implementation tasks:

* Define plugin metadata in `metadata.txt` (name, version, qgisMinimumVersion, author).
* Implement plugin entry point in `__init__.py` using `classFactory`.
* Add provider registration/unregistration in `hausdorff_alts_plugin.py`.
* Implement `QgsProcessingProvider` subclass in `processing_provider.py`.
* Register `DirectedHausdorffAlgorithm` from `algorithms/directed_hausdorff_algorithm.py`.

Done when:

* Plugin appears in QGIS Plugin Manager.
* Processing toolbox shows your provider and one algorithm placeholder.

---

## Step 2: Define Processing Parameters and Outputs

Build the algorithm shell first, before geometry logic.

Implementation tasks:

* Implement `name()`, `displayName()`, `group()`, `groupId()`, `createInstance()`.
* Add parameters:
    * Source layer (`QgsProcessingParameterFeatureSource`)
    * Target layer (`QgsProcessingParameterFeatureSource`)
    * Mode enum (`1-1`, `1-N`, `N-1`, `N-N`)
    * Directed boolean
    * Densification distance (double, min > 0)
    * Maximum candidate neighbors (integer, min 1)
* Define sink output (`QgsProcessingParameterFeatureSink`) with fields:
    * `distance` (double)
    * `source_id` (string or long long)
    * `target_id` (string or long long)
    * optional `direction` (`A_to_B` / `B_to_A` when symmetric mode is requested)
* Set output geometry type to LineString CRS-compatible with source.

Done when:

* Algorithm runs without errors and writes placeholder rows to a sink.

---

## Step 3: Implement Core Geometry Utilities

Create helper methods to keep `processAlgorithm()` readable.

Implementation tasks:

* `sample_geometry_points(geom, step) -> List[QgsPointXY]`
    * Use `geom.densifyByDistance(step)`.
    * Iterate vertices and return sampled points.
* `closest_point_distance(point_xy, geomB) -> (distance, closest_point_xy)`
    * Use `geomB.closestSegmentWithContext(point_xy)`.
* `build_deviation_line(pointA, pointB) -> QgsGeometry`
    * Return `QgsGeometry.fromPolylineXY([pointA, pointB])`.
* Add guard checks for empty/null geometries.

Done when:

* Utility methods pass manual spot checks in QGIS Python console.

---

## Step 4: Implement Directed Hausdorff Function

Implement one robust function and reuse it everywhere.

Recommended function contract:

```python
compute_directed_hausdorff(geomA, geomB, step) -> {
        "distance": float,
        "point_a": QgsPointXY,
        "point_b": QgsPointXY,
        "line": QgsGeometry,
}
```

Implementation tasks:

* Sample points from `geomA`.
* For each sampled point, compute nearest point on `geomB`.
* Track maximum of minimum distances.
* Return both points and deviation line geometry.
* Handle edge cases:
    * empty A or B
    * point geometries
    * zero-length lines

Done when:

* Directed value and line are stable for known simple inputs (identical/parallel/offset).

---

## Step 5: Implement Symmetric Hausdorff

Use two directed calls and select the larger result.

Implementation tasks:

* `hAB = compute_directed_hausdorff(A, B, step)`
* `hBA = compute_directed_hausdorff(B, A, step)`
* Return max distance and associated geometry.
* If `Directed=True`, output only `hAB`.
* If `Directed=False`, output symmetric max and optional direction flag.

Done when:

* Symmetric result equals `max(hAB, hBA)` in test cases.

---

## Step 6: Implement Relationship Modes

Start with correctness, then optimize.

Execution plan:

* Implement `1-1` first.
* Add `1-N` and `N-1` by looping counterpart features.
* Add `N-N` pairwise matrix mode.
* Defer set-to-set union mode until pairwise is stable.

Implementation tasks:

* Build iteration strategy based on mode.
* For each pair, compute directed/symmetric Hausdorff.
* Write one output feature per evaluated pair.
* Report progress via `feedback.setProgress()`.

Done when:

* All four modes run and produce expected row counts.

---

## Step 7: Add Spatial Index and Candidate Filtering

Optimize only after baseline behavior is correct.

Implementation tasks:

* Build `QgsSpatialIndex` for target layer.
* For each source feature, fetch nearest/bbox candidates.
* Limit candidates with `Maximum candidate neighbors`.
* Fallback to full scan if index returns no candidates.

Done when:

* `1-N` and `N-N` runtime improves on medium datasets with same results.

---

## Step 8: Error Handling and Parameter Validation

Implementation tasks:

* Reject non-positive densification distance.
* Reject empty sources/targets for selected mode.
* Skip invalid geometries with warning feedback.
* Ensure CRS compatibility rules are clear:
    * either enforce same CRS
    * or reproject target to source CRS before computation

Done when:

* Algorithm fails fast for invalid setup and continues gracefully for partial invalid features.

---

## Step 9: Build Deterministic Test Dataset and Validation Script

Implementation tasks:

* Create small in-memory or GeoPackage layers for:
    * identical geometries
    * parallel lines
    * constant offset polylines
    * containment/subsegment asymmetry
* Add a repeatable script in `tests/` (or developer script) to run the algorithm and print/assert distances.
* Validate both numeric distance and deviation line endpoints.

Done when:

* All reference cases pass with expected tolerance.

---

## Step 10: Package, Document, and Release

Implementation tasks:

* Update README with:
    * approximation statement
    * parameter guidance for densification
    * performance tradeoffs
* Add usage examples for each mode.
* Bump version in `metadata.txt`.
* Zip plugin for installation test in a fresh QGIS profile.

Done when:

* Plugin installs cleanly and runs from Processing toolbox without local dev assumptions.

---

## Recommended Build Order (Fastest Path)

1. Skeleton/provider registration
2. Algorithm parameters + sink
3. Directed core function
4. Symmetric wrapper
5. Mode loops (`1-1`, then `1-N`, `N-1`, `N-N`)
6. Spatial index optimization
7. Validation dataset + assertions
8. Documentation and packaging

---

## Definition of Done

The plugin is done when all are true:

* Processing algorithm appears and runs in QGIS.
* Directed and symmetric results are numerically correct on reference cases.
* Output includes distance, source/target IDs, and deviation line geometry.
* All requested relationship modes execute with expected row counts.
* Runtime is acceptable on medium input with candidate filtering enabled.
* Documentation clearly states this is a discrete approximation.

---

# Mathematical Definition

## Directed Hausdorff

For geometries (A) and (B):

[
h(A,B) = \max_{a \in A} \min_{b \in B} ||a-b||
]

Interpretation:

1. For each point on (A)
2. compute the distance to geometry (B)
3. keep the **minimum**
4. take the **maximum of those minima**

---

## Symmetric Hausdorff

[
H(A,B) = \max(h(A,B), h(B,A))
]

---

# Algorithm Used (Discrete Approximation)

Because GEOS does not expose continuous Hausdorff optimization, the plugin will compute:

[
h_\epsilon(A,B) =
\max_{a \in S_\epsilon(A)}
\min_{b \in B} ||a-b||
]

Where

```
Sε(A) = sampled points of A
```

Sampling is produced using **densification**.

---

# Plugin Architecture

The plugin should be implemented as a **Processing Algorithm**.

Advantages:

* batch processing
* integration with Model Builder
* scripting compatibility
* GUI integration

Class structure:

```
QgsProcessingAlgorithm
    DirectedHausdorffAlgorithm
```

---

# Inputs

| Parameter                   | Type                  |
| --------------------------- | --------------------- |
| Source layer                | Vector layer          |
| Target layer                | Vector layer          |
| Mode                        | 1-1 / 1-N / N-1 / N-N |
| Directed                    | Boolean               |
| Densification distance      | Float                 |
| Maximum candidate neighbors | Integer               |

---

# Outputs

| Field     | Meaning                          |
| --------- | -------------------------------- |
| distance  | Hausdorff distance               |
| source_id | feature id                       |
| target_id | feature id                       |
| geometry  | line connecting Hausdorff points |

The geometry represents the **Hausdorff location**.

---

# Geometry Sampling

Sampling must include:

* existing vertices
* densified segment points

Use:

```
QgsGeometry.densifyByDistance()
```

Example:

```python
geom = geom.densifyByDistance(step)
```

Then iterate over vertices:

```python
for v in geom.vertices():
```

---

# Directed Hausdorff Algorithm

Pseudo-code:

```
max_distance = 0
argmax_point_A = None
argmin_point_B = None

for point in sampled_points(A):

    distance, closest_point = distance_to_geometry(point, B)

    if distance > max_distance:
        max_distance = distance
        argmax_point_A = point
        argmin_point_B = closest_point
```

---

# Distance Computation

Use the GEOS-powered method:

```
closestSegmentWithContext
```

Example:

```python
dist, _, closest_point, _ = geomB.closestSegmentWithContext(point)
```

This returns:

* minimum distance
* nearest point on geometry

---

# Constructing Hausdorff Geometry

Return a line connecting the two points.

```
QgsGeometry.fromPolylineXY([
    pointA,
    pointB
])
```

This geometry represents the **Hausdorff deviation vector**.

---

# Symmetric Hausdorff Implementation

Compute both directions:

```
hAB = directed(A,B)
hBA = directed(B,A)

return max(hAB, hBA)
```

Return the geometry associated with the larger value.

---

# Relationship Modes

## One → One

Single pair computation.

---

## One → Many

Compute

```
h(A,Bi)
```

for all target features.

Use **spatial index** to limit candidates.

---

## Many → One

Compute

```
h(Ai,B)
```

for all source features.

Output one row per source feature.

---

## Many → Many

Two possible modes:

### Pairwise matrix

Compute all

```
h(Ai,Bj)
```

### Set-to-set

Compute

```
h(union(A), union(B))
```

---

# Performance Considerations

The main cost is:

```
number_of_sample_points × distance_calls
```

Strategies:

## Spatial Index

Use

```
QgsSpatialIndex
```

to filter nearby candidates.

---

## Densification Control

Expose a parameter controlling sampling density.

Too small values will produce very large point sets.

---

## Early Pruning

If bounding box distance exceeds current maximum deviation, skip computation.

---

# Expected Complexity

| Case | Complexity |
| ---- | ---------- |
| 1-1  | O(n)       |
| 1-N  | O(n log N) |
| N-N  | O(N²)      |

Where `n` is number of sampled points.

---

# Limitations

This plugin computes **discrete Hausdorff distance**.

It does **not compute the exact continuous Hausdorff distance** because GEOS does not expose that capability.

Therefore:

```
H_discrete ≤ H_true
```

The result is an **approximation controlled by sampling density**.

---

# Validation Strategy

Test cases should include:

### Parallel lines

Verify midpoint deviation.

---

### Offset polylines

Check that Hausdorff equals offset.

---

### Identical geometries

Distance should be zero.

---

### Subsegment containment

Verify asymmetric Hausdorff.

---

# Estimated Code Size

| Component            | Lines |
| -------------------- | ----- |
| Processing algorithm | ~200  |
| Geometry sampling    | ~80   |
| Distance logic       | ~120  |
| Output handling      | ~80   |

Total expected:

```
~400–500 lines
```

---

# Potential Extensions

Future improvements:

* adaptive densification
* Frechet distance
* visualization of deviation vectors
* batch comparison matrices
* heatmap of deviation along geometry

---

# Summary

The plugin will provide functionality not currently available in QGIS:

* **directed Hausdorff distance**
* **Hausdorff deviation geometry**
* flexible relationship modes

while relying entirely on **core QGIS geometry operations**.

---
