# constantinople-lab-to-nwb
NWB conversion scripts for Constantinople lab data to the [Neurodata Without Borders](https://nwb-overview.readthedocs.io/) data format.

## Installation from Github
We recommend installing this package directly from Github. This option has the advantage that the source code can be modifed if you need to amend some of the code we originally provided to adapt to future experimental differences.
To install the conversion from GitHub you will need to use `git` ([installation instructions](https://github.com/git-guides/install-git)). We also recommend the installation of `conda` ([installation instructions](https://docs.conda.io/en/latest/miniconda.html)) as it contains
all the required machinery in a single and simple install.

From a terminal (note that conda should install one in your system) you can do the following:

```
git clone https://github.com/catalystneuro/constantinople-lab-to-nwb
cd constantinople-lab-to-nwb
conda env create --file make_env.yml
conda activate constantinople_lab_to_nwb_env
```

This creates a [conda environment](https://docs.conda.io/projects/conda/en/latest/user-guide/concepts/environments.html) which isolates the conversion code from your system libraries.  We recommend that you run all your conversion related tasks and analysis from the created environment in order to minimize issues related to package dependencies.

Alternatively, if you want to avoid conda altogether (for example if you use another virtual environment tool) you can install the repository with the following commands using only pip:

```
git clone https://github.com/catalystneuro/constantinople-lab-to-nwb
cd constantinople-lab-to-nwb
pip install -e .
```

Note:
both of the methods above install the repository in [editable mode](https://pip.pypa.io/en/stable/cli/pip_install/#editable-installs).

### Installing conversion specific dependencies

To install *all* the conversion specific dependencies you can run the following command:

```
pip install -r frozen_dependencies.txt
```

## Repository structure
Each conversion is organized in a directory of its own in the `src` directory:

```
constantinople-lab-to-nwb/
├── LICENSE
├── make_env.yml
├── pyproject.toml
├── README.md
├── requirements.txt
├── setup.py
└── src
    ├── constantinople_lab_to_nwb
    │   ├── fiber_photometry
    │   ├── general_interfaces
    │   │   ├── __init__.py
    │   │   └── bpodbehaviorinterface.py
    │   ├── mah_2024
    │   ├── schierek_embargo_2024
    │   │   ├── __init__.py
    │   │   ├── extractors
    │   │   │   ├── __init__.py
    │   │   │   └── schierek_embargo_2024_sortingextractor.py
    │   │   ├── interfaces
    │   │   │   ├── __init__.py
    │   │   │   ├── schierek_embargo_2024_processedbehaviorinterface.py
    │   │   │   └── schierek_embargo_2024_sortinginterface.py
    │   │   ├── mat_utils
    │   │   │   └── convertSULocationToString.m
    │   │   ├── metadata
    │   │   │   ├── schierek_embargo_2024_behavior_metadata.yaml
    │   │   │   ├── schierek_embargo_2024_ecephys_metadata.yaml
    │   │   │   └── schierek_embargo_2024_general_metadata.yaml
    │   │   ├── schierek_embargo_2024_convert_session.py
    │   │   ├── schierek_embargo_2024_notes.md
    │   │   ├── schierek_embargo_2024_nwbconverter.py
    │   │   ├── schierek_embargo_2024_requirements.txt
    │   │   └── tutorials
    └── utils
        ├── __init__.py
        ├── fix_xml_openephys.py
        └── get_subject_metadata.py
```

 For example, for the conversion `schierek_embargo_2024` you can find a directory located in `src/constantinople-lab-to-nwb/schierek_embargo_2024`. Inside each conversion directory you can find the following files:

* `schierek_embargo_2024_convert_sesion.py`: this script defines the function to convert one full session of the conversion.
* `schierek_embargo_2024_requirements.txt`: dependencies specific to this conversion.
* `schierek_embargo_2024_nwbconverter.py`: the place where the `NWBConverter` class is defined.
* `schierek_embargo_2024_notes.md`: notes and comments concerning this specific conversion.
* `extractors/`: directory containing the imaging extractor class for this specific conversion.
* `interfaces/`: directory containing the interface classes for this specific conversion.
* `metadata/`: directory containing the metadata files for this specific conversion.
* `tutorials/`: directory containing tutorials for this specific conversion.
* `utils/`: directory containing utility functions for this specific conversion.

The directory might contain other files that are necessary for the conversion but those are the central ones.

### Notes on the conversion

The conversion notes is located in `src/constantinople_lab_to_nwb/schierek_embargo_2024/schierek_embargo_2024_notes.md`.
This file contains information about the expected file structure and the conversion process.

### Running a specific conversion

Once you have installed the package with pip, you can run any of the conversion scripts in a notebook or a python file:

https://github.com/catalystneuro/constantinople-lab-to-nwb//tree/main/src/schierek_embargo_2024/schierek_embargo_2024_convert_session.py

You can run a specific conversion with the following command:
```
python src/constantinople_lab_to_nwb/schierek_embargo_2024/schierek_embargo_2024_convert_session.py
```

## NWB tutorials

The `tutorials` directory contains Jupyter notebooks that demonstrate how to use the NWB files generated by the conversion scripts.
The notebooks are located in the `src/constantinople_lab_to_nwb/schierek_embargo_2024/tutorials` directory.

You might need to install `jupyter` before running the notebooks:

```
pip install jupyter
cd src/constantinople_lab_to_nwb/schierek_embargo_2024/tutorials
jupyter lab
```

## Upload to the DANDI Archive

Detailed instructions on how to upload the data to the DANDI archive can be found [here](dandi.md).
