
import osmnx as ox
import json
import networkx as nx

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
    return G_combined

def calculate_paths(graph, routes_data):
    """Calculates and adds realistic paths to the routes data."""
    for line, data in routes_data.items():
        print(f"Processing line: {line}")
        for direction in data.get("directions", []):
            stops = direction.get("stops", [])
            path_coordinates = []
            
            # Add the first stop's coordinates to the beginning of the path
            if stops and "lat" in stops[0] and "lon" in stops[0]:
                path_coordinates.append([stops[0]["lat"], stops[0]["lon"]])

            for i in range(len(stops) - 1):
                start_stop = stops[i]
                end_stop = stops[i+1]

                if "lat" not in start_stop or "lon" not in start_stop or "lat" not in end_stop or "lon" not in end_stop:
                    print(f"  Skipping segment for line {line} due to missing coordinates.")
                    continue

                start_point = (start_stop["lat"], start_stop["lon"])
                end_point = (end_stop["lat"], end_stop["lon"])

                try:
                    start_node = ox.nearest_nodes(graph, start_point[1], start_point[0])
                    end_node = ox.nearest_nodes(graph, end_point[1], end_point[0])
                    
                    # Calculate the shortest path
                    route = nx.shortest_path(graph, start_node, end_node, weight='length')
                    
                    # Get the coordinates for the path
                    route_coords = [[graph.nodes[node]['y'], graph.nodes[node]['x']] for node in route]
                    
                    # Add coordinates, skipping the first point to avoid duplication
                    path_coordinates.extend(route_coords[1:])

                except (nx.NetworkXNoPath, ValueError) as e:
                    print(f"  Could not find path for line {line} between {start_stop['name']} and {end_stop['name']}: {e}")
                    # If no path, just connect with a straight line
                    path_coordinates.append([end_stop["lat"], end_stop["lon"]])

            direction["path"] = path_coordinates
    return routes_data

def main():
    """Main function to run the path solver."""
    print("Loading routes data...")
    with open("mpk_viewer/data/routes.json", "r", encoding='utf-8') as f:
        routes_data = json.load(f)
    
    graph = get_graph()
    print("Calculating paths for all routes...")
    updated_routes = calculate_paths(graph, routes_data)
    
    print("Saving updated routes data...")
    with open("mpk_viewer/data/routes.json", "w", encoding='utf-8') as f:
        json.dump(updated_routes, f, indent=2, ensure_ascii=False)
    print("Done.")

if __name__ == "__main__":
    main()
