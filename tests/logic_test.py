import pytest
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd


from app.logic import Image, ImageOrganizer
from app.infra.repository.photos_database import PhotoDatabase

resources_image_files = "tests/resources/exif-samples/"
resources_image_data = "tests/resources/exif-samples/exif_data.xlsx"


class TestPhoto:
    @pytest.mark.parametrize(
        "image_type",
        (
            pytest.param([".jpg", ".jpeg"], id="From JPEG"),
            pytest.param([".png"], id="From PNG"),
            pytest.param([".gif"], id="From GIF"),
            pytest.param([".bmp"], id="From BPM"),
            pytest.param([".raw"], id="From RAW"),
            pytest.param([".tif", ".tiff"], id="From TIFF"),
            pytest.param([".heif"], id="From HEIF"),
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

            photo = Image(image_path)
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


class TestPhotoOrganizer:
    def test_get_info(self):
        pass
    def test_process_file(self):
        pass
    def test_filter_photos(self):
        pass
    def test_check_consistenty(self):
        pass
            
    def setUp(self, tmp_path):
            # Create a temporary directory for testing
            self.temp_dir = tmp_path
 

            # Create a temporary database file for testing
            self.temp_db_path = self.temp_dir / "test.db"

            # Initialize the PhotoOrganizer instance for testing
            self.organizer = ImageOrganizer(self.temp_dir, self.temp_db_path)

    def tearDown(self):
        # Remove the temporary directory and files after testing
        for file in self.temp_dir.glob("*"):
            file.unlink()
        self.temp_dir.rmdir()

    def test_get_info(self, tmp_path):
        # Create a mock PhotoDatabase instance and set its get_all method to return sample data
        self.organizer.db.get_all = MagicMock(return_value=[
            PhotoModel(size=100, new_filepath="path1"),
            PhotoModel(size=200, new_filepath="path2"),
            PhotoModel(size=300, new_filepath="path3")
        ])

        expected_result = {
            "total_photos": 3,
            "total_size": 600,
            "files_exist": 3
        }

        result = self.organizer.get_info()
        self.assertEqual(result, expected_result)

    @patch("app.logic.Photo")
    @patch("app.logic.PhotoDatabase")
    @patch("shutil.copy")
    def test_process_file(self, mock_copy, mock_database, mock_photo):
        # Create a mock Photo instance and set its tags
        mock_photo_instance = MagicMock()
        mock_photo.return_value = mock_photo_instance
        mock_photo_instance.tags = {
            "filepath": "image.jpg",
            "camera": "Canon",
            "datetime": datetime(2023, 5, 20, 10, 30),
            "size": 1000,
            "width": 1920,
            "height": 1080,
            "resolution_units": "dpi",
            "resolution_x": 300,
            "resolution_y": 300,
            "location_coord": "51.5074;-0.1278",
            "location_country": "UK",
            "location_region": "London",
            "location_city": "London",
            "perceptual_hash": "abc123",
            "crypto_hash": "def456"
        }

        # Create a mock PhotoDatabase instance and set its insert_photo method to return a value
        mock_database_instance = MagicMock()
        mock_database.return_value = mock_database_instance
        mock_database_instance.insert_photo.return_value = 1

        # Set up the expected destination filepath and folder
        expected_dest_folder = self.temp_dir / "2023" / "5"
        expected_dest_filename = "abc123_1.jpg"
        expected_dest_filepath = expected_dest_folder / expected_dest_filename

        # Run the process_file method
        result = self.organizer.process_file("image.jpg", do_copy=True)

        # Assert that the appropriate methods were called
        mock_photo.assert_called_once_with("image.jpg")
        mock_database.assert_called_once_with(self.temp_db_path)
        mock_database_instance.insert_photo.assert_called_once_with(
            original_filepath="image.jpg",
            camera="Canon",
            datetime=datetime(2023, 5, 20, 10, 30),
            file_type="jpg",
            size=1000,
            width=1920,
            height=1080,
            resolution_units="dpi",
            resolution_x