from qgis.core import QgsApplication

from .processing_provider import HausdorffAltsProvider


class HausdorffAltsPlugin:
    def __init__(self):
        self.provider = None

    def initGui(self):
        self.provider = HausdorffAltsProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self):
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
