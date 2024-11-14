from pathlib import Path

from neuroconv import NWBConverter
from neuroconv.datainterfaces import DeepLabCutInterface, VideoInterface

from constantinople_lab_to_nwb.fiber_photometry.interfaces import (
    DoricFiberPhotometryInterface,
    DoricCsvFiberPhotometryInterface,
)


class FiberPhotometryNWBConverter(NWBConverter):
    """Primary conversion class for converting the Fiber photometry dataset from the Constantinople Lab."""

    data_interface_classes = dict(
        DeepLabCut=DeepLabCutInterface,
        FiberPhotometryDoric=DoricFiberPhotometryInterface,
        FiberPhotometryCsv=DoricCsvFiberPhotometryInterface,
        Video=VideoInterface,
    )
