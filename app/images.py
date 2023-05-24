from dataclasses import dataclass
import hashlib
import itertools
from pathlib import Path

import imagehash
import yaml


from app.exif import ExifTags
from app.geolocation import GeoLocation
from app.hashing import crypto_hash, perceptual_hash


# load configuration file
with open("app/config.yaml") as file:
    config = yaml.safe_load(file)

# read configuration parameters
DB_FILE = config["database"]["file"]
DB_FOLDER = config["database"]["folder"]
# Read configuration parameters
IMAGE_EXTS = list(
    itertools.chain.from_iterable(
        values for values in config["image"]["types"].values()
    )
)


@dataclass
class Image:
    """
    A class representing an image file and its associated tags.

    Attributes:
        file (str): The file path of the photo.
        filename (str): The base name of the photo file.
        tags (Dict[str, str]): A dictionary of tags associated with the photo.
    """

    def __init__(self, filepath: Path):
        """
        Initializes the Photo class with a file path.

        Args:
            file (str): The file path of the photo.
        """
        self.filepath = filepath.absolute()
        self.size = self.filepath.stat().st_size
        self.type = get_type(self.filepath.suffix.lower())
        self.perceptual_hash = perceptual_hash(self.filepath)
        self.crypto_hash = crypto_hash(self.filepath)
        self.exif_tags = ExifTags(self.filepath)
        if (
            self.exif_tags
            and self.exif_tags.location_lat
            and self.exif_tags.location_long
        ):
            self.geo_location = GeoLocation(
                self.exif_tags.location_long, self.exif_tags.location_lat
            )
        else:
            self.geo_location = GeoLocation(None, None)
        self.customtags = None


def get_type(image_ext):
    for key, value in config["image"]["types"].items():
        if image_ext in value:
            return key
    return None
