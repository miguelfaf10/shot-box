from dataclasses import dataclass, field
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut


@dataclass
class GeoLocation:
    longitude: float
    latitude: float
    country: str = field(init=False)
    state: str = field(init=False)
    city: str = field(init=False)

    def __post_init__(self) -> None:
        if self.latitude and self.longitude:
            country, state, city = get_location_from_gpscoord(
                self.latitude, self.longitude
            )
        else:
            country, state, city = ("unknown", "unknown", "unknown")
        self.country = country
        self.state = state
        self.city = city


def get_location_from_gpscoord(latitude, longitude):
    if not latitude or not longitude:
        return "unknown"

    try:
        geolocator = Nominatim(user_agent="my_app", timeout=1)

        location = geolocator.reverse(f"{latitude}, {longitude}", exactly_one=True)
        address = location.raw["address"]
        city = address.get("city")
        region = address.get("state")
        country = address.get("country")
        return (country, region, city)
    except Exception as E:
        return "unknown"
