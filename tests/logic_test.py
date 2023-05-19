import yaml
import itertools
import pytest
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

from app.logic import Image, ImageOrganizer
from app.infra.repository.photos_database import PhotoDatabase


# configuration parameters
with open("app/config.yaml") as file:
    config = yaml.safe_load(file)

DB_FILE = config["database"]["file"]
DB_FOLDER = config["database"]["folder"]
IMAGE_EXTS = list(
    itertools.chain.from_iterable(
        values for values in config["image"]["types"].values()
    )
)

params_image_type = [
    pytest.param(ext, id=f"From {type}")
    for type, ext in config["image"]["types"].items()
]


@pytest.fixture
def images_folder():
    return "tests/resources/exif-samples/"


@pytest.fixture
def data_file():
    return "tests/resources/exif-samples/exif_data.xlsx"


@pytest.fixture(params=params_image_type)
def allimage_paths(images_folder, request):
    return [
        file_path
        for file_path in Path(images_folder).glob("**/*")
        if file_path.is_file() and file_path.suffix.lower() in request.param
    ]


@pytest.fixture
def allimage_data(data_file):
    return pd.read_excel(data_file).replace({np.nan: None})


class TestPhoto:
    def test_generate_tags(self, allimage_paths, allimage_data):
        for image_path in allimage_paths:
            print("Image file being processed: ", image_path.name)
            image = Image(image_path)
            data = allimage_data[
                allimage_data["original_filepath"].str.contains(
                    image_path.name, regex=False
                )
            ]

            # Assert individual tags
            assert image.tags["filepath"] == str(
                Path(data["original_filepath"].values[0]).absolute()
            )
            assert image.tags["camera"] == data["camera"].values[0]
            assert image.tags["datetime"] == (
                datetime.strptime(data["datetime"].values[0], "%Y-%m-%d %H:%M:%S.%f")
                if data["datetime"].values[0]
                else None
            )
            assert image.tags["size"] == data["size"].values[0]
            assert image.tags["width"] == data["width"].values[0]
            assert image.tags["height"] == data["height"].values[0]
            assert image.tags["resolution_units"] == data["resolution_units"].values[0]
            assert image.tags["resolution_x"] == data["resolution_x"].values[0]
            assert image.tags["resolution_y"] == data["resolution_x"].values[0]
            assert image.tags["location_coord"] == data["location_coord"].values[0]
            assert image.tags["location_country"] == data["location_country"].values[0]
            assert image.tags["location_region"] == data["location_region"].values[0]
            assert image.tags["location_city"] == data["location_city"].values[0]
            assert image.tags["perceptual_hash"] == data["perceptual_hash"].values[0]
            assert image.tags["crypto_hash"] == data["crypto_hash"].values[0]


# @pytest.fixture
# def image_repo(tmp_path):
#     tmp_path.mkdir()
#     tmp_path.joinpath(".photo-organizer/")


# class TestPhotoOrganizer:
#     def test_get_info(self, tmp_path):
#         # Create a mock PhotoDatabase instance and set its get_all method to return sample data
#         self.organizer.db.get_all = MagicMock(
#             return_value=[
#                 ImageModel(size=100, new_filepath="path1"),
#                 ImageModel(size=200, new_filepath="path2"),
#                 ImageModel(size=300, new_filepath="path3"),
#             ]
#         )

#         expected_result = {"total_photos": 3, "total_size": 600, "files_exist": 3}

#         result = self.organizer.get_info()
#         self.assertEqual(result, expected_result)


#     @patch("app.logic.Photo")
#     @patch("app.logic.PhotoDatabase")
#     @patch("shutil.copy")
#     def test_process_file(self, mock_copy, mock_database, mock_photo):
#         # Create a mock Photo instance and set its tags
#         mock_photo_instance = MagicMock()
#         mock_photo.return_value = mock_photo_instance
#         mock_photo_instance.tags = {
#             "filepath": "image.jpg",
#             "camera": "Canon",
#             "datetime": datetime(2023, 5, 20, 10, 30),
#             "size": 1000,
#             "width": 1920,
#             "height": 1080,
#             "resolution_units": "dpi",
#             "resolution_x": 300,
#             "resolution_y": 300,
#             "location_coord": "51.5074;-0.1278",
#             "location_country": "UK",
#             "location_region": "London",
#             "location_city": "London",
#             "perceptual_hash": "abc123",
#             "crypto_hash": "def456"
#         }

#         # Create a mock PhotoDatabase instance and set its insert_photo method to return a value
#         mock_database_instance = MagicMock()
#         mock_database.return_value = mock_database_instance
#         mock_database_instance.insert_photo.return_value = 1

#         # Set up the expected destination filepath and folder
#         expected_dest_folder = self.temp_dir / "2023" / "5"
#         expected_dest_filename = "abc123_1.jpg"
#         expected_dest_filepath = expected_dest_folder / expected_dest_filename

#         # Run the process_file method
#         result = self.organizer.process_file("image.jpg", do_copy=True)

#         # Assert that the appropriate methods were called
#         mock_photo.assert_called_once_with("image.jpg")
#         mock_database.assert_called_once_with(self.temp_db_path)
#         mock_database_instance.insert_photo.assert_called_once_with(
#             original_filepath="image.jpg",
#             camera="Canon",
#             datetime=datetime(2023, 5, 20, 10, 30),
#             file_type="jpg",
#             size=1000,
#             width=1920,
#             height=1080,
#             resolution_units="dpi",
#             resolution_x
