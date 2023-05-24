from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import re
from typing import Tuple

import exifread


@dataclass
class ExifTags:
    filepath: Path
    camera: str = field(init=False)
    datetime: datetime = field(init=False)
    width: int = field(init=False)
    height: int = field(init=False)
    resolution_x: int = field(init=False)
    resolution_y: int = field(init=False)
    resolution_units: str = field(init=False)
    location_lat: float = field(init=False)
    location_long: float = field(init=False)

    def __post_init__(self):
        exif_tags = read_exif(self.filepath)

        # camera
        if val := exif_tags.get("Image Model"):
            self.camera = val.printable
        else:
            self.camera = None

        # datetime
        if val := exif_tags.get("EXIF DateTimeOriginal"):
            self.datetime = datetime.strptime(val.printable, "%Y:%m:%d %H:%M:%S")
        elif val := exif_tags.get("Image DateTime"):
            self.datetime = datetime.strptime(val.printable, "%Y:%m:%d %H:%M:%S")
        else:
            self.datetime = None

        # width
        if val := exif_tags.get("EXIF ExifImageWidth"):
            self.width = extract_first_integer(val.printable)
        elif val := exif_tags.get("Image ImageWidth"):
            self.width = extract_first_integer(val.printable)
        else:
            self.width = None

        # height
        if val := exif_tags.get("EXIF ExifImageLength"):
            self.height = extract_first_integer(val.printable)
        elif val := exif_tags.get("Image ImageLength"):
            self.height = extract_first_integer(val.printable)
        else:
            self.height = None

        # resolution units
        if val := exif_tags.get("Image ResolutionUnit"):
            self.resolution_units = val.printable
        else:
            self.resolution_units = None

        # resolution X
        if val := exif_tags.get("Image XResolution"):
            self.resolution_x = int(val.printable)
        else:
            self.resolution_x = None

        # resolution y
        if val := exif_tags.get("Image YResolution"):
            self.resolution_y = int(val.printable)
        else:
            self.resolution_y = None

        # GPS coordinates
        if val := exif_tags.get("Image GPSInfo"):
            self.location_lat, self.location_long = get_gpscoord_from_exif(exif_tags)
        else:
            self.location_long = None
            self.location_lat = None


def read_exif(filepath: Path):
    # Read the Exif data from the photo file
    with open(str(filepath), "rb") as f:
        try:
            return exifread.process_file(f, details=False)
        except Exception as e:
            print(f"Error reading EXIF from {filepath.name}: {e}")
            return {}


def extract_fraction(rational_str: str):
    number_pattern = re.compile(r"(\d+)(?:/(\d+))?")
    matches = number_pattern.match(rational_str)
    if matches:
        number1 = float(matches.group(1))
        number2 = float(matches.group(2)) if matches.group(2) else 1

    if number2 != 0:
        return number1 / number2
    elif number1 == 0:
        return 0
    else:
        raise ZeroDivisionError


def extract_first_integer(string):
    match_1 = re.match(r"(\d+)", string)  # case of integer e.g.'3434'
    match_2 = re.match(r"\[(\d+),", string)  # case of '[123,0]'
    if match_1:
        return int(match_1[1])
    elif match_2:
        return int(match_2[1])
    else:
        return None


def parse_exifcoord_str(exif_coord_str: str):
    try:
        deg_frac_str, min_frac_str, sec_frac_str = exif_coord_str.strip("[]").split(
            ", "
        )
        deg = extract_fraction(deg_frac_str)
        min = extract_fraction(min_frac_str)
        sec = extract_fraction(sec_frac_str)

        return deg + min / 60 + sec / 3600

    except Exception:
        return None


def get_gpscoord_from_exif(exif_tags: str) -> Tuple[float, float]:
    if exif_tags.get("GPS GPSLongitude"):
        lon_abs_exif_str = exif_tags["GPS GPSLongitude"].printable
    else:
        return None, None

    if exif_tags.get("GPS GPSLatitude"):
        lat_abs_exif_str = exif_tags["GPS GPSLatitude"].printable
    else:
        return None, None

    if exif_tags.get("GPS GPSLongitudeRef"):
        lon_ref_exif_str = exif_tags["GPS GPSLongitudeRef"].printable
    else:
        return None, None

    if exif_tags.get("GPS GPSLatitudeRef"):
        lat_ref_exif_str = exif_tags["GPS GPSLatitudeRef"].printable
    else:
        return None, None

    latitude = parse_exifcoord_str(lat_abs_exif_str) * (
        1 if lat_ref_exif_str.upper() == "N" else -1
    )
    longitude = parse_exifcoord_str(lon_abs_exif_str) * (
        1 if lon_ref_exif_str.upper() == "E" else -1
    )

    return latitude, longitude
