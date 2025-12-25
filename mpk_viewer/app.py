from flask import Flask, render_template, jsonify
from mpyk import MpykClient
import json
import os

app = Flask(__name__)
client = MpykClient()

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
    return render_template('index.html')

@app.route('/api/vehicles')
def get_vehicles():
    """Returns live vehicle positions."""
    positions = client.get_all_positions()
    vehicle_data = [
        {
            'lat': p.lat,
            'lon': p.lon,
            'line': p.line,
            'type': p.kind
        } for p in positions
    ]
    return jsonify(vehicle_data)

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
            "stops": processed_stops
        })

    return jsonify({"line": line, "directions": processed_directions})


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
