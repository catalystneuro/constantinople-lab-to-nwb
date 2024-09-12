"""Primary NWBConverter class for this dataset."""

from typing import Optional, Dict, List
from warnings import warn

import numpy as np
from neuroconv import NWBConverter
from neuroconv.datainterfaces import (
    OpenEphysRecordingInterface,
    PhySortingInterface,
)
from neuroconv.utils import FilePathType
from probeinterface import read_probeinterface, Probe
from pynwb import NWBFile


class SchierekEmbargo2024NWBConverter(NWBConverter):
    """Primary conversion class for converting the Neuropixels dataset from the Constantinople Lab."""

    data_interface_classes = dict(
        RecordingAP=OpenEphysRecordingInterface,
        RecordingLFP=OpenEphysRecordingInterface,
        PhySorting=PhySortingInterface,
    )

    def _set_probe_properties_for_recording_interface(
        self,
        probe: Probe,
        properties_to_add: List[str],
        recording_interface: str,
    ):
        """
        Set the probe properties for the recording interface.

        Parameters
        ----------
        probe : Probe
            The probe object from probeinterface.
        properties_to_add : List[str]
            The properties to add to the recording interface.
        recording_interface : str
            The name of the recording interface.
        """
        recording_interface = self.data_interface_objects[recording_interface]
        recording_interface.set_probe(probe=probe, group_mode="by_probe")
        recording_extractor = recording_interface.recording_extractor
        contact_vector = recording_extractor.get_property("contact_vector")
        if contact_vector is not None:
            for property_name in properties_to_add:
                try:
                    recording_extractor.set_property(property_name, contact_vector[property_name])
                except ValueError:
                    warn(f"Property '{property_name}' not found in probe contact vector.", UserWarning)

    def __init__(
        self,
        source_data: Dict[str, dict],
        probe_group_file_path: Optional[FilePathType] = None,
        probe_properties: Optional[List[str]] = None,
        verbose: bool = True,
    ):

        super().__init__(source_data=source_data, verbose=verbose)

        if probe_group_file_path is not None:
            probe_group = read_probeinterface(file=probe_group_file_path)
            if len(probe_group.probes) == 1:
                probe = probe_group.probes[0]
                # Add probe information to the recording interfaces
                for recording_interface_name in ["RecordingAP", "RecordingLFP"]:
                    self._set_probe_properties_for_recording_interface(
                        probe=probe,
                        properties_to_add=probe_properties,
                        recording_interface=recording_interface_name,
                    )
