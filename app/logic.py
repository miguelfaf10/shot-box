from pathlib import Path
from datetime import datetime
from pprint import pformat
from typing import Dict, List
from dataclasses import dataclass, field
import yaml


import shutil

import exifread
import imagehash

from app.infra.repository.image_database import ImageDatabase
from app.infra.entities.image_model import ImageModel

from app.utils import (
    get_logger,
    scan_folder,
    get_location_from_gpscoord,
    get_gpscoord_from_exif,
    crypto_hash,
    perceptual_hash,
    extract_first_integer,
    get_type,
)

# Create configure module   module_logger
logger = get_logger(__name__)


@dataclass
class GeoLocation:
    longitude: float
    latitude: float
    country: str = field(init=False)
    state: str = field(init=False)
    city: str = field(init=False)

    def __post_init__(self) -> None:
        if self.latitude and self.longitude:
            country, state, city = get_location_from_gpscoord(
                self.latitude, self.longitude
            )
        else:
            country, state, city = ("unknown", "unknown", "unknown")
        self.country = country
        self.state = state
        self.city = city


def read_exif(filepath: Path):
    # Read the Exif data from the photo file
    with open(str(filepath), "rb") as f:
        try:
            return exifread.process_file(f, details=False)
        except Exception as e:
            print(f"Error reading EXIF from {filepath.name}: {e}")
            return {}


class ExifTags:
    def __init__(self, filepath: Path):
        self._exif_tags = read_exif(filepath)

        self.process_tags()
        # self.camera
        # self.datetime
        # self.width
        # self.height
        # self.resolution_x
        # self.resolution_y
        # self.resolution_units
        # self.location_lat
        # self.location_long

    def process_tags(self):
        # camera
        if val := self._exif_tags.get("Image Model"):
            self.camera = val.printable
        else:
            self.camera = None

        # datetime
        if val := self._exif_tags.get("EXIF DateTimeOriginal"):
            self.datetime = datetime.strptime(val.printable, "%Y:%m:%d %H:%M:%S")
        elif val := self._exif_tags.get("Image DateTime"):
            self.datetime = datetime.strptime(val.printable, "%Y:%m:%d %H:%M:%S")
        else:
            self.datetime = None

        # width
        if val := self._exif_tags.get("EXIF ExifImageWidth"):
            self.width = extract_first_integer(val.printable)
        elif val := self._exif_tags.get("Image ImageWidth"):
            self.width = extract_first_integer(val.printable)
        else:
            self.width = None

        # height
        if val := self._exif_tags.get("EXIF ExifImageLength"):
            self.height = extract_first_integer(val.printable)
        elif val := self._exif_tags.get("Image ImageLength"):
            self.height = extract_first_integer(val.printable)
        else:
            self.height = None

        # resolution units
        if val := self._exif_tags.get("Image ResolutionUnit"):
            self.resolution_units = val.printable
        else:
            self.resolution_units = None

        # resolution X
        if val := self._exif_tags.get("Image XResolution"):
            self.resolution_x = int(val.printable)
        else:
            self.resolution_x = None

        # resolution y
        if val := self._exif_tags.get("Image YResolution"):
            self.resolution_y = int(val.printable)
        else:
            self.resolution_y = None

        # GPS coordinates
        if val := self._exif_tags.get("Image GPSInfo"):
            self.location_lat, self.location_long = get_gpscoord_from_exif(
                self._exif_tags
            )
        else:
            self.location_long = None
            self.location_lat = None


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


class ImageOrganizer:
    def __init__(self, repo_path: Path, db_path: Path):
        """Initialize the PhotoOrganizer object.

        Args:
            repo_path (Path): The path to the repository where photos will be copied.
            db_path (Path): The path to the SQLite database file.

        Returns:
            None
        """
        self.repo_path = repo_path
        self.db_path = db_path
        self.db = ImageDatabase(self.db_path) if self.db_path.parent.exists() else None

    def get_info(self):
        """
        Get information about the photos in the database.

        Returns:
            dict: A dictionary containing information about the photos.
                - "total_photos" (int): The total number of photos in the database.
                - "total_size" (int): The total size of all the photos in bytes.
                - "files_exist" (int): The number of photos whose new file path exists in the repository.
        """
        if not self.db:
            return None

        photos = self.db.get_all()

        total_photos = len(photos)
        total_size = 0
        files_exist = 0
        for photo in photos:
            total_size += photo.size
            files_exist += 1 if Path(photo.new_filepath).is_file() else 1

        return {
            "total_photos": total_photos,
            "total_size": total_size,
            "files_exist": files_exist,
        }

    def process_file(self, image_path: Path, do_copy=True):
        # process all images found
        # analyse image and create logic.Photo object
        image_obj = Image(image_path)

        # create image database object
        image_db = ImageModel(
            # basic info
            original_filepath=str(image_obj.filepath),
            file_type=image_obj.type,
            size=image_obj.size,
            perceptual_hash=image_obj.perceptual_hash,
            crypto_hash=image_obj.crypto_hash,
            camera=image_obj.exif_tags.camera,
            datetime=image_obj.exif_tags.datetime,
            width=image_obj.exif_tags.width,
            height=image_obj.exif_tags.height,
            resolution_units=image_obj.exif_tags.resolution_units,
            resolution_x=image_obj.exif_tags.resolution_x,
            resolution_y=image_obj.exif_tags.resolution_y,
            location_longitude=image_obj.geo_location.longitude,
            location_latitude=image_obj.geo_location.latitude,
            location_country=image_obj.geo_location.country,
            location_state=image_obj.geo_location.state,
            location_city=image_obj.geo_location.city,
            new_filepath="",
            n_perceptual_hash=0,
        )

        # add image db object into database
        n_perceptualhash = self.db.insert_image(image_db)
        if n_perceptualhash is None:
            return False

        # copy image files into repository
        if do_copy:
            # Determine the destination folder based on the image's datetime metadata
            # or use a default folder if the datetime is not available
            if image_obj.exif_tags.datetime:
                dest_folder = self.repo_path.joinpath(
                    str(image_obj.exif_tags.datetime.year),
                    str(image_obj.exif_tags.datetime.month),
                )
            else:
                dest_folder = self.repo_path.joinpath("unknown", "unknown")

            dest_folder.mkdir(parents=True, exist_ok=True)

            # Generate the destination filename using the perceptual hash and n_perceptualhash values
            dest_name = f"{image_obj.perceptual_hash}_{n_perceptualhash}"
            extension = Path(image_obj.filepath).suffix[1:]

            # Construct the destination filepath by joining the destination folder and filename
            dest_filename = f"{dest_name}.{extension.upper()}"
            dest_filepath = dest_folder.joinpath(dest_filename).absolute()

            if not dest_filepath.exists():
                try:
                    # Copy the image file from the original filepath to the destination filepath
                    shutil.copy(str(image_obj.exif_tags.filepath), str(dest_filepath))

                    # Update the new_filepath attribute of the image in the database
                    self.db.update_newpath(
                        image_obj.exif_tags.crypto_hash, dest_filepath
                    )
                except Exception:
                    logger.error(Exception)
                    return False
            else:
                logger.error(f"File {dest_filepath.name} already exists in repository")
                return False

            return True

    def filter_photos(self, search_tags: Dict[str, str]) -> List[Image]:
        if search_tags.get("country"):
            filtered_photos = self.db.search_by_location(country=search_tags["country"])

        return filtered_photos

    def display_photos(self, photos: List[Image]) -> None:
        raise NotImplemented
        # Code for displaying selected photos

    def check_consistency(self, image_ext):
        rows = self.db.get_all()

        exist_db_not_copied = []
        exist_db_not_repo = []
        exist_repo_incorrect_image = []
        exist_repo_not_db = scan_folder(self.repo_path, image_ext, recursive=True)

        for row in rows:
            # check db entries
            if row.new_filepath:
                # file has been copied

                if Path(row.new_filepath).exists():
                    # file exists in new location
                    if Path(row.new_filepath).stem.split("_")[0] == perceptual_hash(
                        Path(row.new_filepath)
                    ):
                        # file is the correct image
                        exist_repo_not_db.remove(Path(row.new_filepath))
                    else:
                        exist_repo_incorrect_image.append(Path(row.new_filepath))
                #        file  doesn't exist in new location
                else:
                    exist_db_not_repo.append(Path(row.new_filepath))
            else:
                exist_db_not_copied.append(Path(row.original_filepath))

        return {
            "exist_db_not_copied": exist_db_not_copied,
            "exist_db_not_repo": exist_db_not_repo,
            "exist_repo_not_db": exist_repo_not_db,
            "exist_repo_incorrect_name": exist_repo_incorrect_image,
        }
