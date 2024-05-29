from enum import Enum
from fastapi import FastAPI
from pydantic import BaseModel
from geopy.distance import geodesic     # type:ignore
import pandas as pd
import re

class Status(str, Enum):
    "Valid Status values for mobile food facility permits"
    requested = 'REQUESTED'
    expired = 'EXPIRED'
    suspend = 'SUSPEND'
    approved = 'APPROVED'
    issued = 'ISSUED'

class Applicant(BaseModel):
    "Mobile food facility permit applicant name"
    applicant: str

class Street(BaseModel):
    "Street name of the location of a mobile food facility"
    name: str

class Location(BaseModel):
    "Geographical location"
    latitude: float
    longitude: float

    
def clean_dataframe(df: pd.DataFrame):
    """Given a DataFrame `df` of mobile food facilities, strip any fields with NaN values
    and return a list of cleanednn row dicts."""
    return list(map(lambda record: { k:v for (k, v) in record.items() if v==v}, df.to_dict(orient='records')))
                

def street_name(address: str) -> str:
    """Extract an UPPERCASE street name from the provided address.
    If there's no obvious number out front, just return
    the original address (uppercase). This works sometimes."""
    address = address.upper()
    m = re.match('^\\d[\\w]*\\s+(.+)$', address)
    return m.group(1) if m else address

    
app = FastAPI()

permits = pd.read_csv('resources/Mobile_Food_Facility_Permit.csv')
"""The mobile food facility permit dataset, as a pandas DataFrame"""


@app.post("/by_applicant")
async def by_applicant(applicant: Applicant, status: Status | None = None):
    """Return a list of mobile food facilities matching the provided vendor name.
    If `status` is `not None`, constrain to only facilities with the provided status."""
    matching = permits[permits['Applicant'] == applicant.applicant]
    if status:
        matching = matching[matching['Status'] == status.value]
    return clean_dataframe(matching)


@app.post("/by_street")
async def by_street(street: Street):
    """Return a list of mobile food facilities matching the (possibly incomplete) street name."""
    name = street.name.upper()
    matching = permits[permits['Address'].apply(street_name).str.startswith(name)]
    return clean_dataframe(matching)


@app.post("/by_location")
async def closest_n(location: Location, only_approved: bool = True, num_matches: int = 5):
    """Find the closest `num_matches` mobile food facilities to the provided location.
    If `only_approved` is `True`, return only approved facilities."""
    allowed_permits = permits[permits['Status'] == Status.approved.value] if only_approved else permits
    center = (location.latitude, location.longitude)
    distances = [(i, geodesic(center, (lat, lon)).m) for (i, lat, lon)
        in zip(allowed_permits.index, allowed_permits['Latitude'], allowed_permits['Longitude'])]
    ordered_distances = sorted(distances, key=lambda idpair: idpair[1])
    take_indices = [i for (i, d) in ordered_distances[:num_matches]]
    return clean_dataframe(allowed_permits.loc[take_indices, :])
