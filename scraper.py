import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os

BASE_URL = "https://www.wroclaw.pl"
TIMETABLE_URL = f"{BASE_URL}/komunikacja/rozklady-jazdy"

def get_line_links():
    """
    Fetches the main timetable page and extracts links and types for all individual line pages.
    Returns a list of tuples: (line_url, line_type)
    """
    print("Fetching list of all lines...")
    try:
        response = requests.get(TIMETABLE_URL)
        response.raise_for_status()
        time.sleep(1)  # Add a 1-second delay
    except requests.exceptions.RequestException as e:
        print(f"Error fetching timetable page: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    lines = []

    def scrape_section(header_text, line_type):
        header = soup.find('h2', class_='titleSection', string=header_text)
        if header:
            list_container = header.find_next_sibling('ul', class_='busTimetableList')
            if list_container:
                links = list_container.find_all('a', href=re.compile(r"/komunikacja/linia-"))
                for a in links:
                    if "linia-" in a['href']:
                        full_url = f"{BASE_URL}{a['href']}" if a['href'].startswith('/') else a['href']
                        lines.append((full_url, line_type))

    scrape_section('Tramwaj', 'tram')
    scrape_section('Autobus dzienny', 'bus')
    
    print(f"Found {len(lines)} line links.")
    return sorted(list(set(lines)))

def get_route_data_for_line(line_url, line_type):
    """
    Fetches a single line page and parses it to extract the routes (directions) and stops.
    """
    line_name_match = re.search(r'linia-([a-zA-Z0-9]+)-wroclaw', line_url)
    if not line_name_match:
        print(f"    Could not extract line name from URL: {line_url}")
        return None
    line_name = line_name_match.group(1)
    
    print(f"  Scraping line: {line_name} ({line_type}) from {line_url}")

    try:
        response = requests.get(line_url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"    Error fetching line page: {e}")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    
    print(f"    Parsing content for line {line_name}...")
    directions_data = []
    
    accordion_containers = soup.find_all('div', class_='accordionContent')
    print(f"    Found {len(accordion_containers)} direction containers.")

    if not accordion_containers:
        print(f"    Could not find any route information containers for line {line_name}.")
        return None

    for i, container in enumerate(accordion_containers):
        direction_div = container.find('div', class_='busDirection')
        if not direction_div:
            continue
            
        direction_spans = direction_div.find_all('span')
        direction_parts = [s.get_text(strip=True) for s in direction_spans if s.get_text(strip=True)]
        direction_name = " -> ".join(direction_parts)
        
        if not direction_name:
            continue

        stops_list = container.find('ul', class_='accordionList')
        if not stops_list:
            continue

        stops = []
        stop_items = stops_list.find_all('li', class_='listItem')

        for item in stop_items:
            stop_name_tag = item.find('a', class_='label')
            if not stop_name_tag:
                continue
            
            stop_name = stop_name_tag.get_text(strip=True)
            top_label_span = item.find('span', class_='topLabel')
            street = top_label_span.get_text(strip=True).replace('(', '').replace(')', '') if top_label_span else 'N/A'

            if stop_name:
                stops.append({
                    "name": stop_name,
                    "street": street
                })
        
        if stops:
            directions_data.append({
                "direction_name": direction_name,
                "stops": stops
            })

    print(f"    Finished parsing for line {line_name}. Found {len(directions_data)} valid directions.")
    return {"line": line_name, "directions": directions_data}


def main():
    """
    Main function to orchestrate the scraping process.
    """
    all_routes = {}
    line_links = get_line_links()

    if not line_links:
        print("No line links found. Exiting.")
        return

    for link, line_type in line_links:
        route_data = get_route_data_for_line(link, line_type)
        if route_data and route_data['directions']:
            all_routes[route_data['line']] = {
                "type": line_type,
                "directions": route_data['directions']
            }
        elif route_data:
            all_routes[route_data['line']] = {
                "type": line_type,
                "directions": []
            }
        
        time.sleep(0.1) # A small delay to be polite

    output_dir = "mpk_viewer/data"
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "routes.json"), 'w', encoding='utf-8') as f:
        json.dump(all_routes, f, ensure_ascii=False, indent=2)

    print(f"\nScraping complete. Data saved to {output_dir}/routes.json")

if __name__ == "__main__":
    main()
