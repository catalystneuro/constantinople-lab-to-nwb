from typing import Optional

from neuroconv import NWBConverter
from pynwb import NWBFile

from constantinople_lab_to_nwb.general_interfaces import BpodBehaviorInterface
from constantinople_lab_to_nwb.optogenetics.utils import add_optogenetics_series


class OptogeneticsNWBConverter(NWBConverter):
    """Primary conversion class for converting the optogenetics dataset from the Constantinople Lab."""

    data_interface_classes = dict(
        Behavior=BpodBehaviorInterface,
    )

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata, conversion_options: Optional[dict] = None) -> None:
        super().add_to_nwbfile(nwbfile=nwbfile, metadata=metadata, conversion_options=conversion_options)

        add_optogenetics_series(nwbfile=nwbfile, metadata=metadata)
