from flask import Flask, render_template, jsonify
from mpyk import MpykClient
import json
import os
from datetime import datetime
from pytz import timezone
import qrcode
import base64
from io import BytesIO
import logging

# --- Logging Setup ---
# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Logger for missing lines
missing_lines_logger = logging.getLogger('missing_lines')
missing_lines_logger.setLevel(logging.INFO)
missing_lines_handler = logging.FileHandler('logs/missing_lines.log')
missing_lines_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
missing_lines_logger.addHandler(missing_lines_handler)


# --- Vehicle Data Logging Setup ---
if not os.path.exists('vehicle_logs'):
    os.makedirs('vehicle_logs')

def setup_vehicle_logger(line):
    log_dir = os.path.join('vehicle_logs', datetime.now().strftime('%Y-%m-%d'))
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"line_{line}.log")
    
    logger_name = f"vehicle_data_{line}_{datetime.now().strftime('%Y%m%d')}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    
    # Prevent adding multiple handlers if the logger is re-used in the same request/app context
    if logger.hasHandlers():
        # Clear existing handlers to reconfigure with the correct file path for the day
        logger.handlers.clear()

    handler = logging.FileHandler(log_file, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    return logger

app = Flask(__name__)
client = MpykClient()

# App version
APP_VERSION = "00.01.00.00b"

# Author details
AUTHOR_NAME = "Filip Pawłowski"
AUTHOR_EMAIL = "filippawlowski2012@gmail.com"
GITHUB_REPO = "https://github.com/kotlecikmud/MPKViewer"

# Load route data from JSON file
routes_data = {}
routes_path = os.path.join(os.path.dirname(__file__), 'data', 'routes.json')
try:
    with open(routes_path, 'r', encoding='utf-8') as f:
        routes_data = json.load(f)
except FileNotFoundError:
    print(f"Error: The file {routes_path} was not found.")
except json.JSONDecodeError:
    print(f"Error: Could not decode JSON from {routes_path}.")

@app.route('/')
def index():
    # Sort the line numbers naturally (e.g., '2', '10', '100')
    sorted_lines = sorted(routes_data.keys(), key=lambda x: int(''.join(filter(str.isdigit, x))) if any(char.isdigit() for char in x) else float('inf'))
    
    # Separate lines into buses and trams based on the top-level 'type' attribute
    buses = [line for line in sorted_lines if routes_data.get(line, {}).get('type') == 'bus']
    trams = [line for line in sorted_lines if routes_data.get(line, {}).get('type') == 'tram']
    
    # Generate QR code for email
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(f"mailto:{AUTHOR_EMAIL}")
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    return render_template('index.html', 
                           version=APP_VERSION,
                           author_name=AUTHOR_NAME,
                           author_email=AUTHOR_EMAIL,
                           github_repo=GITHUB_REPO,
                           buses=buses,
                           trams=trams,
                           qr_code=img_str)

@app.route('/api/vehicles')
def get_vehicles():
    """Returns live vehicle positions and the last update time."""
    positions = client.get_all_positions()
    
    # Log missing lines
    live_lines = {p.line for p in positions}
    known_lines = set(routes_data.keys())
    missing = live_lines - known_lines
    for line in missing:
        missing_lines_logger.info(f"Line '{line}' found in live data but not in routes.json")
        
    # --- Vehicle Data Logging ---
    loggers = {}
    try:
        for p in positions:
            if p.line not in loggers:
                loggers[p.line] = setup_vehicle_logger(p.line)
            
            log_message = f"lat={p.lat}, lon={p.lon}, type={p.kind}, line={p.line}"
            loggers[p.line].info(log_message)

    except Exception as e:
        app.logger.error(f"Failed to log vehicle data: {e}")
    finally:
        # Close all handlers to prevent file locking issues
        for logger in loggers.values():
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
    # --- End of Logging ---

    # Get the current time in Europe/Warsaw timezone
    tz = timezone('Europe/Warsaw')
    last_update_time = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')

    vehicle_data = [
        {
            'lat': p.lat,
            'lon': p.lon,
            'line': p.line,
            'type': p.kind
        } for p in positions
    ]
    
    return jsonify({
        "vehicles": vehicle_data,
        "last_update": last_update_time
    })

@app.route('/api/routes')
def get_all_routes():
    """Returns a list of all available lines with their types."""
    lines_with_types = []
    for line_id, data in routes_data.items():
        # Heuristic to determine type: if any vehicle variant is a tram, call it a tram.
        is_tram = any('tram' in d.get('type', '').lower() for d in data.get('directions', []))
        # A simple fallback for routes.json that might not have the new structure.
        # This part might need adjustment if your routes.json format is different.
        # The scraper should be updated to provide a definitive 'type' field at the top level.
        vehicle_type = data.get('type', 'bus' if not is_tram else 'tram') # Basic fallback
        
        lines_with_types.append({
            "line": line_id,
            "type": vehicle_type
        })
    return jsonify(lines_with_types)


@app.route('/api/routes/<line>')
def get_route(line):
    """Returns the specific route data for a given line, using pre-existing coordinates."""
    line_data = routes_data.get(line)
    
    # --- Dynamic Logging for Route Traces ---
    try:
        # Create date-stamped directory
        log_dir = os.path.join('logs', 'route_traces', datetime.now().strftime('%Y-%m-%d'))
        os.makedirs(log_dir, exist_ok=True)
        
        # Configure a temporary logger
        log_file = os.path.join(log_dir, f"line_{line}.log")
        
        logger_name = f"route_trace_{line}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        route_logger = logging.getLogger(logger_name)
        route_logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler(log_file, encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        handler.setFormatter(formatter)
        
        route_logger.addHandler(handler)
        
        route_logger.info(f"--- Route Trace for Line: {line} ---")
        if line_data:
            route_logger.info(json.dumps(line_data, indent=2, ensure_ascii=False))
        else:
            route_logger.info("Line not found in routes.json")
        route_logger.info("--- End Trace ---")
        
        handler.close()
        route_logger.removeHandler(handler)

    except Exception as e:
        app.logger.error(f"Failed to log route trace for line {line}: {e}")
    # --- End of Logging ---

    if not line_data:
        return jsonify({"error": "Line not found"}), 404

    if not line_data.get("directions"):
        return jsonify({
            "line": line,
            "error": "Route details are not available for this line.",
            "source": line_data.get("source")
        })

    processed_directions = []
    for direction in line_data.get("directions", []):
        processed_stops = []
        for stop in direction.get("stops", []):
            cleaned_name = stop["name"].replace("NŻPrzystanek na życzenie", "").strip()
            
            processed_stop = {
                "name": cleaned_name,
                "street": stop.get("street"),
                "lat": stop.get("lat"),
                "lon": stop.get("lon")
            }
            processed_stops.append(processed_stop)

        processed_directions.append({
            "direction_name": direction["direction_name"],
            "stops": processed_stops,
            "path": direction.get("path", [])
        })

    return jsonify({"line": line, "directions": processed_directions})


from flask import request
from datetime import timedelta
from geopy.distance import geodesic
import re

@app.route('/api/logged_routes/dates')
def get_logged_dates():
    """Returns a list of dates for which logs are available."""
    log_dir = 'vehicle_logs'
    if not os.path.exists(log_dir):
        return jsonify([])
    
    dates = [d for d in os.listdir(log_dir) if os.path.isdir(os.path.join(log_dir, d))]
    valid_dates = []
    for date_str in dates:
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            valid_dates.append(date_str)
        except ValueError:
            continue
            
    return jsonify(sorted(valid_dates, reverse=True))


@app.route('/api/logged_routes')
def get_logged_routes_for_date():
    """
    Returns processed logged routes for a specific date.
    Detects route ends if a vehicle is stationary for more than 10 minutes.
    """
    date = request.args.get('date')
    if not date:
        return jsonify({"error": "Date parameter is required"}), 400

    log_dir = os.path.join('vehicle_logs', date)
    if not os.path.exists(log_dir):
        return jsonify({"error": "No logs found for this date"}), 404

    all_routes = {}
    
    log_pattern = re.compile(
        r'^(?P<timestamp>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2},\d{3})\s-\s'
        r'lat=(?P<lat>[-?\d\.]+),\s'
        r'lon=(?P<lon>[-?\d\.]+),'
    )

    for filename in os.listdir(log_dir):
        if filename.startswith('line_') and filename.endswith('.log'):
            line_name = filename.replace('line_', '').replace('.log', '')
            filepath = os.path.join(log_dir, filename)
            
            points = []
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        match = log_pattern.match(line)
                        if match:
                            data = match.groupdict()
                            points.append({
                                'timestamp': datetime.strptime(data['timestamp'], '%Y-%m-%d %H:%M:%S,%f'),
                                'lat': float(data['lat']),
                                'lon': float(data['lon'])
                            })
            except Exception as e:
                app.logger.error(f"Error reading log file {filename}: {e}")
                continue

            if not points:
                continue

            points.sort(key=lambda p: p['timestamp'])

            line_routes = []
            current_route = []
            
            if points:
                current_route.append((points[0]['lat'], points[0]['lon']))

            for i in range(1, len(points)):
                prev_point = points[i-1]
                current_point = points[i]
                
                time_diff = current_point['timestamp'] - prev_point['timestamp']
                
                if time_diff > timedelta(minutes=10):
                    if len(current_route) > 1:
                        line_routes.append(current_route)
                    current_route = [(current_point['lat'], current_point['lon'])]
                else:
                    current_route.append((current_point['lat'], current_point['lon']))

            if len(current_route) > 1:
                line_routes.append(current_route)
            
            if line_routes:
                all_routes[line_name] = line_routes

    return jsonify(all_routes)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
