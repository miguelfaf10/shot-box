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
    original_filepath = Column(String)
    new_filepath = Column(String)
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
    perceptual_hash = Column(String)
    crypto_hash = Column(String)


class PhotoDatabase:
    def __init__(self, db_path: Path):
        """Create the database tables."""
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

    def add_photo(self, photo: PhotoModel):
        """Add a new photo to the database."""
        with Session(self.engine) as session:
            if (
                session.query(PhotoModel)
                .filter_by(crypto_hash=photo.crypto_hash)
                .first()
                is None
            ):
                session.add(photo)
                session.commit()
                return True
            else:
                return False

    def update_photo_newpath(self, crypto_hash, newpath):
        with Session(self.engine) as session:
            photo = session.query(PhotoModel).filter_by(crypto_hash=crypto_hash).one()
            photo.new_filepath = str(newpath)
            session.commit()

    def search_by_date(self, start_date, end_date=None):
        if not end_date:
            end_date = datetime.now()
        with Session(self.engine) as session:
            photos = (
                session.query(PhotoModel)
                .filter(PhotoModel.date_time.between(start_date, end_date))
                .all()
            )

        return photos

    def search_photos(self, tags):
        """Search for photos by tag."""
        return (
            self.session.query(PhotoModel)
            .filter(PhotoModel.tags.like(f"%{tags}%"))
            .all()
        )

    def get_all(self) -> List[PhotoModel]:
        with Session(self.engine) as session:
            photos = session.query(PhotoModel).all()

        return photos

    def get_photos_paths(self) -> Dict[str, Dict[str, str]]:
        """Returns a dictionary with photo data."""
        photos = self.session.query(PhotoModel).all()
        return {
            photo.crypto_hash.hex(): {
                "new_filepath": photo.new_filepath,
                "size": photo.size,
            }
            for photo in photos
        }

    def db_exists(self):
        return bool(self.db_path.exists())

    def db_valid(self) -> bool:
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
