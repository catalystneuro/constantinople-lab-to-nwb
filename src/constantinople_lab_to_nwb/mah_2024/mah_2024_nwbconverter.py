from neuroconv import NWBConverter

from constantinople_lab_to_nwb.mah_2024.interfaces import Mah2024BpodInterface, Mah2024ProcessedBehaviorInterface


class Mah2024NWBConverter(NWBConverter):
    """Primary conversion class for converting the Behavior dataset from the Constantinople Lab."""

    data_interface_classes = dict(
        RawBehavior=Mah2024BpodInterface,
        ProcessedBehavior=Mah2024ProcessedBehaviorInterface,
    )
