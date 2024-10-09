from pathlib import Path

from neuroconv import NWBConverter
from neuroconv.datainterfaces import DeepLabCutInterface, VideoInterface

from constantinople_lab_to_nwb.fiber_photometry.interfaces import (
    DoricFiberPhotometryInterface,
    DoricCsvFiberPhotometryInterface,
)
from constantinople_lab_to_nwb.general_interfaces import BpodBehaviorInterface


class FiberPhotometryNWBConverter(NWBConverter):
    """Primary conversion class for converting the Fiber photometry dataset from the Constantinople Lab."""

    data_interface_classes = dict(
        DeepLabCut=DeepLabCutInterface,
        Video=VideoInterface,
        Behavior=BpodBehaviorInterface,
    )

    def __init__(self, source_data: dict[str, dict], verbose: bool = True):
        """Validate source_data against source_schema and initialize all data interfaces."""
        fiber_photometry_source_data = source_data["FiberPhotometry"]
        fiber_photometry_file_path = Path(fiber_photometry_source_data["file_path"])
        if fiber_photometry_file_path.suffix == ".doric":
            self.data_interface_classes["FiberPhotometry"] = DoricFiberPhotometryInterface
        elif fiber_photometry_file_path.suffix == ".csv":
            self.data_interface_classes["FiberPhotometry"] = DoricCsvFiberPhotometryInterface
        super().__init__(source_data=source_data, verbose=verbose)
