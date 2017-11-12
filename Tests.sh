#!/bin/sh
curl  'http://localhost:8888/routeList&a=sf-muni' &> TestOutput.txt
curl  'http://localhost:8888/agencyList' &>> TestOutput.txt
curl  'http://localhost:8888/stats' &>> TestOutput.txt
curl  'http://localhost:8888/routeConfig&a=sf-muni&r=N' &>> TestOutput.txt
curl  'http://localhost:8888/predictions&a=sf-muni&r=N&s=5205&useShortTitles=true' &>> TestOutput.txt
curl  'http://localhost:8888/predictionsForMultiStops&a=sf-muni&stops=N|6997&stops=N|3909' &>> TestOutput.txt
curl  'http://localhost:8888/schedule&a=sf-muni&r=N' &>> TestOutput.txt
curl  'http://localhost:8888/vehicleLocations&a=sf-muni&r=N&t=1144953500233' &>> TestOutput.txt
