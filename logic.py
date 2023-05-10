from pathlib import Path
from datetime import datetime
from pprint import pformat
from typing import Dict, List

import shutil

import exifread
import imagehash

from utils import get_location_from_gpscoord, get_gpscoord_from_exif
from utils import generate_crypto_hash, generate_perceptual_hash

from database import PhotoModel, PhotoDatabase
from utils import get_logger

# Create configure module   module_logger
logger = get_logger(__name__)


class Photo:
    """
    A class representing a photo and its associated tags.

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
        self.tags = self.generate_tags()

    def __str__(self):
        return pformat(self.tags, indent=2)

    def generate_tags(self) -> Dict[str, str]:
        """
        Generates tags associated with the photo using Exif metadata.

        Returns:
            Dict[str, str]: A dictionary containing various tags associated with the photo.
        """
        # Read the Exif data from the photo file
        with open(str(self.filepath), "rb") as f:
            exif_tags = exifread.process_file(f, details=False)

        # Initialize a dictionary to store the tags
        tags = {}

        # file information
        tags["filepath"] = str(self.filepath)

        # exif image information
        tags["camera"] = (
            exif_tags["Image Model"].printable if exif_tags.get("Image Model") else None
        )
        tags["datetime"] = (
            datetime.strptime(
                exif_tags["EXIF DateTimeOriginal"].printable, "%Y:%m:%d %H:%M:%S"
            )
            if exif_tags.get("EXIF DateTimeOriginal")
            else None
        )
        tags["size"] = self.filepath.stat().st_size
        tags["width"] = (
            exif_tags["EXIF ExifImageWidth"].printable
            if exif_tags.get("EXIF ExifImageWidth")
            else None
        )
        tags["height"] = (
            exif_tags["EXIF ExifImageLength"].printable
            if exif_tags.get("EXIF ExifImageLength")
            else None
        )
        tags["resolution_units"] = (
            exif_tags["Image ResolutionUnit"].printable
            if exif_tags.get("Image ResolutionUnit")
            else None
        )
        tags["resolution_x"] = (
            exif_tags["Image XResolution"].printable
            if exif_tags.get("Image XResolution")
            else None
        )
        tags["resolution_y"] = (
            exif_tags["Image YResolution"].printable
            if exif_tags.get("Image YResolution")
            else None
        )

        # extract exif GPS information if available
        if exif_tags.get("Image GPSInfo"):
            latitude, longitude = get_gpscoord_from_exif(exif_tags)

            if latitude and longitude:
                location_coord_str = f"{latitude:.6f};{longitude:.6f}"
                location_str = get_location_from_gpscoord(latitude, longitude)
            else:
                location_str = "unknown_location"
                location_coord_str = "unknown_location"
        else:
            location_str = "unknown_location"
            location_coord_str = "unknown_location"

        tags["location_coord"] = location_coord_str
        tags["location"] = location_str

        # generate image hash ids
        tags["perceptual_hash"] = generate_perceptual_hash(str(self.filepath))
        tags["crypto_hash"] = generate_crypto_hash(str(self.filepath))

        return tags


class PhotoOrganizer:
    def __init__(self, path: Path, db_filename):
        self.path = path
        path_db = path.joinpath(f".photo-organizer/{db_filename}")
        self.database = PhotoDatabase(path_db)

    def check_validity(self):
        # TODO: Check if a valid repository with valid database file exists
        return True

    def get_summary(self):
        photos = self.database.get_all()

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

    def add_image(self, image: Photo) -> None:
        photo_model = PhotoModel(
            original_filepath=image.tags["filepath"],
            new_filepath="",
            camera=image.tags["camera"],
            date_time=image.tags["datetime"],
            size=image.tags["size"],
            width=image.tags["width"],
            height=image.tags["height"],
            resolution_units=image.tags["resolution_units"],
            resolution_x=image.tags["resolution_x"],
            resolution_y=image.tags["resolution_y"],
            location_coord=image.tags["location_coord"],
            location=image.tags["location"],
            perceptual_hash=image.tags["perceptual_hash"],
            crypto_hash=image.tags["crypto_hash"],
        )

        self.database.add_photo(photo_model)

    def copy_image(self, image: Photo) -> bool:
        dest_folder = (
            self.path.joinpath(
                str(image.tags["datetime"].year),
                str(image.tags["datetime"].month),
            )
            if image.tags.get("datetime")
            else self.path.joinpath("unknown", "unknown")
        )
        dest_folder.mkdir(parents=True, exist_ok=True)

        dest_name = image.tags["perceptual_hash"]
        extension = Path(image.tags["filepath"]).suffix[1:]

        dest_filename = f"{dest_name}.{extension.upper()}"
        dest_filepath = dest_folder.joinpath(dest_filename).absolute()

        if not dest_filepath.exists():
            try:
                shutil.copy(str(image.filepath), str(dest_filepath))
                self.database.update_photo_newpath(
                    image.tags["crypto_hash"], dest_filepath
                )
            except Exception:
                logger.error(Exception)
                return False
        else:
            logger.error(f"File {dest_filepath.name} already exists in database")
            return False

        return True

    def process_file(self, image_path: Path, do_copy=True):
        # process all images found
        # analyse image and create logic.Photo object
        image_obj = Photo(image_path)

        # create image database object
        image_db = PhotoModel(
            original_filepath=image_obj.tags["filepath"],
            new_filepath="",
            camera=image_obj.tags["camera"],
            date_time=image_obj.tags["datetime"],
            size=image_obj.tags["size"],
            width=image_obj.tags["width"],
            height=image_obj.tags["height"],
            resolution_units=image_obj.tags["resolution_units"],
            resolution_x=image_obj.tags["resolution_x"],
            resolution_y=image_obj.tags["resolution_y"],
            location_coord=image_obj.tags["location_coord"],
            location=image_obj.tags["location"],
            perceptual_hash=image_obj.tags["perceptual_hash"],
            crypto_hash=image_obj.tags["crypto_hash"],
        )

        # add image db object into database
        if not self.database.add_photo(image_db):
            return False

        # copy image files into repository
        if do_copy:
            self.copy_image(image_obj)

        return True

    def filter_photos(self, search_tags: Dict[str, str]) -> List[Photo]:
        filtered_photos = []
        # Code for filtering photos based on search tags
        return filtered_photos

    def display_photos(self, photos: List[Photo]) -> None:
        pass
        # Code for displaying selected photos


input_photo = "/home/miguel/sw/photo-organizer/data/Curling/IMG_4834.JPG"
