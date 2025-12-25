import json
import os

def merge_data():
    """
    Merges the processed dataset with the existing routes.json file.
    """
    processed_dir = 'processed_dataset'
    routes_file = 'mpk_viewer/data/routes.json'

    # Read the existing routes data
    try:
        with open(routes_file, 'r', encoding='utf-8') as f:
            routes_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {routes_file} not found. Please run the scraper first.")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {routes_file}.")
        return

    # Read the processed line lists
    with open(os.path.join(processed_dir, 'all_lines.txt'), 'r') as f:
        all_lines = {line.strip() for line in f}
    with open(os.path.join(processed_dir, 'bus_lines.txt'), 'r') as f:
        bus_lines = {line.strip() for line in f}
    with open(os.path.join(processed_dir, 'tram_lines.txt'), 'r') as f:
        tram_lines = {line.strip() for line in f}

    # Identify missing lines
    existing_lines = set(routes_data.keys())
    missing_lines = all_lines - existing_lines

    print(f"Found {len(missing_lines)} missing lines.")

    # Add missing lines to the routes data
    for line in missing_lines:
        line_type = 'bus' if line in bus_lines else 'tram'
        routes_data[line] = {
            "type": line_type,
            "directions": [],
            "source": "processed_dataset_2022"
        }
        print(f"Added missing line: {line} ({line_type})")

    # Write the updated data back to the routes.json file
    with open(routes_file, 'w', encoding='utf-8') as f:
        json.dump(routes_data, f, ensure_ascii=False, indent=2)

    print(f"\nMerge complete. {routes_file} has been updated.")

if __name__ == '__main__':
    merge_data()
