from qgis.core import QgsProcessingProvider

from .algorithms.directed_hausdorff_algorithm import DirectedHausdorffAlgorithm


class HausdorffAltsProvider(QgsProcessingProvider):
    def id(self):
        return "hausdorff_alts"

    def name(self):
        return "Hausdorff Alts"

    def longName(self):
        return self.name()

    def loadAlgorithms(self):
        self.addAlgorithm(DirectedHausdorffAlgorithm())
