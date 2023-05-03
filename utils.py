import logging
from geopy.geocoders import Nominatim


def get_coordinate_from_exif_str(exif_coord_str: str) -> float:
    if not exif_coord_str:
        return None

    deg, min, sec_fraction = str(exif_coord_str).strip("[]").split(", ")
    sec_numerator, sec_denominator = map(int, sec_fraction.split("/"))
    sec = sec_numerator / sec_denominator

    return float(deg) + float(min) / 60 + sec / 3600


def get_location_from_gps(latitude, longitude):
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


def get_logger(main=False):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    if main:
        formatter = logging.Formatter("%(levelname)s - %(message)s")
        handler = logging.FileHandler("logs/log.log", mode="a")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
