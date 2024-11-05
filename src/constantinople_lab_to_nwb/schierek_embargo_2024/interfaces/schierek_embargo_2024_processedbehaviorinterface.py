"""Primary class for converting experiment-specific behavior."""

from pathlib import Path
from typing import Optional, Union

import numpy as np
from ndx_structured_behavior.utils import loadmat
from neuroconv import BaseDataInterface
from neuroconv.utils import get_base_schema
from pynwb.epoch import TimeIntervals
from pynwb.file import NWBFile


class SchierekEmbargo2024ProcessedBehaviorInterface(BaseDataInterface):
    """Behavior interface for schierek_embargo_2024 conversion"""

    def __init__(
        self,
        file_path: Union[str, Path],
        default_struct_name: str = "S",
        verbose: bool = True,
    ):
        """
        Interface for adding data from the processed behavior file to an existing NWB file.

        Parameters
        ----------
        file_path: Union[str, Path]
            Path to the .mat file containing the processed behavior data.
        default_struct_name: str, optional
            The struct name to load from the .mat file, default is "S".
        """

        self.default_struct_name = default_struct_name
        self._center_port_column_name = "Cled"
        self._side_name_mapping = {"L": "Left", "R": "Right"}
        self._block_name_mapping = {1: "Mixed", 2: "High", 3: "Low"}
        super().__init__(file_path=file_path, verbose=verbose)

    def _read_file(self, file_path: Union[str, Path]) -> dict:
        behavior_data = loadmat(file_path)
        if self.default_struct_name not in behavior_data:
            raise ValueError(f"The struct name '{self.default_struct_name}' not found in {file_path}.")

        return behavior_data[self.default_struct_name]

    def get_metadata_schema(self) -> dict:
        metadata_schema = super().get_metadata_schema()
        metadata_schema["properties"]["Behavior"] = get_base_schema(tag="Behavior")
        metadata_schema["properties"]["Behavior"].update(
            required=["TimeIntervals"],
            properties=dict(
                TimeIntervals=dict(
                    type="object",
                    properties=dict(name=dict(type="string"), description=dict(type="string")),
                )
            ),
        )
        return metadata_schema

    def get_metadata(self) -> dict:
        metadata = super().get_metadata()
        metadata["Behavior"] = dict(
            TimeIntervals=dict(
                name="processed_trials",
                description="Contains the processed Bpod trials.",
            )
        )
        return metadata

    def _get_aligned_center_port_times(self):
        """Get the aligned center port times from the processed behavior data."""
        data = self._read_file(file_path=self.source_data["file_path"])
        if self._center_port_column_name in data:
            return [center_port_times[0] for center_port_times in data[self._center_port_column_name]]
        else:
            raise ValueError(f"'{self._center_port_column_name}' column not found in processed behavior data.")

    def add_to_nwbfile(
        self,
        nwbfile: NWBFile,
        metadata: dict,
        column_name_mapping: Optional[dict] = None,
        column_descriptions: Optional[dict] = None,
        trial_start_times: Optional[list] = None,
        trial_stop_times: Optional[list] = None,
    ) -> None:
        data = self._read_file(file_path=self.source_data["file_path"])

        time_intervals_metadata = metadata["Behavior"]["TimeIntervals"]
        trials_table = TimeIntervals(**time_intervals_metadata)

        if "RewardedSide" in data:
            data["RewardedSide"] = [self._side_name_mapping[side] for side in data["RewardedSide"]]

        if "Block" in data:
            data["Block"] = [self._block_name_mapping[block] for block in data["Block"]]

        columns_with_boolean = ["hits", "vios", "optout"]
        for column in columns_with_boolean:
            if column in data:
                data[column] = list(np.array(data[column]).astype(bool))

        columns_to_add = data.keys()
        if column_name_mapping is not None:
            columns_to_add = [column for column in column_name_mapping.keys() if column in data.keys()]

        num_trials = len(data["NoseInCenter"])
        if nwbfile.trials is None:
            assert trial_start_times is not None, "'trial_start_times' must be provided if trials table is not added."
            assert trial_stop_times is not None, "'trial_stop_times' must be provided if trials table is not added."
            assert (
                len(trial_start_times) == num_trials
            ), f"Length of 'trial_start_times' ({len(trial_start_times)}) must match the number of trials ({num_trials})."
            assert (
                len(trial_stop_times) == num_trials
            ), f"Length of 'trial_stop_times' ({len(trial_stop_times)}) must match the number of trials ({num_trials})."
        else:
            trial_start_times = nwbfile.trials["start_time"][:]
            trial_stop_times = nwbfile.trials["stop_time"][:]

        for start_time, stop_time in zip(trial_start_times, trial_stop_times):
            trials_table.add_row(
                start_time=start_time,
                stop_time=stop_time,
                check_ragged=False,
            )

        # break it into onset and offset time columns
        if self._center_port_column_name in columns_to_add:
            columns_to_add.remove(self._center_port_column_name)
            trials_table.add_column(
                name="center_poke_onset_time",
                description="The time of center port LED on for each trial.",
                data=[center_poke_times[0] for center_poke_times in data[self._center_port_column_name]],
            )
            trials_table.add_column(
                name="center_poke_offset_time",
                description="The time of center port LED off for each trial.",
                data=[center_poke_times[1] for center_poke_times in data[self._center_port_column_name]],
            )

        for column_name in columns_to_add:
            name = column_name_mapping.get(column_name, column_name) if column_name_mapping is not None else column_name
            description = (
                column_descriptions.get(column_name, "no description")
                if column_descriptions is not None
                else "no description"
            )
            trials_table.add_column(
                name=name,
                description=description,
                data=data[column_name],
            )

        nwbfile.add_time_intervals(trials_table)
