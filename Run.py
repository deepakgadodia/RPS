

# Constants (Can be changed according to requirements) ------------------------------------------------------

# This is the server port. 
PORT = 8888

# Caching variables
CACHE_ELE_MAX = 100
TIME_LIMIT_MAX = 60 # Seconds

# Threshold for slow response time in seconds
SLOW_REQUEST_THRESHOLD = 1

# Time unit for slow request threshold.  Currently 's' for seconds
TIME_UNIT = 's'

# Message displayed when the server is starting
START_MSG = 'Starting on port: ' + str(PORT)


# Reverse proxy constants -----------------------------------------------------

# Nextbus API URL pieces
URL =  'http://webservices.nextbus.com/service/publicXMLFeed'
CMD = '?command='

ROOT_PATH = '/'
STATS_PATH = '/stats'
FAVICON_PATH = '/favicon.ico'


# Database constants ----------------------------------------------------------

# Info used to connect to the MySQL database
MYSQL_CONNECT_INFO = {'host': 'deepakgadodia.chqdxrp2tj0k.us-east-1.rds.amazonaws.com',     # Host
                     'user': 'deepakgadodia',                       # Username
                     'passwd': 'thousandeyes',                      # Password
                     'db': 'deepakgadodia'}                         # DB name

# Used for the statistics page
QUERYKEY = 'queries'
SLOW_REQ_KEY = 'slow_requests'
GET_QUERY = ('SELECT * FROM queries')
GET_SLOW_REQUESTS = ('SELECT * FROM slow_requests')
#CLEAN_QUERIES_COMMAND = ('DELETE FROM queries')
#CLEAN_SLOW_REQUESTS_COMMAND = ('DELETE FROM slow_requests')


import urllib
import time
import mysql.connector
import pprint
import json
import os
import BaseHTTPServer
import SocketServer
from expiringdict import ExpiringDict

"""
Tools used by the reverse proxy service.
"""

# Build a URL based on user's requested path
def url_nextbus(path):
    if path == ROOT_PATH:
        return URL 
    else:
        # Build a URL with the requested command
        return URL + CMD + path[1:]


# Get an http response 
def get_nextbus_response(request, cache):
    if request.path in cache:
        # Return cached request.
        cache[request.path] = cache.get(request.path)
    else:
        # Request not cached.
        resource_url = url_nextbus(request.path)
        response = urllib.urlopen(resource_url)

        # Storing 'response' in the cache does not store the data from read(),
        # so we create a small dictionary to hold the necessary data
        info = {'data': response.read(), \
                'code': response.code, \
                'headers': response.info().items()}

        # Store this info in the cache       
        cache[request.path] = info
        
    return cache[request.path]


# Gather data from the database
def get_statistics(db):
    queries = {}
    slow_requests = {}

    cursor = db.cursor()
    
    # Get all query data
    cursor.execute(GET_QUERY)
    for (endpoint, count) in cursor:
        queries[str(endpoint)] = count

    # Get slow request data
    cursor.execute(GET_SLOW_REQUESTS)
    for (endpoint, time) in cursor:
        slow_requests.setdefault(str(endpoint), []).append \
                                (str(float(time)) + TIME_UNIT)

    cursor.close()

    # Return the statistics as a dictionary
    return {QUERYKEY: queries, 
            SLOW_REQ_KEY: slow_requests}

# Update the queries table of the statistics
def update_queries(request, cursor):   
    # Check if it is already in the database
    query_count_command = ("SELECT * FROM queries "
                         + "WHERE endpoint = '" + request.path + "'")
    cursor.execute(query_count_command)
   
    # Increment or insert a row in the database
    if len(cursor.fetchall()) == 0:
        
        query_command = ("INSERT INTO queries "
                       + "VALUES('" + request.path + "', 1)")        
    else:
        
        query_command = ("UPDATE queries " 
               + "SET request_count = request_count + 1 "
               + "WHERE endpoint = '" + request.path + "'")

    cursor.execute(query_command)

# Update the slow_requests table of the statistics
def update_slow_requests(request, cursor, request_time):
    
    if request_time <= SLOW_REQUEST_THRESHOLD:
        return

    command = ("INSERT INTO slow_requests "
             + "VALUES('" + request.path + "', " + str(request_time) + ")")
    cursor.execute(command)


# Update stats
def update_statistics(request, request_time, db):
    
    if request.path == FAVICON_PATH:
        return

    cursor = db.cursor()
    
    update_queries(request, cursor)
    update_slow_requests(request, cursor, request_time)

    db.commit()
    cursor.close()
    

# Handle stats request 
def handle_stats_request(request, db):
    
    request.send_response(200)
    request.send_header('Content-type', 'text/json')
    request.end_headers()
    
    
    statistics = get_statistics(db)

    # Write data to a file 
    with open('data.txt', 'w') as out:
        json.dump(statistics, out, sort_keys=True, indent=4, separators=(',', ': '))
    
    # Load the formatted data to the page
    with open('data.txt') as out:
        request.wfile.write(out.read())

    # Delete the file
    os.remove('data.txt')

# Get the requested resource and load it to the page
def handle_proxy_request(request, start_time, cache, db):
    
    response = get_nextbus_response(request, cache)

    # Data to load on the web page
    data = response['data']

    # Use headers obtained from the our request to NextBus
    request.send_response(response['code'])

    # Load the data to the page
    for key, value in response['headers']:
        request.send_header(key, value)
    request.end_headers()
    request.wfile.write(data)

    # Record the amount of time taken to complete the request
    end = time.time()
    request_time = end - start_time    
    update_statistics(request, request_time, db)



class ProxyServer(BaseHTTPServer.HTTPServer, SocketServer.ThreadingMixIn):
    pass    

class ProxyHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(request):
        # Start a timer to record slow requests
        start_time = time.time()

        # Handle the GET request
        if request.path == STATS_PATH:
            # Statistics request
            handle_stats_request(request, db)
        else:
            # Standard reverse proxy request
            handle_proxy_request(request, start_time, cache, db)
            
# Connect to MySQL database
db = mysql.connector.connect(**MYSQL_CONNECT_INFO)

# Create the cache 
cache = ExpiringDict(max_len = CACHE_ELE_MAX, \
                     max_age_seconds = TIME_LIMIT_MAX)

print START_MSG

# Start the reverse proxy server
ProxyServer(("", PORT), ProxyHandler).serve_forever()
