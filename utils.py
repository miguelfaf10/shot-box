from pathlib import Path
from typing import List, Tuple
import logging
from rich.logging import RichHandler
from geopy.geocoders import Nominatim


def scan_folder(folder_path: Path, image_exts) -> List[Path]:
    # Add new photo folders to the database

    return [
        file_path
        for file_path in folder_path.glob("**/*")
        if file_path.is_file() and file_path.suffix.lower() in image_exts
    ]


def get_gpscoord_from_exif(exif_tags: str) -> Tuple[float, float]:
    def parse_coordinate_str(exif_coord_str: str):
        try:
            deg, min, sec_fraction = exif_coord_str.strip("[]").split(", ")
            if "/" in sec_fraction:
                sec_numerator, sec_denominator = sec_fraction.split("/")
                sec = float(sec_numerator) / float(sec_denominator)
            else:
                sec = float(sec_fraction)

            return float(deg) + float(min) / 60 + sec / 3600

        except Exception:
            return None

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

    latitude = parse_coordinate_str(lat_abs_exif_str) * (
        1 if lat_ref_exif_str.upper() == "N" else -1
    )
    longitude = parse_coordinate_str(lon_abs_exif_str) * (
        1 if lon_ref_exif_str.upper() == "E" else -1
    )

    return latitude, longitude


def get_location_from_gpscoord(latitude, longitude):
    if not (latitude and longitude):
        return "unknown_location"

    geolocator = Nominatim(user_agent="my_app")
    if location := geolocator.reverse(f"{latitude}, {longitude}", exactly_one=True):
        address = location.raw["address"]
        city = address.get("city", "")
        region = address.get("state", "")
        country = address.get("country", "")
        return f"{country};{region};{city}"
    else:
        return "unknown_location"


from PIL import Image
import imagehash
import hashlib


def generate_perceptual_hash(image_path: str, method: str = "phash") -> str:
    """
    Generates a perceptual hash identifier for an image using the specified method.

    Args:
        image_path (str): The file path of the image.
        method (str, optional): The hashing method to use. Defaults to 'phash'.
            Options: 'average', 'phash', 'dhash', 'whash'.

    Returns:
        str: The perceptual hash identifier for the image content.
    """
    if method not in ["average", "phash", "dhash", "whash"]:
        raise ValueError(f"Unsupported hashing method: {method}")

    with Image.open(image_path) as img:
        if method == "average":
            hash_value = imagehash.average_hash(img)
        elif method == "phash":
            hash_value = imagehash.phash(img)
        elif method == "dhash":
            hash_value = imagehash.dhash(img)
        elif method == "whash":
            hash_value = imagehash.whash(img)

    return str(hash_value)


def generate_crypto_hash(image_path: str, algorithm: str = "sha256") -> str:
    """
    Generates a unique hash identifier for an image using the specified hashing algorithm.

    Args:
        image_path (str): The file path of the image.
        algorithm (str, optional): The hashing algorithm to use. Defaults to 'sha256'.

    Returns:
        str: The unique hash identifier for the image content.
    """
    if algorithm not in hashlib.algorithms_guaranteed:
        raise ValueError(f"Unsupported hashing algorithm: {algorithm}")

    hasher = hashlib.new(algorithm)

    with open(image_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)

    return hasher.hexdigest()


def get_logger(name):
    logger = logging.getLogger("rich")
    logger.setLevel(logging.DEBUG)

    #        formatter = logging.Formatter("%(levelname)s - %(message)s")
    formatter = logging.Formatter(
        "%(asctime)s -  [%(filename)s:%(lineno)d] - %(levelname)s - %(message)s"
    )
    handler = logging.FileHandler("logs/log.log", mode="a")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
