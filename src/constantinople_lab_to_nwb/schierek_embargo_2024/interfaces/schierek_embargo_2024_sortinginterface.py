from neuroconv.datainterfaces.ecephys.basesortingextractorinterface import BaseSortingExtractorInterface
from pydantic import FilePath

from constantinople_lab_to_nwb.schierek_embargo_2024.extractors import SchierekEmbargo2024SortingExtractor


class SchierekEmbargo2024SortingInterface(BaseSortingExtractorInterface):
    Extractor = SchierekEmbargo2024SortingExtractor

    def __init__(self, file_path: FilePath, sampling_frequency: float, verbose: bool = True):
        """
        Parameters
        ----------
        file_path: FilePathType
            Path to the MAT file containing the spiking data.
        sampling_frequency: float
            The sampling frequency of the recording.
        verbose: bool, default: True
            Allows verbosity.
        """
        super().__init__(file_path=file_path, sampling_frequency=sampling_frequency, verbose=verbose)
