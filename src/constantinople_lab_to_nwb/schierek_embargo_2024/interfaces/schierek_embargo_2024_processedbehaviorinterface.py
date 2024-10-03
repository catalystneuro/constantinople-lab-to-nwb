"""Primary class for converting experiment-specific behavior."""

from pathlib import Path
from typing import Optional, Union

import numpy as np
from warnings import warn
from ndx_structured_behavior.utils import loadmat
from neuroconv import BaseDataInterface
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
            The struct name to load from the .mat file, default is "A".
        """

        self.default_struct_name = default_struct_name
        super().__init__(file_path=file_path, verbose=verbose)

    def _read_file(self, file_path: Union[str, Path]) -> dict:
        behavior_data = loadmat(file_path)
        if self.default_struct_name not in behavior_data:
            raise ValueError(f"The struct name '{self.default_struct_name}' not found in {file_path}.")

        return behavior_data[self.default_struct_name]

    def add_to_nwbfile(
        self,
        nwbfile: NWBFile,
        metadata: dict,
        column_name_mapping: Optional[dict] = None,
        column_descriptions: Optional[dict] = None,
    ) -> None:
        data = self._read_file(file_path=self.source_data["file_path"])

        if "RewardedSide" in data:
            side_mapping = {"L": "Left", "R": "Right"}
            data["RewardedSide"] = [side_mapping[side] for side in data["RewardedSide"]]

        columns_with_boolean = ["hits", "vios", "optout"]
        for column in columns_with_boolean:
            if column in data:
                data[column] = list(np.array(data[column]).astype(bool))

        columns_to_add = column_name_mapping.keys() if column_name_mapping is not None else data.keys()

        trials = nwbfile.trials
        if trials is None:
            raise ValueError("Trials table not found in NWB file.")

        for column_name in columns_to_add:
            if column_name not in data:
                warn(f"Column '{column_name}' not found in processed behavior data.", UserWarning)
                continue
            name = column_name_mapping.get(column_name, column_name) if column_name_mapping is not None else column_name
            description = (
                column_descriptions.get(column_name, "no description")
                if column_descriptions is not None
                else "no description"
            )
            trials.add_column(
                name=name,
                description=description,
                data=data[column_name],
            )
