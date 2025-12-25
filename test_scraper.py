
import requests
from bs4 import BeautifulSoup

TIMETABLE_URL = "https://www.wroclaw.pl/komunikacja/rozklady-jazdy"

try:
    response = requests.get(TIMETABLE_URL)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    
    print("Finding headers...")
    headers = soup.find_all('h2', class_='titleSection')
    if headers:
        for header in headers:
            print(f"Found header: {header.get_text(strip=True)}")
    else:
        print("No headers with class 'titleSection' found.")

except requests.exceptions.RequestException as e:
    print(f"Error fetching timetable page: {e}")
