from fastapi.testclient import TestClient
from typing import Any
import re

from .api import app, street_name

client = TestClient(app)

def test_by_applicant_simple():
    """Retrieve facilities for a specific applicant known to be in the provided dataset."""
    name = "Let's Be Frank"             # hi Frank
    response = client.post('/by_applicant', json={"applicant": name})
    assert len(response.json()) == 2
    assert all(map(lambda elem: elem['Applicant'] == name, response.json())), 'some returned item has non-matching Applicant'
    assert all(map(lambda elem: elem['Status'] == 'EXPIRED', response.json())), 'some returned item has unexpected status'

def test_by_applicant_status_match():
    """Retrieve facilities for a specific applicant, specifying permit status."""
    name = "Let's Be Frank"
    response = client.post('/by_applicant?status=EXPIRED', json={"applicant": name})
    assert len(response.json()) == 2
    
def test_by_applicant_no_status_match():
    """Retrieve facilities for a specific applicant but with a non-matching permit status."""
    name = "Let's Be Frank"
    response = client.post('/by_applicant?status=APPROVED', json={"applicant": name})
    assert len(response.json()) == 0


def extract_street(element: dict[str, Any]) -> str | None:
    """Extract the street name from an address element in the provided dict, e.g., 123 BARKSDALE CT -> BARKSDALE."""
    m = re.match('^\\d[\\w]+\\s+(\\w+)', element['Address'])
    return m.group(1) if m else None

def test_by_street_partial_mult_matches():
    """Retrieve facilities on a named street, where the provided name is short enough to be ambiguous."""
    response = client.post('/by_street', json={"name": "HA"})
    assert len(response.json()) == 7
    streets = set(map(extract_street, response.json()))
    assert streets == {'HARBOR', 'HARRISON', 'HAYES'}
    
def test_by_street_partial_sing_match():
    """Retrieve facilities on a named street, where the provided name is long enough to be unique."""
    response = client.post('/by_street', json={"name": "HARR"})
    assert len(response.json()) == 5
    streets = set(map(extract_street, response.json()))
    assert streets == {'HARRISON'}

def test_by_street_complete():
    """Retrieve facilities on a named street."""
    response = client.post('/by_street', json={"name": "HARBOR "})
    assert len(response.json()) == 1
    streets = set(map(extract_street, response.json()))
    assert streets == {'HARBOR'}

def test_by_location():
    """Return the nearest 5 facilities to the provided location."""
    response = client.post('/by_location', json={"latitude": 37.727, "longitude": -122.433}) # Mission near Cotter
    assert len(response.json()) == 5
    streets = set(map(extract_street, response.json()))
    # not obvious but matches with cursory manually inspected results
    assert streets == {None, 'ALEMANY', 'BAY', 'CAPITOL'}

    # move to a different place, we should get different results
    response2 = client.post('/by_location', json={"latitude": 37.77, "longitude": -122.45})
    assert len(response2.json()) == 5
    streets = set(map(extract_street, response2.json()))
    assert streets == {'EDDY', 'FELL', 'OTIS', 'PARNASSUS', '20TH'} # S of the Panhandle

    
def test_by_location_any():
    """Return the nearest 5 facilities to the provided location."""
    response = client.post('/by_location?only_approved=0', json={"latitude": 37.727, "longitude": -122.433}) # Mission near Cotter
    assert len(response.json()) == 5
    streets = set(map(extract_street, response.json()))
    # not obvious but matches with cursory manually inspected results
    # in particular, two 4xxx block Mission are status REQUESTED
    assert streets == {'ALEMANY', 'GENEVA', 'MISSION'}


def test_street_name():
    """Test the street name extraction. It works, kinda sorta."""
    assert street_name('221B Baker St').startswith('BAKER')
    assert street_name('1000 Mammon Ln').startswith('MAMMON')
    assert street_name('1640 Riverside Dr').startswith('RIVERSIDE')
    assert street_name('Assessors Block 3905/Lot01').startswith('ASSESSORS BLOCK')    
