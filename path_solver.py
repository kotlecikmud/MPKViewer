import osmnx as ox
import json
import networkx as nx
from tqdm import tqdm
from datetime import datetime
import time


def ts():
    """Zwraca aktualny czas w formacie HH:MM:SS"""
    return datetime.now().strftime("%H:%M:%S")


def save_routes(routes_data):
    """Zapisuje dane tras do pliku JSON"""
    with open("mpk_viewer/data/routes_solved.json", "w", encoding="utf-8") as f:
        json.dump(routes_data, f, indent=2, ensure_ascii=False)


def get_graph():
    """Pobiera i łączy sieć drogową oraz tramwajową dla Wrocławia"""
    place_name = "Wroclaw, Poland"

    print(f"[{ts()}] Fetching drive network...")
    t0 = time.perf_counter()
    G_drive = ox.graph_from_place(place_name, network_type="drive")
    print(f"[{ts()}] Drive network loaded in {time.perf_counter() - t0:.1f}s")

    print(f"[{ts()}] Fetching tram network...")
    t0 = time.perf_counter()
    G_tram = ox.graph_from_place(
        place_name, custom_filter='["railway"~"tram"]'
    )
    print(f"[{ts()}] Tram network loaded in {time.perf_counter() - t0:.1f}s")

    print(f"[{ts()}] Combining networks...")
    G_combined = nx.compose(G_drive, G_tram)

    return G_combined, G_drive


def calculate_paths(G_combined, G_drive, routes_data):
    """Liczy realistyczne ścieżki pomiędzy przystankami"""
    start_time = time.perf_counter()
    print(f"[{ts()}] Path calculation started")

    with tqdm(routes_data.items(), desc="Processing lines") as pbar:
        for line, data in pbar:
            pbar.set_description(f"Processing line ({line})")

            for direction in data.get("directions", []):
                stops = direction.get("stops", [])
                path_coordinates = []

                if stops and "lat" in stops[0] and "lon" in stops[0]:
                    path_coordinates.append(
                        [stops[0]["lat"], stops[0]["lon"]]
                    )

                for i in range(len(stops) - 1):
                    start_stop = stops[i]
                    end_stop = stops[i + 1]

                    if (
                        "lat" not in start_stop or "lon" not in start_stop
                        or "lat" not in end_stop or "lon" not in end_stop
                    ):
                        continue

                    try:
                        start_node = ox.nearest_nodes(
                            G_drive,
                            start_stop["lon"],
                            start_stop["lat"],
                        )
                        end_node = ox.nearest_nodes(
                            G_drive,
                            end_stop["lon"],
                            end_stop["lat"],
                        )

                        route = nx.shortest_path(
                            G_combined,
                            start_node,
                            end_node,
                            weight="length",
                        )

                        route_coords = [
                            [
                                G_combined.nodes[node]["y"],
                                G_combined.nodes[node]["x"],
                            ]
                            for node in route
                        ]

                        path_coordinates.extend(route_coords[1:])

                    except (nx.NetworkXNoPath, ValueError):
                        # fallback: linia prosta
                        path_coordinates.append(
                            [end_stop["lat"], end_stop["lon"]]
                        )

                direction["path"] = path_coordinates

            # zapis po każdej linii (bezpieczne przy długim liczeniu)
            save_routes(routes_data)

    print(
        f"[{ts()}] Path calculation finished in "
        f"{time.perf_counter() - start_time:.1f}s"
    )

    return routes_data


def main():
    program_start = time.perf_counter()
    print(f"[{ts()}] Program started")

    print(f"[{ts()}] Loading routes data...")
    with open("mpk_viewer/data/routes.json", "r", encoding="utf-8") as f:
        routes_data = json.load(f)

    G_combined, G_drive = get_graph()

    print(f"[{ts()}] Calculating paths for all routes...")
    calculate_paths(G_combined, G_drive, routes_data)

    print(
        f"[{ts()}] Done. Total time: "
        f"{time.perf_counter() - program_start:.1f}s"
    )


if __name__ == "__main__":
    main()
