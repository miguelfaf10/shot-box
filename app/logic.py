import itertools
from pathlib import Path
from enum import Enum
from datetime import datetime
from pprint import pformat
from typing import Dict, List, Protocol
from dataclasses import dataclass, field
import yaml

import shutil

from app.infra.repository.media_database import MediaDatabase
from app.infra.entities.media_model import MediaDBModel
from app.hashing import perceptual_hash

from app.utils import (
    get_logger,
    scan_folder,
)

# Create configure module   module_logger
logger = get_logger(__name__)

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


class IntrinsicTags(Protocol):
    filepath: Path
    camera: str
    datetime: datetime
    width: int
    height: int
    resolution_x: int
    resolution_y: int
    resolution_units: str
    location_lat: float
    location_long: float


class CustomTags(Protocol):
    pass


class GeoLocation(Protocol):
    longitude: float
    latitude: float
    country: str
    state: str
    city: str


class MediaObj(Protocol):
    filepath: Path
    size: int
    type: str
    perceptual_hash: str
    crypto_hash: str
    intrinsic_tags: IntrinsicTags
    geo_location: GeoLocation
    custom_tags: CustomTags


class MediaOrganizer:
    def __init__(self, repo_path: Path, media_db: MediaDatabase):
        """Initialize the PhotoOrganizer object.

        Args:
            repo_path (Path): The path to the repository where photos will be copied.
            db_path (Path): The path to the SQLite database file.

        Returns:
            None
        """
        self.repo_path = repo_path
        self.db = media_db

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

    def process_file(self, media_obj: MediaObj, do_copy=True):
        # create media database object
        media_db_model = MediaDBModel(
            # basic info
            original_filepath=str(media_obj.filepath),
            file_type=media_obj.type,
            size=media_obj.size,
            perceptual_hash=media_obj.perceptual_hash,
            crypto_hash=media_obj.crypto_hash,
            # exif info
            camera=media_obj.exif_tags.camera,
            datetime=media_obj.exif_tags.datetime,
            width=media_obj.exif_tags.width,
            height=media_obj.exif_tags.height,
            resolution_units=media_obj.exif_tags.resolution_units,
            resolution_x=media_obj.exif_tags.resolution_x,
            resolution_y=media_obj.exif_tags.resolution_y,
            # geolocation
            location_longitude=media_obj.geo_location.longitude,
            location_latitude=media_obj.geo_location.latitude,
            location_country=media_obj.geo_location.country,
            location_state=media_obj.geo_location.state,
            location_city=media_obj.geo_location.city,
            new_filepath="",
            n_perceptual_hash=0,
        )

        # add image db object into database
        n_perceptualhash = self.db.insert_media(media_db_model)
        if n_perceptualhash is None:
            return False

        # copy image files into repository
        if do_copy:
            # Determine the destination folder based on the image's datetime metadata
            # or use a default folder if the datetime is not available
            if media_obj.exif_tags.datetime:
                dest_folder = self.repo_path.joinpath(
                    str(media_obj.exif_tags.datetime.year),
                    str(media_obj.exif_tags.datetime.month),
                )
            else:
                dest_folder = self.repo_path.joinpath("unknown", "unknown")

            dest_folder.mkdir(parents=True, exist_ok=True)

            # Generate the destination filename using the perceptual hash and n_perceptualhash values
            dest_name = f"{media_obj.perceptual_hash}_{n_perceptualhash}"
            extension = Path(media_obj.filepath).suffix[1:]

            # Construct the destination filepath by joining the destination folder and filename
            dest_filename = f"{dest_name}.{extension.upper()}"
            dest_filepath = dest_folder.joinpath(dest_filename).absolute()

            if not dest_filepath.exists():
                try:
                    # Copy the image file from the original filepath to the destination filepath
                    shutil.copy(str(media_obj.exif_tags.filepath), str(dest_filepath))

                    # Update the new_filepath attribute of the image in the database
                    self.db.update_newpath(
                        media_obj.exif_tags.crypto_hash, dest_filepath
                    )
                except Exception:
                    logger.error(Exception)
                    return False
            else:
                logger.error(f"File {dest_filepath.name} already exists in repository")
                return False

            return True

    def filter_photos(self, search_tags: Dict[str, str]) -> List[MediaObj]:
        if search_tags.get("country"):
            filtered_photos = self.db.search_by_location(country=search_tags["country"])

        return filtered_photos

    def display_photos(self, photos: List[MediaObj]) -> None:
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


class Repository:
    """Handles repository folders and creation of ImageOrganizer"""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path.absolute()
        self.db_path = repo_path.joinpath(DB_FOLDER).joinpath(DB_FILE)
        if not (self.repo_path.exists() and self.db_path.parent.exists()):
            self.db_path.parent.mkdir(parents=True)

        self.photo_org = MediaOrganizer(self.repo_path, MediaDatabase(self.db_path))
