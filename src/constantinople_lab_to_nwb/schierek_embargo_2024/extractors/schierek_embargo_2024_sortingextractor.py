from typing import Optional, List

import numpy as np
from pymatreader import read_mat
from spikeinterface import BaseSorting, BaseSortingSegment

from pydantic import FilePath


def _get_electrode_properties(units_data: List[dict], num_units: int, properties_mapping: dict):
    properties = dict()
    for property_name, renamed_property_name in properties_mapping.items():
        property_values = [
            units_data[i][property_name] if property_name in units_data[i] and units_data[i][property_name] else np.nan
            for i in range(num_units)
        ]
        if any(value is not np.nan for value in property_values):
            properties.update({renamed_property_name: property_values})
    return properties


class SchierekEmbargo2024SortingExtractor(BaseSorting):
    extractor_name = "SchierekEmbargo2024Sorting"
    name = "schierekembargo2024"

    def __init__(self, file_path: FilePath, sampling_frequency: float):
        units_data = read_mat(file_path)
        assert "SU" in units_data, f"The 'SU' structure is missing from '{file_path}'."

        num_units = len(units_data["SU"])
        unit_ids = np.arange(num_units)

        super().__init__(sampling_frequency=sampling_frequency, unit_ids=unit_ids)

        spike_times = []
        for unit in units_data["SU"]:
            spike_times.append(unit["st"])

        sorting_segment = SchierekEmbargo2024SortingSegment(
            sampling_frequency=sampling_frequency,
            spike_times=spike_times,
        )
        self.add_sorting_segment(sorting_segment)

        cluster_ids = [units_data["SU"][i]["cluster_id"] for i in range(num_units)]
        # Rename to 'original_cluster_id' to match Phy output
        self.set_property(key="original_cluster_id", values=cluster_ids)

        # rec_channel is 1-based
        channel_ids = [units_data["SU"][i]["rec_channel"] - 1 for i in range(num_units)]
        # Rename to 'ch' to match Phy output
        self.set_property(key="ch", values=channel_ids)

        electrode_properties_mapping = dict(
            channel_depth="channel_depth_um",
            location="brain_area",
            umDistFromL1="distance_from_L1_um",
            AP="x",
            ML="y",
            DV="z",
        )
        self._electrode_properties = _get_electrode_properties(
            units_data["SU"], num_units, electrode_properties_mapping
        )


class SchierekEmbargo2024SortingSegment(BaseSortingSegment):
    def __init__(self, sampling_frequency: float, spike_times: List[np.ndarray]):
        BaseSortingSegment.__init__(self)
        self._spike_times = spike_times
        self._sampling_frequency = sampling_frequency

    def get_unit_spike_train(
        self,
        unit_id: int,
        start_frame: Optional[int] = None,
        end_frame: Optional[int] = None,
    ) -> np.ndarray:
        times = self._spike_times[unit_id]
        frames = (times * self._sampling_frequency).astype(int)
        if start_frame is not None:
            frames = frames[frames >= start_frame]
        if end_frame is not None:
            frames = frames[frames < end_frame]
        return frames
