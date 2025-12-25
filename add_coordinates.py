import json
import re
import time
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

ROUTES_FILE = 'mpk_viewer/data/routes.json'

def clean_stop_name(name):
    return re.sub(r'NŻPrzystanek na życzenie$', '', name).strip()

def save_routes(routes_data):
    with open(ROUTES_FILE, 'w', encoding='utf-8') as f:
        json.dump(routes_data, f, indent=2, ensure_ascii=False)

def get_coordinates(geolocator, stop_name, street):
    if street and street != 'N/A':
        query = f"{stop_name}, {street}, Wroclaw, Poland"
    else:
        query = f"{stop_name}, Wroclaw, Poland"

    for i in range(3):
        try:
            location = geolocator(query, timeout=10)
            if location:
                return {
                    'lat': location.latitude,
                    'lon': location.longitude
                }
        except Exception as e:
            print(f"Error fetching {query} ({i+1}/3): {e}")
            time.sleep(2)

    return None

def add_coordinates_to_routes():
    with open(ROUTES_FILE, 'r', encoding='utf-8') as f:
        routes_data = json.load(f)

    geolocator = Nominatim(user_agent="mpk_viewer_geocoder")
    geocode = RateLimiter(
        geolocator.geocode,
        min_delay_seconds=1,
        error_wait_seconds=5
    )

    stops_to_process = []

    for route in routes_data.values():
        for direction in route['directions']:
            for stop in direction['stops']:
                if 'lat' not in stop or 'lon' not in stop:
                    stop_name = clean_stop_name(stop['name'])
                    street = stop.get('street')
                    stops_to_process.append((stop_name, street))

    stops_to_process = list(dict.fromkeys(stops_to_process))  # unique

    print(f"Found {len(stops_to_process)} stops without coordinates")

    for i, (stop_name, street) in enumerate(stops_to_process, start=1):
        coords = get_coordinates(geocode, stop_name, street)

        if not coords:
            print(f"[{i}/{len(stops_to_process)}] ❌ {stop_name}")
            continue

        # update ALL matching stops immediately
        for route in routes_data.values():
            for direction in route['directions']:
                for stop in direction['stops']:
                    if (
                        clean_stop_name(stop['name']) == stop_name
                        and stop.get('street') == street
                    ):
                        stop['lat'] = coords['lat']
                        stop['lon'] = coords['lon']

        save_routes(routes_data)

        print(f"[{i}/{len(stops_to_process)}] ✅ {stop_name} saved")

    print("Done. routes.json updated incrementally.")

if __name__ == '__main__':
    add_coordinates_to_routes()
