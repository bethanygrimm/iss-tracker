#!/usr/bin/env python3
import requests
import logging
logging.basicConfig(level='DEBUG')
import xml
import xmltodict #xmltodict must be installed on pip3
import argparse
from typing import List
from typing import Tuple
import time
import sys
import math
from flask import Flask, request
import redis
import json
from astropy import coordinates
from astropy import units
from astropy.time import Time
from geopy.geocoders import Nominatim

#Initialize instance of Flask object
app = Flask(__name__)
#Initialize instance of Redis object
#path /data is mounted onto the port when Redis is initialized
rd = redis.Redis(host='redis-db', port=6379, db=0)

def parse_epoch(epoch: str) -> float:
    '''
    This function converts time from NASA's epoch format to float epoch format
    (that is, the number of seconds since January 1, 1970).

    Args:
        epoch (str): timestamp in NASA's epoch format as a string

    Returns:
        result (float): timestamp in float epoch format
    '''
    #logging.debug(time.strptime("2025-032T12:00:00.000Z", "%Y-%jT%H:%M:%S.%fZ"))
    
    float_time = 0.0
    try:
        float_time = time.mktime(time.strptime(epoch, "%Y-%jT%H:%M:%S.%fZ"))
    except TypeError:
        logging.error(f'Timestamp not in right format (must be str)') 
    except ValueError:
        logging.error(f'Timestamp not in right format')
    return float_time

def return_state_vectors(epoch: float) -> dict:
    '''
    This function is meant to facilitate both /epochs/<epoch> and /now, as they
    both rely on an epoch timestamp, but in different formats. This function
    returns the state vectors for the requested epoch.

    Args:
        epoch (float): the epoch the user wishes to acquire. This must be in
        time.time()'s float format as a number of seconds

    Returns:
        result (dict): a dictionary containing the state vectors of the epoch
        requested
    '''

    #May need to find closest epoch instead: compare the differences between each
    #timestamp and requested timestamp
    difference = sys.float_info.max

    index = 0
    key_str = 'EPOCH'
    temp = {}
    temp_d = 0.

    #Iterate through dataset to find which epoch is numerically closest to now
    try:
        for i in range(len(rd.keys())):
            #iterate through each dictionary
            temp = json.loads(rd.get(i))
            temp_d = abs(epoch - parse_epoch(temp[key_str]))
            if temp_d < difference:
                difference = temp_d
                index = i
    except KeyError:
        logging.error(f'Invalid key - be sure to use ISS Trajectory XML Data')
    except redis.exceptions.ConnectionError:
        logging.error(f'Unable to connect to database.')

    #Return dictionary at requested index, default to first if index invalid
    try:
        return json.loads(rd.get(index))
    except IndexError:
        logging.error(f'Index out of bounds! Defaulting to first index 0')
        return json.loads(rd.get(0))
    except redis.exceptions.ConnectionError:
        logging.error(f'Unable to connect to database.')
        #return a standard dict of values 0
        return {'EPOCH':'1970-01T12:00:00.000Z',
                'X':{'#text':'0.0','@units':'km'},
                'X_DOT':{'#text':'0.0','@units':'km/s'},
                'Y':{'#text':'0.0','@units':'km'},
                'Y_DOT':{'#text':'0.0','@units':'km/s'},
                'Z':{'#text':'0.0','@units':'km'},
                'Z_DOT':{'#text':'0.0','@units':'km/s'},}                

def return_speed(epoch: float) -> dict:
    '''
    This function returns the instantaneous speed for a user-defined epoch
    from the data set.

    Args:
        epoch (float): the epoch the user wishes to acquire. This must be in
        time.time()'s float format as a number of seconds

    Returns:
        result (dict): a dictionary with one key and value - 'instantaneous
        speed' and the ISS' instantaneous speed at the requested index
    '''

    x_key = 'X_DOT'
    y_key = 'Y_DOT'
    z_key = 'Z_DOT'
    t_key = '#text'
    state_vectors = return_state_vectors(epoch)

    inst_speed = math.sqrt(pow(float(state_vectors[x_key][t_key]),2) +
                           pow(float(state_vectors[y_key][t_key]),2) +
                           pow(float(state_vectors[z_key][t_key]),2))
    #must return a dictionary
    return {'Instantaneous Speed (km/s)': inst_speed}

def return_location(epoch: float) -> dict:
    '''
    This function returns the instantaneous position for a user-defined epoch
    from the data set.

    Args:
        epoch (float): the epoch the user wishes to acquire. This must be in
        time.time()'s float format as a number of seconds

    Returns:
        result (dict): a dictionary with four keys and values - instantaneous
        latitude, longitude, altitude, and geoposition for the given epoch
    '''

    temp = {}
    x_key = 'X'
    y_key = 'Y'
    z_key = 'Z'
    t_key = '#text'
    state_vectors = return_state_vectors(epoch)

    x = float(state_vectors[x_key][t_key])
    y = float(state_vectors[y_key][t_key])
    z = float(state_vectors[z_key][t_key])

    #this_epoch needs to be formatted differently:
    this_epoch = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(int(epoch)))
    cartrep = coordinates.CartesianRepresentation([x, y, z], unit=units.km)
    gcrs = coordinates.GCRS(cartrep, obstime=this_epoch)
    itrs = gcrs.transform_to(coordinates.ITRS(obstime=this_epoch))
    loc = coordinates.EarthLocation(*itrs.cartesian.xyz)

    temp.update({'Latitude': loc.lat.value, 'Longitude': loc.lon.value,
                 'Altitude': loc.height.value})

    geocoder = Nominatim(user_agent='iss_tracker')
    geoloc = geocoder.reverse((loc.lat.value, loc.lon.value), zoom=5,
                              language='en')

    temp.update({'Geolocation': str(geoloc)})

    return temp

@app.route('/epochs', methods=['GET'])
def return_epochs() -> List[dict]:
    '''
    This function returns the entire dataset of the ISS data.
    
    Args: None, automatically parses data from NASA's website
    The route supports two query arguments:
        limit (int): starting index to return ISS data from
        offset (int): number of epochs to return

    Returns:
        list_of_dicts (list[dict]): a list of dictionaries containing ISS
            position and velocity information for varying timestamps
    '''
    list_of_dicts = []
    indices = len(rd.keys())
    
    limit = request.args.get('limit', 0)
    offset = request.args.get('offset', indices)

    try:
        limit = int(limit)
        if (limit < 0):
            logging.warning(f'Limit index out of bounds! Defaulting to 0')
            limit = 0
        if (limit > indices):
            logging.warning(f'Limit out of bounds! Defaulting to largest index')
            limit = indices
    except ValueError:
        logging.warning(f'Invalid limit parameter - defaulting to 0')
        limit = 0
    try:
        offset = int(offset)
        if (offset < 0):
            logging.warning(f'Offset index out of bounds! Defaulting to 0')
            offset = 0
        if (offset > (indices - limit)):
            logging.warning(f'Offset out of bounds! Defaulting to largest index')
            offset = (indices - limit)
    except ValueError:
        logging.warning(f'Invalid offset parameter - \
                defaulting to data set length')
        offset = len(list_of_dicts)
    
    #rd is unordered, must iterate through the keys and append them
    for i in range(limit, offset):
        list_of_dicts.append(json.loads(rd.get(i)))

    return list_of_dicts

@app.route('/epochs/<string:epoch>', methods=['GET'])
def return_specific_epoch(epoch: str) -> dict:
    '''
    This function returns the state vectors for a specific user-defined epoch
    from the data set.

    Args:
        epoch (str): the epoch the user wishes to acquire. This must be in the
        format %Y-%jT%H:%M:%S.%fZ, that is 
        [year]-[days in year]T[hour]:[minute]:[second].[microsecond]Z
        (example "2025-32T12:00:00.000Z" for precisely 12:00 on February 1, 2025)
        Epochs are defined at four-minute intervals. If the epoch given does not
        exactly match one in the dataset, the closest one will be returned

    Returns:
        result (dict): a dictionary containing the state vectors of the epoch
        requested
    '''
    #epoch is already a str, error checking built into requested time
    #will return 0.0 if format is incorrect
    requested_time = parse_epoch(epoch)

    state_vectors = return_state_vectors(requested_time)
    return state_vectors

@app.route('/epochs/<string:epoch>/speed', methods=['GET'])
def return_specific_epoch_speed(epoch: str) -> dict:
    '''
    This function returns the instantaneous speed for a user-defined epoch
    from the data set.

    Args:
        epoch (str): the epoch the user wishes to acquire. This must be in the
        format %Y-%jT%H:%M:%S.%fZ, that is
        [year]-[days in year]T[hour]:[minute]:[second].[microsecond]Z
        (example "2025-32T12:00:00.000Z" for precisely 12:00 on February 1, 2025)
        Epochs are defined at four-minute intervals. If the epoch given does not
        exactly match one in the dataset, the closest one will be returned

    Returns:
        result (dict): a dictionary with one key and value - 'instantaneous
        speed' and the ISS' instantaneous speed at the requested index
    '''
    #epoch is already a str, error checking built into requested time
    #will return 0.0 if format is incorrect
    requested_time = parse_epoch(epoch)

    return return_speed(requested_time)

@app.route('/epochs/<string:epoch>/location', methods=['GET'])
def return_specific_epoch_location(epoch: str) -> dict:
    '''
    This function returns the instantaneous position for a user-defined epoch
    from the data set.

    Args:
        epoch (str): the epoch the user wishes to acquire. This must be in the
        format %Y-%jT%H:%M:%S.%fZ, that is
        [year]-[days in year]T[hour]:[minute]:[second].[microsecond]Z
        (example "2025-32T12:00:00.000Z" for precisely 12:00 on February 1, 2025)
        Epochs are defined at four-minute intervals. If the epoch given does not
        exactly match one in the dataset, the closest one will be returned

    Returns:
        result (dict): a dictionary with four keys and values - instantaneous
        latitude, longitude, altitude, and geoposition for the given epoch
    '''
    #epoch is already a str, error checking built into requested time
    #will return 0.0 if format is incorrect
    requested_time = parse_epoch(epoch)

    return return_location(requested_time)

@app.route('/epochs/range', methods=['GET'])
def find_data_range() -> str:
    '''
    This function returns a statement about the time range of data.

    Args: None, automatically parses data from NASA's website

    Returns:
        result (str): a string information about the time range of data
    '''
    range_str = "Data consists of "
    time_i = 0.0
    time_f = 0.0
    key_str = 'EPOCH'
    indices = len(rd.keys())

    range_str = range_str + str(indices)
    range_str = range_str + " indices and ranges from "

    try:
        dict_i = json.loads(rd.get(0))
        dict_f = json.loads(rd.get(indices-1))
        time_i = parse_epoch(dict_i[key_str])
        time_f = parse_epoch(dict_f[key_str])
        #Convert the numerical time to something readable for a user
        range_str = range_str + time.asctime(time.gmtime(time_i))
        range_str = range_str + " to "
        range_str = range_str + time.asctime(time.gmtime(time_f))
    except KeyError:
        #If key is invalid, time range cannot be determined
        range_str = "Data range undetermined"
        logging.error(f'Invalid key')
    range_str = range_str + '\n'
    return range_str

@app.route('/now', methods=['GET'])
def closest_epoch() -> dict:
    '''
    This function returns the index of the epoch closest to the current time.

    Args: None, automatically parses data from NASA's website
    
    Returns:
        result (dict): a dictionary containing the state vectors and instantaneous
        speed and instantaneous position for the epoch that is closest to now
    '''
    #Compare the differences between each timestamp and current timestamp
    difference = sys.float_info.max
    current_time = time.time()
    state_vectors = return_state_vectors(current_time)

    #Utilize the return_speed function defined earlier
    state_vectors.update(return_speed(current_time))

    #Utilize the return_location function defined earlier
    state_vectors.update(return_location(current_time))

    return state_vectors

@app.route('/debug', methods=['GET'])
def debug():
    return "rd length: " + str(len(rd.keys())) + '\n'

def main():
    #Initialize Flask
    app.run(debug=True, host='0.0.0.0')

    logging.debug(f'Flask initialized')
    logging.debug(f'rd length')
    logging.debug(len(rd.keys()))
   
    
    #Initialize the database on startup: only import the data if db is empty
    indices = len(rd.keys())
    if (indices == 0):
        response = requests.get(url="https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml")
        dict_data = xmltodict.parse(response.content)
        list_of_dicts = (dict_data['ndm']['oem']['body']['segment']['data']
                         ['stateVector'])

        #Save to Redis database
        #Redis doesn't support listed dictionaries - therefore, json will be used
        #to facilitate dict to string conversions
        #Be sure to json.loads() while pulling it back
        for i in range(len(list_of_dicts)):
            i_key = i
            rd.set(i_key, json.dumps(list_of_dicts[i]))

    #rd is ready to use
    
    #Test of time.strptime
    logging.debug(time.mktime(time.strptime("2025-050T23:57:00.000Z", 
                                            "%Y-%jT%H:%M:%S.%fZ")))

if __name__ == '__main__':
    main()
