# MeteoApp | Global Meteorological Data Web Application

This repository hosts a web application designed to process, visualize, and analyze global meteorological data. The project, developed in Python using the Django framework with the GeoDjango module, aims to provide a comprehensive tool for understanding weather patterns.

## Objective

The primary goal of this study is to process meteorological data sourced from the NOAA (https://www.noaa.gov/) server, covering a 5-day period. Key variables, including temperature, humidity, and wind speed, undergo processing involving the retrieval of GRIB files, transformation, and loading into a PostgreSQL database equipped with the PostGIS spatial extension.

## Key Features

- **Data Processing:** The application facilitates the retrieval and processing of meteorological data, ensuring accuracy and relevance for subsequent analysis.
  
- **Visualization Techniques:**
  - Time Series Charts: Visual representations of temporal trends using interactive Plotly charts
  - Cartograms: Spatially distorted maps using Choropleth layers on top of interactive Folium base map
  - Spatial Interpolation (Inverse distance weighting - IDW): Interpolating meteorological data across spatial dimensions
  - Clustering (SKATER): Clustering algorithm using Spopt package based on PySAL library
  - Animations: Dynamic visualizations using custom GIFs

## Repository Structure

- `interactiveMap/management/`: custom Django commands to manipulate data
- `interactiveMap/migrations/`: migration files
- `interactiveMap/static/`: CSS files and images
- `interactiveMap/templates/`: HTML template files (divided into 2 folders)
- `interactiveMap/templatetags/`: custom filters used in HTML files via Django Template Language
- `interactiveMap/views/`: view functions
- `interactiveMap/load/`: module for loading borders data into database
- `interactiveMap/load_regions/`: module for loading administrative area (regions) borders data into database

The remaining unspecified files are regular files of the project or Django application.

## Environment

- **IDE:** PyCharm
- **Python Version:** 3.7.9
- **Web Technologies:** HTML with Django Template Language, CSS

## Dependencies (Virtual Environment)

<details>
<summary>Click to expand/collapse</summary>

Package            Version
---
- affine             2.4.0    
- aiohttp            3.8.4    
- aiosignal          1.3.1    
- asciitree          0.3.3    
- asgiref            3.6.0
- async-timeout      4.0.2
- asynctest          0.13.0
- attrs              23.1.0
- beautifulsoup4     4.12.2
- branca             0.6.0
- certifi            2022.12.7
- cffi               1.15.1
- cfgrib             0.9.10.3
- charset-normalizer 3.1.0
- click              8.1.3
- click-plugins      1.1.1
- cligj              0.7.2
- colorama           0.4.6
- cycler             0.11.0
- Django             3.2.18
- eccodes            1.2.0
- ecmwflibs          0.5.1
- entrypoints        0.4
- esda               2.4.3
- et-xmlfile         1.1.0
- fasteners          0.18
- findlibs           0.0.5
- Fiona              1.9.3
- folium             0.14.0
- fonttools          4.38.0
- frozenlist         1.3.3
- fsspec             2023.1.0
- geopandas          0.10.2
- greenlet           2.0.2
- idna               3.4
- importlib-metadata 4.13.0
- Jinja2             3.1.2
- joblib             1.2.0
- kiwisolver         1.4.4
- libpysal           4.7.0
- mapclassify        2.5.0
- MarkupSafe         2.1.3
- matplotlib         3.5.3
- multidict          6.0.4
- munch              2.5.0
- networkx           2.6.3
- numcodecs          0.10.2
- numpy              1.21.6
- openpyxl           3.1.2
- packaging          23.1
- pandas             1.3.5
- Pillow             9.5.0
- pip                23.1.2
- platformdirs       3.10.0
- plotly             5.15.0
- psycopg2-binary    2.9.6
- PuLP               2.7.0
- pycparser          2.21
- PyKrige            1.7.0
- pyparsing          3.1.0
- pyproj             3.2.1
- python-dateutil    2.8.2
- pytz               2023.3
- requests           2.29.0
- Rtree              1.0.1
- scikit-learn       1.0.2
- scipy              1.7.3
- setuptools         67.4.0
- shapely            2.0.1
- six                1.16.0
- soupsieve          2.4.1
- spaghetti          1.6.5
- spopt              0.4.1
- SQLAlchemy         1.4.46
- sqlparse           0.4.4
- tenacity           8.2.2
- threadpoolctl      3.1.0
- typing_extensions  4.7.1
- urllib3            1.26.15
- wheel              0.38.4
- xarray             0.20.2
- yarl               1.9.2
- zarr               2.12.0
- zipp               3.15.0


</details>

## Data Management

The repository includes scripts and commands for manually downloading, modifying, and loading data into the PostgreSQL database. A tutorial guides users through executing these commands. 
Additionally, a database backup file is provided for easy replication.

<details>
<summary>Click to expand/collapse</summary>

Follow the tutorial for manual data processing:

- **downloading meteorological data**:
  - Run Django shell
`python manage.py shell`

  - Import the data_downloader module as a Python module
`import data_downloader`

  - Run the download_files script with a date range from 30th October 2023 to 3rd November 2023
`data_downloader.download_files(startdate='20231030', enddate='20231103')`

- **modifying meteorological data**:
  - To execute the script, run the following command in the terminal from the project folder (../MeteoApp):
`python manage.py modify_data`

- **loading meteorological data into database**:
  - To run the script, execute the following command in the terminal from the project folder (optionally, execute the command to truncate the 'location' table)
`python manage.py add_data`

- **loading borders data into database**:
  - Run Django shell
`python manage.py shell`

  - Import the load module as a Python module
`from interactiveMap import load`

  - Run the load script with the run() method
`load.run()`

</details>

## Google Drive Links

- [Meteorological Data Files](https://drive.google.com/file/d/1Yb8rnlXhNgY9oN0L-7GqNykVu6pe86yB/view?usp=drive_link) 
- [Database Backup File](https://drive.google.com/file/d/1z1ULQZLuhdjA4WosFzMtwjq_u8q1U9p5/view?usp=drive_link)

## Inspiration

Links to external repositories and sources that inspired or provided guidance for the project.

1. [tomchavakis](https://github.com/tomchavakis/grib-downloader/blob/main/grib_downloader.py)
   - Downloading data from the NOAA server.

2. [Majramos](https://gist.github.com/Majramos/5e8985adc467b80cccb0cc22d140634e)
   - Implementation of spatial interpolation method (Inverse distance weighting)
  
## User Experience (UX)

The application focuses on delivering a seamless user experience with two distinct modules (Interactive Map Module and Data Exploration Module), each featuring a unique interface and specialized functionalities. For a firsthand experience, a link to a recording showcasing the application in use is provided.

[Recording](https://drive.google.com/file/d/1HOPQRWFCZSFcYH2HlRIoEJZCg8xu38G4/view?usp=drive_link)

- **Interactive Map Module**:
The Interactive Map Module features a central interactive base map created with Folium. Users can pan and zoom, change the map's theme, and hover over layers to display meteorological variable values. Below the map, there's an interactive time series plot using Plotly. A panel on the right allows users to select visualization options, and a concise summary of parameters is displayed. The left menu provides navigation options.

- **Data Exploration Module**:
The Data Exploration Module has tabs for various visualizations, each described with a title and brief summary. Users can switch tabs using the left panel and find user hints for specific visualizations. Available country options and submission buttons are placed below each description. After submission, visualizations display with titles, axis labels, and legends. A top menu allows navigation to the homepage or the Interactive Map Module.

---
Thank you for your interest in this meteorological data web application!
