from pathlib import Path
from datetime import datetime
from pprint import pformat
from typing import Dict, List

import shutil

import exifread
import imagehash

from utils import get_location_from_gps, get_coordinate_from_exif_str
from utils import generate_crypto_hash, generate_perceptual_hash

from database import PhotoModel, PhotoDatabase
from utils import get_logger

# Create configure module   module_logger
logger = get_logger()

DB_FILE_NAME = "photo.db"
IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".bmp"]


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
        tags["camera"] = exif_tags["Image Model"].printable
        tags["datetime"] = datetime.strptime(
            exif_tags["EXIF DateTimeOriginal"].printable, "%Y:%m:%d %H:%M:%S"
        )
        tags["size"] = self.filepath.stat().st_size
        tags["width"] = exif_tags["EXIF ExifImageWidth"].printable
        tags["height"] = exif_tags["EXIF ExifImageLength"].printable
        tags["resolution_units"] = exif_tags["Image ResolutionUnit"].printable
        tags["resolution_x"] = exif_tags["Image XResolution"].printable
        tags["resolution_y"] = exif_tags["Image YResolution"].printable

        # extract exif GPS information if available
        if exif_tags.get("Image GPSInfo"):
            latitude = get_coordinate_from_exif_str(
                exif_tags["GPS GPSLatitude"].printable
            )
            longitude = get_coordinate_from_exif_str(
                exif_tags["GPS GPSLongitude"].printable
            )
            if latitude and longitude:
                location_coord_str = f"{latitude:.6f};{longitude:.6f}"
                location_str = get_location_from_gps(latitude, longitude)
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
    def __init__(self, path: Path):
        self.path = path
        path_db = path.joinpath(f".photo-organizer/{DB_FILE_NAME}")
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

    def scan_folder(self, folder_path: Path) -> List[Path]:
        # Add new photo folders to the database

        return [
            file_path
            for file_path in folder_path.glob("**/*")
            if file_path.is_file() and file_path.suffix.lower() in IMAGE_EXTENSIONS
        ]

    def analyse_images(self, image_files: List[Path]) -> List[Photo]:
        return [Photo(image_file) for image_file in image_files]

    def add_images(self, image_list: List[Photo]) -> List[Photo]:
        for image in image_list:
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

    def copy_images(self, image_list: List[Photo]):
        # Find all photo files in the photo_folders list

        for image in image_list:
            dest_folder = self.path.joinpath(
                str(image.tags["datetime"].year),
                str(image.tags["datetime"].month),
            )
            dest_folder.mkdir(parents=True, exist_ok=True)

            dest_name = image.tags["perceptual_hash"]
            extension = Path(image.tags["filepath"]).suffix[1:]

            dest_filename = f"{dest_name}.{extension.upper()}"
            dest_filepath = dest_folder.joinpath(dest_filename).absolute()

            shutil.copy(str(image.filepath), str(dest_filepath))

            self.database.update_photo_newpath(image.tags["crypto_hash"], dest_filepath)

    def filter_photos(self, search_tags: Dict[str, str]) -> List[Photo]:
        filtered_photos = []
        # Code for filtering photos based on search tags
        return filtered_photos

    def display_photos(self, photos: List[Photo]) -> None:
        pass
        # Code for displaying selected photos


input_photo = "/home/miguel/sw/photo-organizer/data/Curling/IMG_4834.JPG"
