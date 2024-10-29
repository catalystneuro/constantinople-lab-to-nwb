from neuroconv import NWBConverter

from constantinople_lab_to_nwb.general_interfaces import BpodBehaviorInterface
from constantinople_lab_to_nwb.mah_2024.interfaces import Mah2024ProcessedBehaviorInterface


class Mah2024NWBConverter(NWBConverter):
    """Primary conversion class for converting the Behavior dataset from the Constantinople Lab."""

    data_interface_classes = dict(
        RawBehavior=BpodBehaviorInterface,
        ProcessedBehavior=Mah2024ProcessedBehaviorInterface,
    )
