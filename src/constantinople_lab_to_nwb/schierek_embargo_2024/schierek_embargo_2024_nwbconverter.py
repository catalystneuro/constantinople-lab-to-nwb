"""Primary NWBConverter class for this dataset."""

from typing import Optional, Dict, List
from warnings import warn

import numpy as np
from pynwb import NWBFile
from neuroconv import NWBConverter
from neuroconv.datainterfaces import (
    OpenEphysRecordingInterface,
    PhySortingInterface,
)
from neuroconv.utils import FilePathType
from probeinterface import read_probeinterface, Probe

from constantinople_lab_to_nwb.general_interfaces import BpodBehaviorInterface
from constantinople_lab_to_nwb.utils import add_optogenetics_series

from constantinople_lab_to_nwb.schierek_embargo_2024.interfaces import (
    SchierekEmbargo2024SortingInterface,
    SchierekEmbargo2024ProcessedBehaviorInterface,
)


class SchierekEmbargo2024NWBConverter(NWBConverter):
    """Primary conversion class for converting the Neuropixels dataset from the Constantinople Lab."""

    data_interface_classes = dict(
        RecordingAP=OpenEphysRecordingInterface,
        RecordingLFP=OpenEphysRecordingInterface,
        PhySorting=PhySortingInterface,
        ProcessedSorting=SchierekEmbargo2024SortingInterface,
        RawBehavior=BpodBehaviorInterface,
        ProcessedBehavior=SchierekEmbargo2024ProcessedBehaviorInterface,
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

    def _set_electrode_properties_for_recording_interface(self, recording_interface: str):
        """
        Set the electrode properties retrieved from the processed sorting interface for the recording interface.

        Parameters
        ----------
        recording_interface: str
            The name of the recording interface.
        """
        recording_extractor = self.data_interface_objects[recording_interface].recording_extractor
        sorting_extractor = self.data_interface_objects["ProcessedSorting"].sorting_extractor
        electrode_properties = sorting_extractor._electrode_properties

        # TODO confirm channel indices match to channel info from sorting
        channel_ids = sorting_extractor.get_property("ch")
        channel_ids = list(channel_ids)
        for property_name in electrode_properties:
            property_values = electrode_properties[property_name]
            missing_value = "unknown" if property_name == "brain_area" else np.nan
            channel_indices_from_recording = recording_extractor.ids_to_indices()
            values_to_add = [
                property_values[channel_ids.index(i)] if i in channel_ids else missing_value
                for i in channel_indices_from_recording
            ]
            recording_extractor.set_property(property_name, values_to_add)

    def __init__(
        self,
        source_data: Dict[str, dict],
        probe_group_file_path: Optional[FilePathType] = None,
        probe_properties: Optional[List[str]] = None,
        verbose: bool = True,
    ):

        super().__init__(source_data=source_data, verbose=verbose)

        for recording_interface_name in ["RecordingAP", "RecordingLFP"]:
            if "ProcessedSorting" in self.data_interface_objects:
                self._set_electrode_properties_for_recording_interface(recording_interface_name)

            if probe_group_file_path is not None:
                probe_group = read_probeinterface(file=probe_group_file_path)
                if len(probe_group.probes) == 1:
                    probe = probe_group.probes[0]
                    # Add probe information to the recording interfaces
                    self._set_probe_properties_for_recording_interface(
                        probe=probe,
                        properties_to_add=probe_properties,
                        recording_interface=recording_interface_name,
                    )

    def get_metadata(self):
        metadata = super().get_metadata()

        # Explicity set session_start_time to Bpod start time
        session_start_time = self.data_interface_objects["RawBehavior"].get_metadata()["NWBFile"]["session_start_time"]
        metadata["NWBFile"].update(session_start_time=session_start_time)

        if "Electrodes" not in metadata["Ecephys"]:
            metadata["Ecephys"]["Electrodes"] = []

        metadata["Ecephys"]["Electrodes"].extend(
            [
                dict(
                    name="channel_depth_um",
                    description="The distance of the channel from the tip of the neuropixels probe in micrometers.",
                ),
                dict(name="distance_from_L1_um", description="The distance from L1 in micrometers."),
                dict(
                    name="x",
                    description="The anterior/posterior neuropixels probe location relative to Bregma in micrometers.",
                ),
                dict(
                    name="y",
                    description="The medial/lateral neuropixels probe location relative to Bregma in micrometers.",
                ),
                dict(
                    name="z",
                    description="The dorsal/ventral neuropixels probe location relative to Bregma in micrometers.",
                ),
            ]
        )

        return metadata

    def temporally_align_data_interfaces(self):
        processed_behavior_interface = self.data_interface_objects["ProcessedBehavior"]
        center_port_aligned_times = processed_behavior_interface._get_aligned_center_port_times()

        raw_behavior_interface = self.data_interface_objects["RawBehavior"]
        trial_start_times_from_bpod, _ = raw_behavior_interface.get_trial_times()
        bpod_first_trial_start_time = trial_start_times_from_bpod[0]
        time_shift = bpod_first_trial_start_time - center_port_aligned_times[0]

        recording_interface_names = [
            interface_name for interface_name in self.data_interface_objects if "Recording" in interface_name
        ]

        for recording_interface_name in recording_interface_names:
            recording_interface = self.data_interface_objects[recording_interface_name]
            unaligned_timestamps = recording_interface.get_timestamps()
            unaligned_starting_time = unaligned_timestamps[0]
            if unaligned_starting_time + time_shift < 0:
                raise ValueError("The recording aligned starting time should not be negative.")
            recording_interface.set_aligned_starting_time(aligned_starting_time=time_shift)

        sorting_interface_names = [
            interface_name for interface_name in self.data_interface_objects if "Sorting" in interface_name
        ]
        for sorting_interface_name in sorting_interface_names:
            sorting_interface = self.data_interface_objects[sorting_interface_name]
            sorting_interface.register_recording(self.data_interface_objects[recording_interface_names[0]])

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata, conversion_options: Optional[dict] = None) -> None:
        super().add_to_nwbfile(nwbfile=nwbfile, metadata=metadata, conversion_options=conversion_options)

        add_optogenetics_series(nwbfile=nwbfile, metadata=metadata)
