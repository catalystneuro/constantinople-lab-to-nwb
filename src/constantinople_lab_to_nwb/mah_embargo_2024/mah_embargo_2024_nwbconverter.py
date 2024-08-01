from neuroconv import NWBConverter

from constantinople_lab_to_nwb.mah_embargo_2024.interfaces import MahEmbargo2024BehaviorInterface


class MahEmbargo2024NWBConverter(NWBConverter):
    """Primary conversion class for converting the Behavior dataset from the Constantinople Lab."""

    data_interface_classes = dict(
        Behavior=MahEmbargo2024BehaviorInterface,
    )
