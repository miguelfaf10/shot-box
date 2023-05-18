from app.infra.configs.base import Base
from sqlalchemy import create_engine, Column, Integer, String, DateTime, MetaData


# Define database model for photos
if "photos" not in Base.metadata.tables:

    class Photos(Base):
        __tablename__ = "photos"
        id = Column(Integer, primary_key=True)
        original_filepath = Column(String, nullable=False)
        camera = Column(String)
        date_time = Column(DateTime)
        file_type = Column(String)
        size = Column(Integer)
        width = Column(Integer)
        height = Column(Integer)
        resolution_units = Column(String)
        resolution_x = Column(Integer)
        resolution_y = Column(Integer)
        location_coord = Column(String)
        location_country = Column(String)
        location_region = Column(String)
        location_city = Column(String)
        perceptual_hash = Column(String, nullable=False)
        crypto_hash = Column(String, nullable=False, unique=True)
        new_filepath = Column(String, default="")
        n_perceptual_hash = Column(Integer, nullable=False, default=0)

        def __repr__(self):
            return f"Photo(origin={self.original_filepath})"
