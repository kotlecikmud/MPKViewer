const map = L.map('map').setView([51.1079, 17.0385], 13);
let vehicleMarkers = [];
let currentBaseLayer;
let selectedLine = null;
let routePolylines = [];
let stopMarkers = [];

// --- Map Layers ---
const streetLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
});
const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    attribution: 'Tiles &copy; Esri'
});
const darkLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
});

function setStreetViewTheme() {
    const hour = new Date().getHours();
    const isNight = hour < 6 || hour >= 20;
    const targetLayer = isNight ? darkLayer : streetLayer;
    if (currentBaseLayer !== targetLayer) {
        if (currentBaseLayer) {
            map.removeLayer(currentBaseLayer);
        }
        map.addLayer(targetLayer);
        currentBaseLayer = targetLayer;
    }
}

function updateVehicleMarkers() {
    fetch('/api/vehicles')
        .then(response => response.json())
        .then(data => {
            vehicleMarkers.forEach(marker => marker.remove());
            vehicleMarkers = [];
            data.forEach(vehicle => {
                if (selectedLine && vehicle.line !== selectedLine) {
                    return;
                }
                const marker = L.circleMarker([vehicle.lat, vehicle.lon], {
                    radius: 8,
                    fillColor: vehicle.type === 'bus' ? '#ff7800' : '#0078ff',
                    color: '#000',
                    weight: 1,
                    opacity: 1,
                    fillOpacity: 0.8
                }).addTo(map);
                marker.bindPopup(`<b>Line:</b> ${vehicle.line}<br><b>Type:</b> ${vehicle.type}`);
                vehicleMarkers.push(marker);
            });
        });
}

function fetchAndDisplayLines() {
    fetch('/api/routes')
        .then(response => response.json())
        .then(data => {
            const busList = document.getElementById('bus-list');
            const tramList = document.getElementById('tram-list');
            busList.innerHTML = '';
            tramList.innerHTML = '';

            // Separate and sort lines
            const buses = data.filter(line => line.type === 'bus').sort((a, b) => a.line.localeCompare(b.line, undefined, {numeric: true}));
            const trams = data.filter(line => line.type === 'tram').sort((a, b) => a.line.localeCompare(b.line, undefined, {numeric: true}));

            buses.forEach(line => {
                const li = document.createElement('li');
                li.textContent = line.line;
                li.dataset.lineId = line.line;
                li.addEventListener('click', () => {
                    document.querySelectorAll('#bus-list li, #tram-list li').forEach(item => item.classList.remove('selected'));
                    li.classList.add('selected');
                    displayRoute(line.line);
                });
                busList.appendChild(li);
            });

            trams.forEach(line => {
                const li = document.createElement('li');
                li.textContent = line.line;
                li.dataset.lineId = line.line;
                li.addEventListener('click', () => {
                    document.querySelectorAll('#bus-list li, #tram-list li').forEach(item => item.classList.remove('selected'));
                    li.classList.add('selected');
                    displayRoute(line.line);
                });
                tramList.appendChild(li);
            });
        });
}


function displayRoute(lineId) {
    selectedLine = lineId;
    updateVehicleMarkers();

    fetch(`/api/routes/${lineId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                const stopsContainer = document.getElementById('stops-container');
                stopsContainer.innerHTML = `<h3>${lineId}</h3><p>${data.error}</p>`;
                if (data.source) {
                    stopsContainer.innerHTML += `<p>Data from: ${data.source}</p>`;
                }
                document.getElementById('line-selection-container').style.display = 'none';
                stopsContainer.style.display = 'block';
                return;
            }

            routePolylines.forEach(polyline => map.removeLayer(polyline));
            routePolylines = [];

            stopMarkers.forEach(marker => marker.remove());
            stopMarkers = [];
            
            const colors = ['blue', 'red', 'green', 'purple', 'orange', 'black'];
            let colorIndex = 0;

            const routeSelectionContainer = document.getElementById('route-selection-container');
            routeSelectionContainer.innerHTML = '<h4>Routes</h4>';

            data.directions.forEach((direction, index) => {
                const routeCoordinates = direction.stops
                    .filter(stop => stop.lat && stop.lon)
                    .map(stop => [stop.lat, stop.lon]);

                let polyline;
                if (routeCoordinates.length > 0) {
                    polyline = L.polyline(routeCoordinates, { color: colors[colorIndex % colors.length] }).addTo(map);
                    routePolylines.push(polyline);
                    colorIndex++;
                }

                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.id = `route-${index}`;
                checkbox.checked = true;
                checkbox.addEventListener('change', () => {
                    if (checkbox.checked) {
                        if (polyline) map.addLayer(polyline);
                    } else {
                        if (polyline) map.removeLayer(polyline);
                    }
                });

                const label = document.createElement('label');
                label.htmlFor = `route-${index}`;
                label.textContent = direction.direction_name;
                
                const routeControl = document.createElement('div');
                routeControl.appendChild(checkbox);
                routeControl.appendChild(label);
                routeSelectionContainer.appendChild(routeControl);
            });

            if (routePolylines.length > 0) {
                const group = new L.featureGroup(routePolylines);
                map.fitBounds(group.getBounds());
            }

            data.directions.forEach(direction => {
                direction.stops.forEach(stop => {
                    if (stop.lat && stop.lon) {
                        const marker = L.circleMarker([stop.lat, stop.lon], {
                            radius: 5,
                            fillColor: '#ffffff',
                            color: '#000',
                            weight: 1,
                            opacity: 1,
                            fillOpacity: 0.8
                        }).addTo(map);
                        marker.bindPopup(`<b>${stop.name}</b><br>${stop.street}`);
                        stopMarkers.push(marker);
                    }
                });
            });

            // Populate the stops container
            const stopsContainer = document.getElementById('stops-container');
            stopsContainer.innerHTML = `<h3>${data.line}</h3><button id="back-to-lines">Back</button>`;
            stopsContainer.appendChild(routeSelectionContainer);
            document.getElementById('back-to-lines').addEventListener('click', () => {
                document.getElementById('stops-container').style.display = 'none';
                document.getElementById('line-selection-container').style.display = 'block';
                selectedLine = null;
                document.querySelectorAll('#bus-list li, #tram-list li').forEach(item => item.classList.remove('selected'));
                routePolylines.forEach(polyline => map.removeLayer(polyline));
                routePolylines = [];
                stopMarkers.forEach(marker => marker.remove());
                stopMarkers = [];
                updateVehicleMarkers();
            });

            data.directions.forEach(direction => {
                const directionEl = document.createElement('div');
                directionEl.className = 'direction';
                
                const header = document.createElement('h4');
                header.textContent = direction.direction_name;
                directionEl.appendChild(header);

                const stopList = document.createElement('ul');
                stopList.className = 'stop-list';
                direction.stops.forEach(stop => {
                    const stopLi = document.createElement('li');
                    stopLi.textContent = stop.name;
                    stopList.appendChild(stopLi);
                });
                directionEl.appendChild(stopList);

                stopsContainer.appendChild(directionEl);
            });

            // Hide line selection and show stops container
            document.getElementById('line-selection-container').style.display = 'none';
            stopsContainer.style.display = 'block';
        })
        .catch(error => {
            console.error("Error fetching route data:", error);
        });
}


// --- Sidebar Toggle ---
document.getElementById('toggle-left-sidebar').addEventListener('click', () => {
    document.getElementById('left-sidebar').classList.toggle('closed');
});
document.getElementById('toggle-right-sidebar').addEventListener('click', () => {
    document.getElementById('right-sidebar').classList.toggle('closed');
});


// --- Event Listeners ---
document.getElementById('street-view-btn').addEventListener('click', () => {
    if (map.hasLayer(satelliteLayer)) map.removeLayer(satelliteLayer);
    setStreetViewTheme();
});
document.getElementById('satellite-view-btn').addEventListener('click', () => {
    if (currentBaseLayer) map.removeLayer(currentBaseLayer);
    currentBaseLayer = null; // We are no longer on a "base" layer
    if (!map.hasLayer(satelliteLayer)) map.addLayer(satelliteLayer);
});
document.getElementById('reset-view-btn').addEventListener('click', () => {
    selectedLine = null;
    document.querySelectorAll('#bus-list li, #tram-list li').forEach(item => item.classList.remove('selected'));
    
    routePolylines.forEach(polyline => map.removeLayer(polyline));
    routePolylines = [];

    stopMarkers.forEach(marker => marker.remove());
    stopMarkers = [];

    // Hide stops and show line selection
    document.getElementById('stops-container').style.display = 'none';
    document.getElementById('line-selection-container').style.display = 'block';

    updateVehicleMarkers(); // Update to show all vehicles
});


// --- Initial Load ---
setStreetViewTheme();
updateVehicleMarkers();
fetchAndDisplayLines();
setInterval(updateVehicleMarkers, 15000);
setInterval(() => {
    if (!map.hasLayer(satelliteLayer)) {
        setStreetViewTheme();
    }
}, 300000);
