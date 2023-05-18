from unittest import mock
from mock_alchemy.mocking import UnifiedAlchemyMagicMock
from infra.entities.photos import Photos


session = UnifiedAlchemyMagicMock(
    data = [
        (
            [mock.call.query(Photos),
             moch.call.filter()],
            [Photos(id=0,
                    original_filpath='',
                    camera='',
                    date_time=datetime(),
                    size=1234,
                    width=10,
                    height=10,
                    resolution_units='px/cm',
                    resolution_x=1000,
                    resolution_y=1000,
                    location_coord='23.233,-65.656',
                    location_country=,
                    location_region='Portugal',
                    location_city='Porto',
                    perceptual_hash=,
                    crypto_hash=,
                    new_filepath=,
                    n_perceptual_hash=,
                    )]
        )
    ]
)