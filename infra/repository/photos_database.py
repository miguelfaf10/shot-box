from pathlib import Path
from datetime import datetime
from typing import List, Dict

from sqlalchemy import MetaData
from infra.configs.base import Base
from infra.configs.connection import DBConnectionHandler
from infra.entities.photos import Photos

from utils import get_logger

logger = get_logger(__name__)


class PhotoDatabase:
    def __init__(self, db_path: Path):
        """Create the database tables initialize the database connection,
        and handles all database operations

        Args:
            db_path (Path): Path to the database file.
        """
        self.db_path = db_path

        if not self.db_path.exists():
            # Create database
            with DBConnectionHandler(self.db_path) as db:
                Base.metadata.create_all(bind=db.get_engine())
            logger.error(f"Database {self.db_path} created")
        elif not self.db_valid():
            logger.error(f"Database {self.db_path} not valid")
        else:
            logger.error(f"Database {self.db_path} exists and is valid")

    def db_valid(self) -> bool:
        """Check if the database file contains a valid database structure.

        Returns:
            bool: True if the database structure is valid, False otherwise.
        """
        metadata = MetaData()
        with DBConnectionHandler(self.db_path) as db:
            metadata.reflect(bind=db.get_engine())

        tables_check = metadata.sorted_tables
        tables_model = Photos.metadata.sorted_tables

        if len(tables_check) != len(tables_model):
            logger.debug(
                f"Database {str(self.db_path)} doesn't contain correct number of tables"
            )
            return False

        for k, table_model in enumerate(tables_model):
            if table_model.name != tables_check[k].name:
                logger.debug(
                    f"Database {str(self.db_path)} doesn't contain correct table's names"
                )
                return False

            if set(table_model.columns.keys()) != set(tables_check[0].columns.keys()):
                logger.debug(
                    f"Database {str(self.db_path)} doesn't contain correct table's names"
                )
                return False

        return True

    def insert_photo(self, photo: Photos):
        """Insert a new photo to the database. It first verifies if an entry with
        same perceptual_hash key already exists and fills in the n_perceptual_hash
        field accordingly.

        Args:
            photo (Photos): The photo object to be added to the database.

        Returns:
            int: The n_perceptual_hash value of the added photo.
        """
        with DBConnectionHandler(self.db_path) as db:
            # if entrie with same crypto_hash exists cancel
            if not (
                db.session.query(Photos)
                .filter_by(crypto_hash=photo.crypto_hash)
                .one_or_none()
            ):
                photo.n_perceptual_hash = (
                    db.session.query(Photos)
                    .filter_by(perceptual_hash=photo.perceptual_hash)
                    .count()
                )

                db.session.add(photo)
                db.session.commit()
                logger.info(f"Added {photo.original_filepath} to database")
                return photo.n_perceptual_hash
            else:
                return None

    def update_photo_newpath(self, crypto_hash: str, newpath: Path):
        """Update the new filepath of a photo in the database, which is queried
        using the unique field crypto_hash.

        Args:
            crypto_hash: The crypto_hash of the photo.
            newpath: The new filepath to be updated.
        """
        with DBConnectionHandler(self.db_path) as db:
            db.session.query(Photos).filter_by(crypto_hash=crypto_hash).update(
                {"new_filepath": str(newpath)}
            )
            db.session.commit()

    def search_by_date(self, start_date, end_date=None):
        """Search photos in the database within a specified date range.

        Args:
            start_date: The start date of the range.
            end_date: The end date of the range (default: datetime.now()).

        Returns:
            List[Photos]: A list of photos matching the date range.
        """
        if not end_date:
            end_date = datetime.now()
        with DBConnectionHandler(self.db_path) as db:
            photos = (
                db.session.query(Photos)
                .filter(Photos.date_time.between(start_date, end_date))
                .all()
            )

        return photos

    def search_by_perceptualhash(self, perceptual_hash):
        """Search a photo in the database by its perceptual_hash.

        Args:
            perceptual_hash: The perceptual hash key to search for.

        Returns:
            Photos: The photo matching the perceptual hash, or None if not found.
        """
        with DBConnectionHandler(self.db_path) as db:
            photo = (
                db.session.query(Photos)
                .filter_by(perceptual_hash=perceptual_hash)
                .one_or_none()
            )

        return photo

    def get_all(self) -> List[Photos]:
        """Retrieve all photos from the database.

        Returns:
            List[Photos]: A list of all photos in the database.
        """
        with DBConnectionHandler(self.db_path) as db:
            photos = db.session.query(Photos).all()

        return photos

    def get_photos_paths(self) -> Dict[str, Dict[str, str]]:
        """Retrieve the repository file paths for all photos in the database.

        Returns:
        Dict[str, Dict[str, str]]: A dictionary mapping photo crypto_hash's
            to their corresponding file paths in repository and sizes.
        """
        with DBConnectionHandler(self.db_path) as db:
            photos = db.session.query(Photos).all()
        return {
            photo.crypto_hash.hex(): {
                "new_filepath": photo.new_filepath,
                "size": photo.size,
            }
            for photo in photos
        }
