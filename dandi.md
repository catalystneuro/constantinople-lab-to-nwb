# DANDI archive instructions

## Setup

1. Create a DANDI account at https://dandiarchive.org/

2. Install the DANDI client in your local Python environment (already gets installed in the conda environment of this repo):
```
pip install dandi
```

3. Export your DANDI API token as an environment variable (copy it from DANDI archive website).

If you're on Linux / MacOS:
```
export DANDI_API_KEY=personal-key-value
```

If you're on Windows:
```
set DANDI_API_KEY=personal-key-value
```

## Upload data

Given that you have a dandiset created, you can upload assets to it using the DANDI client.

1. Download the dandiset to a local directory. For example, to download the dandiset with ID `DANDI:001264`:
```
dandi download --download dandiset.yaml DANDI:001264
```
This command will download the dandiset metadata file `dandiset.yaml` to the current directory, without downloading the actual data files. This is useful when you only want to upload new data files to an existing dandiset.

2. Change directory to the dandiset folder:
```
cd 001264
```

3. Organize the converted NWB files according to the dandiset structure, where `<source_folder>` is the folder containing the NWB files created by your conversion script:
```
dandi organize <source_folder> --files-mode move --media-files-mode copy --update-external-file-paths
```

4. Run validation on the assets:
```
dandi validate .
```

5. Upload the assets to the DANDI archive:
```
dandi upload
```

## Additional information
For detailed instructions on how to upload data to the DANDI archive, refer to the DANDI handbook: https://www.dandiarchive.org/handbook/13_upload/

To explore all the options available in the DANDI client, you can run the commands with the `--help` flag. For example:
```
dandi --help
dandi download --help
dandi organize --help
dandi validate --help
dandi upload --help
```
