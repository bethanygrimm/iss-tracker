from iss_tracker import parse_epoch, return_state_vectors, return_epochs, return_speed, return_location, return_specific_epoch, return_specific_epoch_speed, return_specific_epoch_location, find_data_range, closest_epoch
import requests
import pytest
import time
import sys
import math
import redis

#Test parse_epoch
def test_parse_epoch():
    assert(parse_epoch("2025-001T00:00:00.000Z") == 1735689600.0)
    assert(parse_epoch("a") == 0.0)
    assert(parse_epoch(5) == 0.0)

#Use requests.get to test methods housed in Flask routes
response1 = requests.get('http://127.0.0.1:5000/epochs')
response2 = requests.get('http://127.0.0.1:5000/epochs/0')
response3 = requests.get('http://127.0.0.1:5000/epochs/0/speed')
response4 = requests.get('http://127.0.0.1:5000/epochs?limit=0&offset=1')
response5 = requests.get('http://127.0.0.1:5000/epochs/range')
response6 = requests.get('http://127.0.0.1:5000/now')
response7 = requests.get('http://127.0.0.1:5000/epochs/0/location')

#Test that return_state_vectors returns a dict with at least one of the required keys
def test_return_state_vectors():
    assert(isinstance(return_state_vectors(0.0), dict) == True)
    assert(isinstance((return_state_vectors(0.0)['EPOCH']), str) == True)

#Test that return_speed returns a dict with at least one of the required keys
def test_return_state_vectors():
    assert(isinstance(return_speed(0.0), dict) == True)
    assert(isinstance((return_speed(0.0)['Instantaneous Speed (km/s)']),
                      str) == True)

#Test that return_location returns a dict with at least one of the required keys
def test_return_state_vectors():
    assert(isinstance(return_location(0.0), dict) == True)
    assert(isinstance((return_location(0.0)['Geolocation']), str) == True)

#Test that return_epochs does return a list of dicts (for /epochs) and one dict (for /epochs?limit=0&offset=1')
def test_return_epochs():
    assert(isinstance((response1.json()), list) == True)
    assert(len(response4.json()) == 1)

#Test return_specific_epoch and that it contains the key 'EPOCH'. If so, it should contain the other keys
def test_return_specific_epoch():
    assert(response1.json()[0] == response2.json())
    assert(response2.json() == response4.json()[0])
    assert(isinstance((response2.json()['EPOCH']), str) == True)

#Test that instantaneous speed consists of a key 'Instantaneous Speed (km/s)' and a float value
def test_return_specific_epoch_speed():
    assert(isinstance((response3.json()), dict) == True)
    assert(isinstance((response3.json()['Instantaneous Speed (km/s)']), 
                      float) == True)

#Test that location includes a key 'Altitude' and a float value, and a key 'Geolocation'
def test_return_specific_epoch_speed():
    assert(isinstance((response7.json()), dict) == True)
    assert(isinstance((response7.json()['Altitude']), float) == True)
    assert(isinstance((response7.json()['Geolocation']), str) == True)

#Test that requesting data range returns a string
def test_find_data_range():
    assert(response5.status_code == 200)
    assert(isinstance(response5.content, bytes) == True)

#Test that route /now returns correct kind of data
def test_closest_epoch():
    assert(response6.status_code == 200)
    assert(isinstance((response6.json()), dict) == True)
    assert(isinstance((response6.json()['EPOCH']), str) == True)
    assert(isinstance((response6.json()['Instantaneous Speed (km/s)']), 
                      float) == True)
