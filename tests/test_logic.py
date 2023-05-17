import unittest
from pathlib import Path
from itertools import cycle
from datetime import datetime
from unittest.mock import patch

print(__name__)

import pandas as pd
from logic import Photo, PhotoOrganizer

resources_image_files = "tests/resources/exif-samples/"
resources_image_data = "tests/resources/exif-samples/exif_data.xlsx"


class TestPhoto(unittest.TestCase):
    def test_generate_tags_jpg(self):
        image_paths = [
            file_path
            for file_path in Path(resources_image_files).glob("**/*")
            if file_path.is_file() and file_path.suffix.lower() in [".jpg", ".jpeg"]
        ]

        image_data = pd.read_csv(resources_image_data)

        image_data[image_data["original_filepath"].str.contains(image_paths[10].name)]

        for image_path in image_paths:
            photo = Photo(image_path)

            data = image_data[
                image_data["original_filepath"].str.contains(image_path.name)
            ]

            # Assert individual tags
            self.assertEqual(photo.tags["filepath"], data["filepath"].values[0])
            self.assertEqual(photo.tags["camera"], data["camera"].values[0])
            self.assertEqual(photo.tags["date_time"], data["date_time"].values[0])
            self.assertEqual(photo.tags["size"], data["size"].values[0])
            self.assertEqual(photo.tags["width"], data["width"].values[0])
            self.assertEqual(photo.tags["height"], data["height"].values[0])
            self.assertEqual(
                photo.tags["resolution_units"], data["resolution_units"].values[0]
            )
            self.assertEqual(photo.tags["resolution_x"], data["resolution_x"].values[0])
            self.assertEqual(photo.tags["resolution_y"], data["resolution_x"].values[0])
            self.assertEqual(
                photo.tags["location_coord"], data["location_coord"].values[0]
            )
            self.assertEqual(
                photo.tags["location_country"], data["location_country"].values[0]
            )
            self.assertEqual(
                photo.tags["location_region"], data["location_region"].values[0]
            )
            self.assertEqual(
                photo.tags["location_city"], data["loccation_city"].values[0]
            )
            self.assertEqual(
                photo.tags["perceptual_hash"], data["perceptual_hash"].values[0]
            )
            self.assertEqual(photo.tags["crypto_hash"], data["crypto_hash"].values[0])
