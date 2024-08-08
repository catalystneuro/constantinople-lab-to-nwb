"""Primary class for converting experiment-specific behavior."""
from datetime import datetime
from pathlib import Path
from typing import Optional
from warnings import warn

import numpy as np
import pandas as pd
from pymatreader import read_mat
from pynwb.file import NWBFile

from neuroconv.datainterfaces.text.timeintervalsinterface import TimeIntervalsInterface
from neuroconv.utils import DeepDict, FilePathType


def _transform_data(data: dict, session_index: int) -> pd.DataFrame:
    """
    Transform the data from the .mat file into a DataFrame.
    """
    if "ntrials" not in data:
        raise ValueError("The 'ntrials' key is missing from the data.")
    num_trials = data["ntrials"]
    # Calculate start and stop indices
    start_indices = np.concatenate(([0], np.cumsum(num_trials)[:-1])).astype(int)
    stop_indices = np.cumsum(num_trials).astype(int)

    start = start_indices[session_index]
    stop = stop_indices[session_index]

    num_all_trials = int(np.sum(num_trials))
    column_names = list(data.keys())

    columns_with_arrays = [column for column in column_names if isinstance(data[column], np.ndarray) and len(data[column]) == num_all_trials]
    # Create DataFrame with relevant columns
    dataframe = pd.DataFrame({column_name: data[column_name][start:stop] for column_name in columns_with_arrays})

    # Add side
    if "side" in data:
        side = np.array([side_char for side_char in data["side"]])
        side_to_add = side[start:stop]
        dataframe["side"] = side_to_add

    if "wait_thresh" in data:
        dataframe["wait_thresh"] = data["wait_thresh"] * len(dataframe)

    columns_with_integers = ["trial_num", "trainingstage", "test_block", "block", "adapt_block"]
    for column in columns_with_integers:
        if column in data:
            dataframe[column] = data[column][start:stop].astype(int)

    return dataframe


class MahEmbargo2024BehaviorInterface(TimeIntervalsInterface):
    """Behavior interface for mah_embargo_2024 conversion"""

    keywords = ["behavior"]

    def __init__(
            self,
            file_path: FilePathType,
            date: str,
            sampling_frequency: float,
            default_struct_name: str = "A",
            verbose: bool = True,
    ):

        self.default_struct_name = default_struct_name
        self.date = date
        super().__init__(file_path=file_path, verbose=verbose)

        self.dataframe["start_time"] = np.arange(0, len(self.dataframe)) / sampling_frequency

    def _read_file(self, file_path: FilePathType, **read_kwargs):
        behavior_data = read_mat(file_path)
        if self.default_struct_name not in behavior_data:
            raise ValueError(f"The struct name '{self.default_struct_name}' not found in {file_path}.")

        behavior_data = behavior_data[self.default_struct_name]
        if "date" not in behavior_data:
            raise ValueError(f"Date not found in {file_path}.")
        if self.date not in behavior_data["date"]:
            raise ValueError(f"Date '{self.date}' not found in {file_path}.")

        session_index = behavior_data["date"].index(self.date)
        dataframe = _transform_data(data=behavior_data, session_index=session_index)

        return dataframe

    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()

        file_name = Path(self.source_data["file_path"]).stem
        subject_id = file_name.split("_")[-1]
        session_id = f"{subject_id}-{self.date}"
        metadata["NWBFile"].update(session_id=session_id)
        metadata["Subject"].update(subject_id=subject_id)
        try:
            session_start_time = datetime.strptime(self.date, "%d-%b-%Y")
            metadata["NWBFile"].update(session_start_time=session_start_time)
        except ValueError:
            warn(f"Could not parse date '{self.date}' to datetime. "
                 "Please update the session_start_time manually: metadata['NWBFile']['session_start_time'] = 'YYYY-MM-DD HH:MM:SS'.")

        return metadata
