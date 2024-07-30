"""Primary NWBConverter class for this dataset."""
from neuroconv import NWBConverter
from neuroconv.datainterfaces import (
    OpenEphysRecordingInterface,
    PhySortingInterface,
)


class SchierekEmbargo2024NWBConverter(NWBConverter):
    """Primary conversion class for converting the Neuropixels dataset from the Constantinople Lab."""

    data_interface_classes = dict(
        RecordingAP=OpenEphysRecordingInterface,
        RecordingLFP=OpenEphysRecordingInterface,
        Sorting=PhySortingInterface,
    )
