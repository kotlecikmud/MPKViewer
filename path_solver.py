
import osmnx as ox
import json
import networkx as nx
from tqdm import tqdm

def save_routes(routes_data):
    """Saves the routes data to a JSON file."""
    with open("mpk_viewer/data/routes_solved.json", "w", encoding='utf-8') as f:
        json.dump(routes_data, f, indent=2, ensure_ascii=False)

def get_graph():
    """Fetches and combines the street and tram networks for Wroclaw."""
    place_name = "Wroclaw, Poland"
    print("Fetching drive network...")
    # Fetch street network
    G_drive = ox.graph_from_place(place_name, network_type='drive')
    
    print("Fetching tram network...")
    # Fetch tram network
    G_tram = ox.graph_from_place(place_name, custom_filter='["railway"~"tram"]')
    
    print("Combining networks...")
    # Combine the two graphs
    G_combined = nx.compose(G_drive, G_tram)
    return G_combined, G_drive

def calculate_paths(G_combined, G_drive, routes_data):
    """Calculates and adds realistic paths to the routes data."""
    for line, data in tqdm(routes_data.items(), desc=f"Processing line ({line})"):
        for direction in data.get("directions", []):
            stops = direction.get("stops", [])
            path_coordinates = []
            
            if stops and "lat" in stops[0] and "lon" in stops[0]:
                path_coordinates.append([stops[0]["lat"], stops[0]["lon"]])

            for i in range(len(stops) - 1):
                start_stop = stops[i]
                end_stop = stops[i+1]

                if "lat" not in start_stop or "lon" not in start_stop or "lat" not in end_stop or "lon" not in end_stop:
                    # This case is handled by skipping, but we can log it if needed
                    continue

                start_point = (start_stop["lat"], start_stop["lon"])
                end_point = (end_stop["lat"], end_stop["lon"])

                try:
                    start_node = ox.nearest_nodes(G_drive, start_point[1], start_point[0])
                    end_node = ox.nearest_nodes(G_drive, end_point[1], end_point[0])
                    
                    route = nx.shortest_path(G_combined, start_node, end_node, weight='length')
                    
                    route_coords = [[G_combined.nodes[node]['y'], G_combined.nodes[node]['x']] for node in route]
                    
                    path_coordinates.extend(route_coords[1:])

                except (nx.NetworkXNoPath, ValueError):
                    # If no path is found, connect with a straight line
                    path_coordinates.append([end_stop["lat"], end_stop["lon"]])

            direction["path"] = path_coordinates
        
        # Save after processing each line
        save_routes(routes_data)
    return routes_data

def main():
    """Main function to run the path solver."""
    print("Loading routes data...")
    with open("mpk_viewer/data/routes.json", "r", encoding='utf-8') as f:
        routes_data = json.load(f)
    
    G_combined, G_drive = get_graph()
    print("Calculating paths for all routes...")
    calculate_paths(G_combined, G_drive, routes_data)
    
    print("Done.")

if __name__ == "__main__":
    main()
