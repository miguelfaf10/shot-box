from pathlib import Path
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, DateTime, MetaData
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Dict, List

from utils import get_logger

# Create configure module   module_logger
logger = get_logger(__name__)

Base = declarative_base()


# Define database model for photos
class PhotoModel(Base):
    __tablename__ = "photos"
    id = Column(Integer, primary_key=True)
    original_filepath = Column(String, nullable=False)
    camera = Column(String)
    date_time = Column(DateTime)
    size = Column(Integer)
    width = Column(String)
    height = Column(String)
    resolution_units = Column(String)
    resolution_x = Column(Integer)
    resolution_y = Column(Integer)
    location_coord = Column(String)
    location = Column(String)
    perceptual_hash = Column(String, nullable=False)
    crypto_hash = Column(String, nullable=False, unique=True)
    new_filepath = Column(String, default="")
    n_perceptual_hash = Column(Integer, nullable=False, default=0)

    def __repr__(self):
        return f"Photo(origin={self.original_filepath})"


class PhotoDatabase:
    def __init__(self, db_path: Path):
        """Create the database tables initialize the database connection,
        and handles all database operations

        Args:
            db_path (Path): Path to the database file.
        """
        # Define database engine

        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{str(self.db_path)}")

        if self.db_exists():
            if not self.db_valid():
                logger.error(
                    f"Database file {self.db_path} doesn't contain valid database"
                )
        else:
            # Define base class for database models
            Base.metadata.create_all(bind=self.engine)

        self.session = sessionmaker(bind=self.engine)

    def db_exists(self):
        """Check if the database file exists.

        Returns:
            bool: True if the database file exists, False otherwise.
        """
        return bool(self.db_path.exists())

    def db_valid(self) -> bool:
        """Check if the database file contains a valid database structure.

        Returns:
            bool: True if the database structure is valid, False otherwise.
        """
        metadata = MetaData()
        metadata.reflect(bind=self.engine)

        tables_check = metadata.sorted_tables
        tables_model = PhotoModel.metadata.sorted_tables

        if len(tables_check) != len(tables_model):
            logger.debug(
                f"Database {str(db_path)} doesn't contain correct number of tables"
            )
            return False

        for k, table_model in enumerate(tables_model):
            if table_model.name != tables_check[k].name:
                logger.debug(
                    f"Database {str(db_path)} doesn't contain correct table's names"
                )
                return False

            if set(table_model.columns.keys()) != set(tables_check[0].columns.keys()):
                logger.debug(
                    f"Database {str(db_path)} doesn't contain correct table's names"
                )
                return False

        return True

    def add_photo(self, photo: PhotoModel):
        """Add a new photo to the database. It also verifies if an entry with
        same perceptual_hash key already exists and fills in the n_perceptual_hash
        field accordingly.

        Args:
            photo (PhotoModel): The photo object to be added to the database.

        Returns:
            int: The n_perceptual_hash value of the added photo.
        """
        with Session(self.engine) as session:
            # if entrie with same crypto_hash exists cancel
            if not (
                session.query(PhotoModel)
                .filter_by(crypto_hash=photo.crypto_hash)
                .one_or_none()
            ):
                photo.n_perceptual_hash = (
                    session.query(PhotoModel)
                    .filter_by(perceptual_hash=photo.perceptual_hash)
                    .count()
                )

                session.add(photo)
                session.commit()
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
        with Session(self.engine) as session:
            session.query(PhotoModel).filter_by(crypto_hash=crypto_hash).update(
                {"new_filepath": str(newpath)}
            )
            session.commit()

    def search_by_date(self, start_date, end_date=None):
        """Search photos in the database within a specified date range.

        Args:
            start_date: The start date of the range.
            end_date: The end date of the range (default: datetime.now()).

        Returns:
            List[PhotoModel]: A list of photos matching the date range.
        """
        if not end_date:
            end_date = datetime.now()
        with Session(self.engine) as session:
            photos = (
                session.query(PhotoModel)
                .filter(PhotoModel.date_time.between(start_date, end_date))
                .all()
            )

        return photos

    def search_by_perceptualhash(self, perceptual_hash):
        """Search a photo in the database by its perceptual_hash.

        Args:
            perceptual_hash: The perceptual hash key to search for.

        Returns:
            PhotoModel: The photo matching the perceptual hash, or None if not found.
        """
        with Session(self.engine) as session:
            photo = (
                session.query(PhotoModel)
                .filter_by(perceptual_hash=perceptual_hash)
                .one_or_none()
            )

        return photo

    def get_all(self) -> List[PhotoModel]:
        """Retrieve all photos from the database.

        Returns:
            List[PhotoModel]: A list of all photos in the database.
        """
        with Session(self.engine) as session:
            photos = session.query(PhotoModel).all()

        return photos

    def get_photos_paths(self) -> Dict[str, Dict[str, str]]:
        """Retrieve the repository file paths for all photos in the database.

        Returns:
        Dict[str, Dict[str, str]]: A dictionary mapping photo crypto_hash's
            to their corresponding file paths in repository and sizes.
        """
        photos = self.session.query(PhotoModel).all()
        return {
            photo.crypto_hash.hex(): {
                "new_filepath": photo.new_filepath,
                "size": photo.size,
            }
            for photo in photos
        }
