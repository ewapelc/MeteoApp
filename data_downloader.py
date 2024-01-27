# The code in this python script is adapted from public github repository:
# https://github.com/tomchavakis/grib-downloader

from datetime import datetime
import os
import requests
import pandas as pd
import time

server = "https://nomads.ncep.noaa.gov/cgi-bin/"
dataset = 'filter_gfs_0p25.pl'
URL = server + dataset

suffix = 'z.pgrb2.0p25.f000'

# Every six hours the model generates new files.
timelist = ['00', '06', '12', '18']

DOWNLOADS_DIR = "filestorage/grib"
VARIABLES = "UGRD,VGRD,GUST,TMP,RH,SPFH,PWAT,TCDC"
LEVELS = "1000_mb,entire_atmosphere_%5C%28considered_as_a_single_layer%5C%29,surface"


def create_server_by_time(time):
    if time in range(0, 4):
        return URL + '?file=gfs.t' + timelist[time] + suffix
    return


def create_url(run, datestring):
    """
    Add url parameters (such as levels, variables, date and cycle)
    to determine the data in the files.
    """
    variables = VARIABLES.split(',')
    levels = LEVELS.split(',')
    url = create_server_by_time(run)
    # Levels
    for item in levels:
        url = url + '&lev_' + item + '=on'
    # Variables
    for item in variables:
        url = url + '&var_' + item + '=on'
    # Longitude and latitude ranges
    url = url + '&leftlon=0&rightlon=360&toplat=90&bottomlat=-90'
    # Date
    url = url + '&dir=%2Fgfs.' + datestring
    # Cycle (e.g. 00, 06 etc.)
    url = url + '%2F' + timelist[run]
    # atmos subdirectory
    url = url + '%2F' + 'atmos'
    return url


def file_exist_in_server(run, datestring):
    result = create_url(run, datestring)
    r = requests.get(result, stream=True)
    return r.status_code, result


def create_local_filename(run, datestring):
    return "gfs." + datestring + ".t" + timelist[run] + suffix + ".grib2"


def get_path_to_file(local_filename):
    return os.path.join('./', DOWNLOADS_DIR, local_filename)


def file_is_downloaded(local_filename):
    path = get_path_to_file(local_filename)
    if os.path.exists(path):
        return True
    else:
        return False


def get_file(url, local_filename):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        path_to_file = get_path_to_file(local_filename)
        with open(path_to_file, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                # If you have chunk encoded response uncomment if
                # and set chunk_size parameter to None.
                # if chunk:
                f.write(chunk)


def download_files(startdate, enddate):
    startdate_obj = datetime.strptime(startdate, '%Y%m%d').date()
    enddate_obj = datetime.strptime(enddate, '%Y%m%d').date()
    daterange = pd.date_range(startdate_obj, enddate_obj)

    print("Download files from the server.\n")

    for d in daterange:
        datestring = d.strftime('%Y%m%d')
        for run in range(0, 4):
            local_filename = create_local_filename(run, datestring)
            # Check if file is already downloaded locally
            if file_is_downloaded(local_filename):
                print("For date: {} and cycle: {} the file is already downloaded".format(datestring, timelist[run]))
                continue
            # Check if file exists in server
            exist = file_exist_in_server(run, datestring)
            if exist[0] == 404:
                print("For date: {} and cycle: {} the file doesn't yet exist on the server\nFinish download".format(
                    datestring, timelist[run]))
                return
            # Create downloads path
            path = os.path.join('./', DOWNLOADS_DIR)
            if not os.path.exists(path):
                try:
                    os.makedirs(path, exist_ok=True)
                    print("Directory '%s' created successfully" % DOWNLOADS_DIR)
                except OSError as error:
                    print("Directory '%s' can not be created")
            # Get the file
            get_file(exist[1], local_filename)
            print(f"Downloaded file: {local_filename}", end="\n")
            time.sleep(1)

    print('\x1b[6;30;42m' + 'Successfully downloaded data.' + '\x1b[0m')