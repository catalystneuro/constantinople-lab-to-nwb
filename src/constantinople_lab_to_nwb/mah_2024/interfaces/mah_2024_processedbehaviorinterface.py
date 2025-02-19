"""Primary class for converting experiment-specific behavior."""

from pathlib import Path
from typing import Optional, Union

import numpy as np
import pandas as pd
from ndx_structured_behavior.utils import loadmat
from neuroconv import BaseDataInterface
from neuroconv.utils import get_base_schema, DeepDict
from pynwb.epoch import TimeIntervals
from pynwb.file import NWBFile


class Mah2024ProcessedBehaviorInterface(BaseDataInterface):
    """Behavior interface for mah_2024 conversion"""

    def __init__(
        self,
        file_path: Union[str, Path],
        date_index: int,
        default_struct_name: str = "A",
        verbose: bool = True,
    ):
        """
        Interface for adding data from the processed behavior file to an existing NWB file.

        Parameters
        ----------
        file_path: Union[str, Path]
            Path to the .mat file containing the processed behavior data.
        date_index: int
            The row index of the date in the .mat file.
        default_struct_name: str, optional
            The struct name to load from the .mat file, default is "A".
        """

        self.default_struct_name = default_struct_name
        self.date_index = date_index
        self._side_name_mapping = {"L": "Left", "R": "Right"}
        self._block_name_mapping = {1: "Mixed", 2: "High", 3: "Low"}
        super().__init__(file_path=file_path, verbose=verbose)

    def _read_file(self, file_path: Union[str, Path]) -> pd.DataFrame:
        behavior_data = loadmat(file_path)
        if self.default_struct_name not in behavior_data:
            raise ValueError(f"The struct name '{self.default_struct_name}' not found in {file_path}.")

        behavior_data = behavior_data[self.default_struct_name]
        if "date" not in behavior_data:
            raise ValueError(f"Date not found in {file_path}.")

        dataframe = self._transform_data(data=behavior_data)

        return dataframe

    def _transform_data(self, data: dict) -> pd.DataFrame:
        """
        Transform the data from the .mat file into a DataFrame.
        """
        if "ntrials" not in data:
            raise ValueError("The 'ntrials' key is missing from the data.")
        num_trials = data["ntrials"]
        # Calculate start and stop indices
        start_indices = np.concatenate(([0], np.cumsum(num_trials)[:-1])).astype(int)
        stop_indices = np.cumsum(num_trials).astype(int)

        start = start_indices[self.date_index]
        stop = stop_indices[self.date_index]

        num_all_trials = int(np.sum(num_trials))
        column_names = list(data.keys())

        columns_with_arrays = [
            column for column in column_names if isinstance(data[column], list) and len(data[column]) == num_all_trials
        ]
        # Create DataFrame with relevant columns
        dataframe = pd.DataFrame({column_name: data[column_name][start:stop] for column_name in columns_with_arrays})

        # Add side
        if "side" in data:
            side = np.array([side_char for side_char in data["side"]])
            side_to_add = side[start:stop]
            dataframe["side"] = side_to_add

        if "wait_thresh" in data:
            dataframe["wait_thresh"] = [data["wait_thresh"]] * len(dataframe)

        return dataframe

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

    def add_to_nwbfile(
        self,
        nwbfile: NWBFile,
        metadata: dict,
        column_name_mapping: Optional[dict] = None,
        column_descriptions: Optional[dict] = None,
        trial_start_times: Optional[list] = None,
        trial_stop_times: Optional[list] = None,
    ) -> None:
        dataframe = self._read_file(file_path=self.source_data["file_path"])

        time_intervals_metadata = metadata["Behavior"]["TimeIntervals"]
        trials_table = TimeIntervals(**time_intervals_metadata)

        if "side" in dataframe.columns:
            dataframe["side"] = dataframe["side"].map(self._side_name_mapping)

        if "block" in dataframe.columns:
            dataframe["block"] = dataframe["block"].map(self._block_name_mapping)

        columns_with_boolean = ["catch", "hits", "vios", "optout"]
        for column in columns_with_boolean:
            if column in dataframe.columns:
                dataframe[column] = dataframe[column].astype(bool)

        columns_to_add = dataframe.columns
        if column_name_mapping is not None:
            columns_to_add = [column for column in column_name_mapping.keys() if column in dataframe.columns]

        num_trials = len(dataframe)
        if nwbfile.trials is None:
            assert (
                trial_start_times is not None
            ), "'trial_start_times' must be provided if trials table is not in acquisition."
            assert (
                trial_stop_times is not None
            ), "'trial_stop_times' must be provided if trials table is not in acquisition."
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
                data=dataframe[column_name].values.tolist(),
            )

        nwbfile.add_time_intervals(trials_table)
