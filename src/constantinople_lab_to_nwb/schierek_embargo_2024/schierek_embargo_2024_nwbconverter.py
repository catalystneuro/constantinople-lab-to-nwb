"""Primary NWBConverter class for this dataset."""
from neuroconv import NWBConverter
from neuroconv.datainterfaces import (
    SpikeGLXRecordingInterface,
    PhySortingInterface,
)

from constantinople_lab_to_nwb.schierek_embargo_2024 import SchierekEmbargo2024BehaviorInterface


class SchierekEmbargo2024NWBConverter(NWBConverter):
    """Primary conversion class for my extracellular electrophysiology dataset."""

    data_interface_classes = dict(
        Recording=SpikeGLXRecordingInterface,
        Sorting=PhySortingInterface,
        Behavior=SchierekEmbargo2024BehaviorInterface,
    )
