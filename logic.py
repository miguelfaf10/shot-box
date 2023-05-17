from pathlib import Path
from datetime import datetime
from pprint import pformat
from typing import Dict, List

import shutil

import exifread
import imagehash

from infra.repository.photos_database import PhotoDatabase
from infra.entities.photos import Photos
from utils import get_logger, scan_folder
from utils import get_location_from_gpscoord, get_gpscoord_from_exif
from utils import generate_crypto_hash, generate_perceptual_hash

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
                location_str = "unknown"
                location_coord_str = "unknown"
        else:
            location_str = "unknown"
            location_coord_str = "unknown"

        tags["location_coord"] = location_coord_str
        if location_str != "unknown":
            tags["location_country"] = location_str.split(";")[0]
            tags["location_region"] = location_str.split(";")[1]
            tags["location_city"] = location_str.split(";")[2]
        else:
            tags["location_country"] = None
            tags["location_region"] = None
            tags["location_city"] = None

        # generate image hash ids
        tags["perceptual_hash"] = generate_perceptual_hash(self.filepath)
        tags["crypto_hash"] = generate_crypto_hash(self.filepath)

        return tags


class PhotoOrganizer:
    def __init__(self, repo_path: Path, db_path: Path):
        self.repo_path = repo_path
        self.db_path = db_path
        self.db = PhotoDatabase(self.db_path)

    def get_info(self):
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
        image_obj = Photo(image_path)

        # create image database object
        image_db = Photos(
            original_filepath=image_obj.tags["filepath"],
            camera=image_obj.tags["camera"],
            date_time=image_obj.tags["datetime"],
            size=image_obj.tags["size"],
            width=image_obj.tags["width"],
            height=image_obj.tags["height"],
            resolution_units=image_obj.tags["resolution_units"],
            resolution_x=image_obj.tags["resolution_x"],
            resolution_y=image_obj.tags["resolution_y"],
            location_coord=image_obj.tags["location_coord"],
            location_country=image_obj.tags["location_country"],
            location_region=image_obj.tags["location_region"],
            location_city=image_obj.tags["location_city"],
            perceptual_hash=image_obj.tags["perceptual_hash"],
            crypto_hash=image_obj.tags["crypto_hash"],
            new_filepath="",
            n_perceptual_hash=0,
        )

        # add image db object into database
        n_perceptualhash = self.db.insert_photo(image_db)
        if n_perceptualhash is None:
            return False

        # copy image files into repository
        if do_copy:
            # Determine the destination folder based on the image's datetime metadata
            # or use a default folder if the datetime is not available
            dest_folder = (
                self.repo_path.joinpath(
                    str(image_obj.tags["datetime"].year),
                    str(image_obj.tags["datetime"].month),
                )
                if image_obj.tags.get("datetime")
                else self.repo_path.joinpath("unknown", "unknown")
            )
            dest_folder.mkdir(parents=True, exist_ok=True)

            # Generate the destination filename using the perceptual hash and n_perceptualhash values
            dest_name = f"{image_obj.tags['perceptual_hash']}_{n_perceptualhash}"
            extension = Path(image_obj.tags["filepath"]).suffix[1:]

            # Construct the destination filepath by joining the destination folder and filename
            dest_filename = f"{dest_name}.{extension.upper()}"
            dest_filepath = dest_folder.joinpath(dest_filename).absolute()

            if not dest_filepath.exists():
                try:
                    # Copy the image file from the original filepath to the destination filepath
                    shutil.copy(str(image_obj.tags["filepath"]), str(dest_filepath))

                    # Update the new_filepath attribute of the image in the database
                    self.db.update_newpath(image_obj.tags["crypto_hash"], dest_filepath)
                except Exception:
                    logger.error(Exception)
                    return False
            else:
                logger.error(f"File {dest_filepath.name} already exists in repository")
                return False

            return True

    def filter_photos(self, search_tags: Dict[str, str]) -> List[Photo]:
        if search_tags.get("country"):
            filtered_photos = self.db.search_by_location(country=search_tags["country"])

        return filtered_photos

    def display_photos(self, photos: List[Photo]) -> None:
        pass
        # Code for displaying selected photos

    def check_consistency(self, image_ext):
        rows = self.db.get_all()

        exist_db_not_copied = []
        exist_db_not_repo = []
        exist_repo_incorrect_image = []
        exist_repo_not_db = scan_folder(self.repo_path, image_ext)

        for row in rows:
            # check db entries
            if row.new_filepath:
                # file has been copied

                if Path(row.new_filepath).exists():
                    # file exists in new location
                    if Path(row.new_filepath).stem.split("_")[
                        0
                    ] == generate_perceptual_hash(Path(row.new_filepath)):
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
