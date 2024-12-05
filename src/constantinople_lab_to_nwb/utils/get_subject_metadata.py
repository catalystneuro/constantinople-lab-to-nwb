from pathlib import Path
from typing import Union
from warnings import warn

import pandas as pd
from pymatreader import read_mat


def get_subject_metadata_from_rat_info_folder(
    folder_path: Union[str, Path],
    subject_id: str,
    date: str,
) -> dict:
    """
    Load subject metadata from the rat info files.
    The "registry.mat" file contains information about the subject such as date of birth, sex, and vendor.
    The "Mass_registry.mat" file contains information about the weight of the subject.

    Parameters
    ----------
    folder_path: Union[str, Path]
        The folder path containing the rat info files.
    subject_id: str
        The subject ID.
    date: str
        The date of the session in the format "yyyy-mm-dd".
    """

    folder_path = Path(folder_path)
    rat_registry_file_path = folder_path / "registry.mat"

    subject_metadata = dict()
    if rat_registry_file_path.exists():
        rat_registry = read_mat(str(rat_registry_file_path))
        rat_registry = pd.DataFrame(rat_registry["Registry"])

        filtered_rat_registry = rat_registry[rat_registry["RatName"] == subject_id]
        if not filtered_rat_registry.empty:
            date_of_birth = filtered_rat_registry["DOB"].values[0]
            if date_of_birth:
                # convert date of birth to datetime with format "yyyy-mm-dd"
                date_of_birth = pd.to_datetime(date_of_birth, format="%Y-%m-%d")
                subject_metadata.update(date_of_birth=date_of_birth)
            else:
                # TODO: what to do if date of birth is missing?
                warn("Date of birth is missing. We recommend adding this information to the rat info files.")
                # Using age range specified in the manuscript
                subject_metadata.update(age="P6M/P24M")
            subject_metadata.update(sex=filtered_rat_registry["sex"].values[0])
            vendor = filtered_rat_registry["vendor"].values[0]
            if vendor:
                subject_metadata.update(description=f"Vendor: {vendor}")

    mass_registry_file_path = folder_path / "Mass_registry.mat"
    if mass_registry_file_path.exists():
        mass_registry = read_mat(str(mass_registry_file_path))
        mass_registry = pd.DataFrame(mass_registry["Mass_registry"])

        filtered_mass_registry = mass_registry[(mass_registry["rat"] == subject_id) & (mass_registry["date"] == date)]
        if not filtered_mass_registry.empty:
            weight_g = filtered_mass_registry["mass"].astype(int).values[0]  # in grams
            # convert mass to kg
            weight_kg = weight_g / 1000
            subject_metadata.update(weight=str(weight_kg))

    return subject_metadata
