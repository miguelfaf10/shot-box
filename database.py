from pathlib import Path

from sqlalchemy import create_engine, Column, Integer, String, DateTime, LargeBinary
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Dict, List

from utils import get_logger

# Create configure module   module_logger
logger = get_logger()

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
    def __init__(self, path: Path):
        """Create the database tables."""
        # Define database engine

        if path.exists():
            logger.info(f"Opening existant {path.name}.")
        else:
            logger.info(f"Creating database file {path.name}.")

        self.engine = create_engine(f"sqlite:///{str(path)}")

        # Define session factory
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

    def search_photos(self, tags):
        """Search for photos by tag."""
        return (
            self.session.query(PhotoModel)
            .filter(PhotoModel.tags.like(f"%{tags}%"))
            .all()
        )

    def get_all(self) -> List[PhotoModel]:
        return self.session.query(PhotoModel).all()

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
