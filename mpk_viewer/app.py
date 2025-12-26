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


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
