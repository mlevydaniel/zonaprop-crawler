from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date


@dataclass
class Listing:
    """
    Domain model representing a single real-estate listing on Zonaprop.

    The class starts with core attributes scraped from search result cards
    and is later enriched with additional details obtained from the listing
    detail page.
    """
    id: str
    date: date
    price: str
    currency: str
    expenses: Optional[str] = None
    location_address: Optional[str] = None
    location_area: Optional[str] = None
    features: List[str] = field(default_factory=list)
    description: Optional[str] = None
    url: Optional[str] = None
    total_area: Optional[str] = None
    covered_area: Optional[str] = None
    rooms: Optional[str] = None
    bathrooms: Optional[str] = None
    parking_spaces: Optional[str] = None
    bedrooms: Optional[str] = None
    age: Optional[str] = None
    publisher_name: Optional[str] = None
    publisher_id: Optional[str] = None
    publisher_url: Optional[str] = None

    def update_details(self, details: dict):
        """
        Update this listing in-place with information.

        Only attributes that already exist on `Listing` are set; unknown
        keys in `details` are ignored (a warning is printed).

        Args:
            details: Dictionary where keys correspond to attribute names
                on the `Listing` class and values contain the new data.
        """
        for key, value in details.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                print(f"Warning: Attribute '{key}' not found in Listing class")

    def to_dict(self):
        """
        Convert the listing to a JSON-serializable dictionary.

        Private attributes and `None` values are omitted. The `date`
        attribute is converted to ISO 8601 string representation.

        Returns:
            A dictionary representation of the listing suitable for JSON.
        """
        result = {
            key: value for key, value in self.__dict__.items()
            if not key.startswith('_') and value is not None
        }
        if 'date' in result:
            result['date'] = result['date'].isoformat()
        return result
