from pathlib import Path
from typing import Union

import numpy as np
from lxml import etree


def fix_settings_xml_missing_channels(
    settings_xml_file_path: Union[str, Path],
    ap_stream_name: str = None,
):
    """
    Modify OpenEphys settings file (settings.xml) to include missing AP channels and their electrode positions.

    This function:
    1. Loads an XML settings file
    2. Identifies missing AP channels
    3. Adds missing channels with appropriate X/Y positions based on detected patterns
    4. Overwrites the XML settings file with the updated configuration
    5. Optionally, verifies the result using probeinterface

    Args:
        settings_xml_file_path (Union[str, Path]): Path to the input XML settings file
        ap_stream_name (str): Name of the data stream for probeinterface verification (optional)

    Raises:
        FileNotFoundError: If the input file doesn't exist
        ValueError: If the XML structure is invalid or required tags are missing
        AssertionError: If the final probe configuration is invalid
    """
    settings_xml_file_path = Path(settings_xml_file_path)
    if not settings_xml_file_path.exists():
        raise FileNotFoundError(f"Settings file not found: {settings_xml_file_path}")

    try:
        tree = etree.parse(str(settings_xml_file_path))
        root = tree.getroot()

        # Locate the <CHANNELS>, <ELECTRODE_XPOS>, and <ELECTRODE_YPOS> tags
        all_channels_from_channel_info = root.xpath(".//CHANNEL_INFO/CHANNEL")
        # Extract AP channels
        all_ap_channels = set(
            sorted(
                int(channel.attrib["number"])
                for channel in all_channels_from_channel_info
                if "AP" in channel.attrib["name"]
            )
        )

        channels_tag = root.xpath(".//CHANNELS")[0]
        electrode_xpos_tag = root.xpath(".//ELECTRODE_XPOS")[0]
        electrode_ypos_tag = root.xpath(".//ELECTRODE_YPOS")[0]

        # Extract channel numbers from the attributes
        channel_numbers = sorted(int(attr[2:]) for attr in channels_tag.attrib.keys())

        # Identify missing channels
        missing_channels = sorted(all_ap_channels - set(channel_numbers))

        # Detect repeating pattern in <ELECTRODE_XPOS> values
        xpos_values = [int(value) for value in electrode_xpos_tag.attrib.values()]
        pattern_length = next(
            (i for i in range(1, len(xpos_values) // 2) if xpos_values[:i] == xpos_values[i : 2 * i]), len(xpos_values)
        )
        xpos_pattern = xpos_values[:pattern_length]

        # Detect repeating pattern in <ELECTRODE_YPOS> values
        ypos_values = [int(value) for value in electrode_ypos_tag.attrib.values()]
        ypos_step = np.unique(np.diff(sorted(set(ypos_values))))[0]

        # Insert missing channels
        for missing_channel in missing_channels:
            channels_tag.set(f"CH{missing_channel}", "0")
            pattern_value = xpos_pattern[missing_channel % pattern_length]
            electrode_xpos_tag.set(f"CH{missing_channel}", str(pattern_value))

            pattern_value_ypos = (missing_channel // 2) * ypos_step  # 20
            electrode_ypos_tag.set(f"CH{missing_channel}", str(pattern_value_ypos))

        # Save the updated XML to a new file
        tree.write(str(settings_xml_file_path), pretty_print=True)

    except Exception as e:
        print(f"Failed to modify settings XML: {str(e)}")
        raise

    if ap_stream_name is not None:
        import probeinterface

        probe = probeinterface.read_openephys(settings_file=settings_xml_file_path, stream_name=ap_stream_name)
        assert len(probe.contact_ids) == 384
        print("Probe configuration verified successfully.")
