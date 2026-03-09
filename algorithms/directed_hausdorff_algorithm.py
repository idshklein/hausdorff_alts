from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsFeature,
    QgsFields,
    QgsField,
    QgsGeometry,
    QgsPointXY,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterNumber,
    QgsSpatialIndex,
    QgsWkbTypes,
)


class DirectedHausdorffAlgorithm(QgsProcessingAlgorithm):
    SOURCE = "SOURCE"
    TARGET = "TARGET"
    MODE = "MODE"
    DIRECTED = "DIRECTED"
    BOTH_DIRECTIONS = "BOTH_DIRECTIONS"
    DENSIFY_STEP = "DENSIFY_STEP"
    MAX_NEIGHBORS = "MAX_NEIGHBORS"
    OUTPUT = "OUTPUT"

    MODE_1_TO_1 = 0
    MODE_1_TO_N = 1
    MODE_N_TO_1 = 2
    MODE_N_TO_N = 3

    def name(self):
        return "directed_hausdorff"

    def displayName(self):
        return "Directed/Symmetric Hausdorff (Discrete)"

    def group(self):
        return "Hausdorff"

    def groupId(self):
        return "hausdorff"

    def shortHelpString(self):
        return (
            "Computes discrete directed or symmetric Hausdorff distance between features "
            "using densified sampling. Output geometries are deviation vectors. "
            "Enable 'Both directions' to always output A->B and B->A as separate lines."
        )

    def createInstance(self):
        return DirectedHausdorffAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.SOURCE,
                "Source layer",
                [QgsProcessing.TypeVectorAnyGeometry],
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.TARGET,
                "Target layer",
                [QgsProcessing.TypeVectorAnyGeometry],
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.MODE,
                "Relationship mode",
                options=["1-1", "1-N", "N-1", "N-N"],
                defaultValue=self.MODE_1_TO_1,
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.DIRECTED,
                "Directed (unchecked = symmetric)",
                defaultValue=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.BOTH_DIRECTIONS,
                "Both directions (output two lines: A_to_B and B_to_A)",
                defaultValue=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.DENSIFY_STEP,
                "Densification distance",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=1.0,
                minValue=0.0000001,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.MAX_NEIGHBORS,
                "Maximum candidate neighbors (for 1-N and N-N)",
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=20,
                minValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                "Hausdorff output",
                type=QgsProcessing.TypeVectorLine,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.SOURCE, context)
        target = self.parameterAsSource(parameters, self.TARGET, context)
        mode = self.parameterAsEnum(parameters, self.MODE, context)
        directed = self.parameterAsBool(parameters, self.DIRECTED, context)
        both_directions = self.parameterAsBool(parameters, self.BOTH_DIRECTIONS, context)
        densify_step = self.parameterAsDouble(parameters, self.DENSIFY_STEP, context)
        max_neighbors = self.parameterAsInt(parameters, self.MAX_NEIGHBORS, context)

        if source is None:
            raise QgsProcessingException("Invalid source layer")
        if target is None:
            raise QgsProcessingException("Invalid target layer")
        if both_directions and not directed:
            raise QgsProcessingException(
                "Invalid parameter combination: 'Both directions' requires 'Directed' to be checked"
            )
        if densify_step <= 0:
            raise QgsProcessingException("Densification distance must be greater than zero")
        if source.sourceCrs() != target.sourceCrs():
            raise QgsProcessingException(
                "Source and target layers must use the same CRS"
            )

        out_fields = QgsFields()
        out_fields.append(QgsField("distance", QVariant.Double))
        out_fields.append(QgsField("source_id", QVariant.String))
        out_fields.append(QgsField("target_id", QVariant.String))
        out_fields.append(QgsField("direction", QVariant.String))
        out_fields.append(QgsField("mode", QVariant.String))

        sink, sink_id = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            out_fields,
            QgsWkbTypes.LineString,
            source.sourceCrs(),
        )
        if sink is None:
            raise QgsProcessingException("Failed to create output sink")

        source_features = [f for f in source.getFeatures() if self._valid_geom_feature(f)]
        target_features = [f for f in target.getFeatures() if self._valid_geom_feature(f)]

        if not source_features:
            raise QgsProcessingException("Source layer has no valid geometries")
        if not target_features:
            raise QgsProcessingException("Target layer has no valid geometries")

        spatial_index = QgsSpatialIndex()
        for target_feature in target_features:
            spatial_index.addFeature(target_feature)
        target_by_id = {f.id(): f for f in target_features}

        pair_count = 0
        mode_text = ["1-1", "1-N", "N-1", "N-N"][mode]

        if mode == self.MODE_1_TO_1:
            pair_count += self._compute_pair(
                source_features[0],
                target_features[0],
                directed,
                both_directions,
                densify_step,
                mode_text,
                sink,
                out_fields,
            )

        elif mode == self.MODE_1_TO_N:
            src_feature = source_features[0]
            candidates = self._candidate_targets(
                src_feature.geometry(), target_features, target_by_id, spatial_index, max_neighbors
            )
            for tgt_feature in candidates:
                if feedback.isCanceled():
                    break
                pair_count += self._compute_pair(
                    src_feature,
                    tgt_feature,
                    directed,
                    both_directions,
                    densify_step,
                    mode_text,
                    sink,
                    out_fields,
                )

        elif mode == self.MODE_N_TO_1:
            tgt_feature = target_features[0]
            total = len(source_features)
            for i, src_feature in enumerate(source_features):
                if feedback.isCanceled():
                    break
                pair_count += self._compute_pair(
                    src_feature,
                    tgt_feature,
                    directed,
                    both_directions,
                    densify_step,
                    mode_text,
                    sink,
                    out_fields,
                )
                feedback.setProgress(int((i + 1) * 100 / max(1, total)))

        elif mode == self.MODE_N_TO_N:
            total = len(source_features)
            for i, src_feature in enumerate(source_features):
                if feedback.isCanceled():
                    break
                candidates = self._candidate_targets(
                    src_feature.geometry(), target_features, target_by_id, spatial_index, max_neighbors
                )
                for tgt_feature in candidates:
                    if feedback.isCanceled():
                        break
                    pair_count += self._compute_pair(
                        src_feature,
                        tgt_feature,
                        directed,
                        both_directions,
                        densify_step,
                        mode_text,
                        sink,
                        out_fields,
                    )
                feedback.setProgress(int((i + 1) * 100 / max(1, total)))

        return {self.OUTPUT: sink_id, "PAIRS": pair_count}

    def _valid_geom_feature(self, feature):
        geom = feature.geometry()
        return geom is not None and not geom.isNull() and not geom.isEmpty()

    def _candidate_targets(self, src_geom, all_targets, target_by_id, spatial_index, max_neighbors):
        if max_neighbors <= 0 or max_neighbors >= len(all_targets):
            return all_targets

        center = src_geom.boundingBox().center()
        candidate_ids = spatial_index.nearestNeighbor(QgsPointXY(center), max_neighbors)
        if not candidate_ids:
            return all_targets

        candidates = []
        for fid in candidate_ids:
            feat = target_by_id.get(fid)
            if feat is not None:
                candidates.append(feat)

        return candidates if candidates else all_targets

    def _compute_pair(self, src_feature, tgt_feature, directed, both_directions, step, mode_text, sink, out_fields):
        src_geom = src_feature.geometry()
        tgt_geom = tgt_feature.geometry()

        if both_directions:
            result_ab = self._compute_directed_hausdorff(src_geom, tgt_geom, step)
            result_ba = self._compute_directed_hausdorff(tgt_geom, src_geom, step)
            if result_ab is None or result_ba is None:
                return 0

            self._write_output(
                sink,
                result_ab,
                src_feature.id(),
                tgt_feature.id(),
                "A_to_B",
                mode_text,
                out_fields,
            )
            self._write_output(
                sink,
                result_ba,
                src_feature.id(),
                tgt_feature.id(),
                "B_to_A",
                mode_text,
                out_fields,
            )
            return 2

        if directed:
            result = self._compute_directed_hausdorff(src_geom, tgt_geom, step)
            if result is None:
                return 0
            self._write_output(
                sink,
                result,
                src_feature.id(),
                tgt_feature.id(),
                "A_to_B",
                mode_text,
                out_fields,
            )
            return 1

        result_ab = self._compute_directed_hausdorff(src_geom, tgt_geom, step)
        result_ba = self._compute_directed_hausdorff(tgt_geom, src_geom, step)
        if result_ab is None or result_ba is None:
            return 0

        if result_ab["distance"] >= result_ba["distance"]:
            self._write_output(
                sink,
                result_ab,
                src_feature.id(),
                tgt_feature.id(),
                "A_to_B",
                mode_text,
                out_fields,
            )
        else:
            # Keep source/target ids fixed for row identity but report direction.
            self._write_output(
                sink,
                result_ba,
                src_feature.id(),
                tgt_feature.id(),
                "B_to_A",
                mode_text,
                out_fields,
            )
        return 1

    def _write_output(self, sink, result, source_id, target_id, direction, mode_text, out_fields):
        out_feature = QgsFeature()
        out_feature.setFields(out_fields, initAttributes=True)
        out_feature.setGeometry(result["line"])
        out_feature["distance"] = float(result["distance"])
        out_feature["source_id"] = str(source_id)
        out_feature["target_id"] = str(target_id)
        out_feature["direction"] = direction
        out_feature["mode"] = mode_text
        sink.addFeature(out_feature)

    def _compute_directed_hausdorff(self, geom_a, geom_b, step):
        sample_points = self._sample_geometry_points(geom_a, step)
        if not sample_points:
            return None

        max_distance = -1.0
        argmax_a = None
        argmin_b = None

        for point_a in sample_points:
            distance, point_b = self._closest_point_distance(point_a, geom_b)
            if point_b is None:
                continue
            if distance > max_distance:
                max_distance = distance
                argmax_a = point_a
                argmin_b = point_b

        if argmax_a is None or argmin_b is None:
            return None

        return {
            "distance": max_distance,
            "point_a": argmax_a,
            "point_b": argmin_b,
            "line": QgsGeometry.fromPolylineXY([argmax_a, argmin_b]),
        }

    def _sample_geometry_points(self, geom, step):
        if geom is None or geom.isNull() or geom.isEmpty():
            return []

        densified = geom.densifyByDistance(step)
        points = []
        for vertex in densified.vertices():
            points.append(QgsPointXY(vertex))

        return points

    def _closest_point_distance(self, point_xy, geom_b):
        point_geom = QgsGeometry.fromPointXY(point_xy)
        closest_geom = geom_b.nearestPoint(point_geom)
        if closest_geom is None or closest_geom.isNull() or closest_geom.isEmpty():
            return 0.0, None

        closest_point = closest_geom.asPoint()
        closest_point_xy = QgsPointXY(closest_point)
        distance = point_geom.distance(closest_geom)
        return float(distance), closest_point_xy
