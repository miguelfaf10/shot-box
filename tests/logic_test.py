import pytest
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd


from app.logic import Photo, PhotoOrganizer
from app.infra.repository.photos_database import PhotoDatabase

resources_image_files = "tests/resources/exif-samples/"
resources_image_data = "tests/resources/exif-samples/exif_data.xlsx"


class TestPhoto:
    @pytest.mark.parametrize(
        ("image_type"),
        (
            ([".jpg", ".jpeg"]),
            ([".png"]),
            ([".gif"]),
            ([".bmp"]),
            ([".raw"]),
            ([".tif", ".tiff"]),
            ([".heif"]),
        ),
    )
    def test_generate_tags(self, image_type):
        image_paths = [
            file_path
            for file_path in Path(resources_image_files).glob("**/*")
            if file_path.is_file() and file_path.suffix.lower() in image_type
        ]

        image_data = pd.read_excel(resources_image_data).replace({np.nan: None})

        for image_path in image_paths:
            if image_path.name == "Crémieux11.tiff":
                pass

            photo = Photo(image_path)
            print("Image file being processed: ", image_path.name)

            data = image_data[
                image_data["original_filepath"].str.contains(
                    image_path.name, regex=False
                )
            ]

            # Assert individual tags
            assert photo.tags["filepath"] == str(
                Path(data["original_filepath"].values[0]).absolute()
            )
            assert photo.tags["camera"] == data["camera"].values[0]
            assert photo.tags["datetime"] == (
                datetime.strptime(data["datetime"].values[0], "%Y-%m-%d %H:%M:%S.%f")
                if data["datetime"].values[0]
                else None
            )
            assert photo.tags["size"] == data["size"].values[0]
            assert photo.tags["width"] == data["width"].values[0]
            assert photo.tags["height"] == data["height"].values[0]
            assert photo.tags["resolution_units"] == data["resolution_units"].values[0]
            assert photo.tags["resolution_x"] == data["resolution_x"].values[0]
            assert photo.tags["resolution_y"] == data["resolution_x"].values[0]
            assert photo.tags["location_coord"] == data["location_coord"].values[0]
            assert photo.tags["location_country"] == data["location_country"].values[0]
            assert photo.tags["location_region"] == data["location_region"].values[0]
            assert photo.tags["location_city"] == data["location_city"].values[0]
            assert photo.tags["perceptual_hash"] == data["perceptual_hash"].values[0]
            assert photo.tags["crypto_hash"] == data["crypto_hash"].values[0]


# class TestPhotoOrganizer(unittest.TestCase):
