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

            const routeGroups = {};
            data.directions.forEach(direction => {
                const stops = direction.stops;
                if (stops.length < 2) return;
                const startStop = stops[0].name;
                const endStop = stops[stops.length - 1].name;
                const key = [startStop, endStop].sort().join('-');
                if (!routeGroups[key]) {
                    routeGroups[key] = { directions: [] };
                }
                routeGroups[key].directions.push(direction);
            });

            Object.values(routeGroups).forEach((group) => {
                const groupPolylines = [];
                group.directions.forEach(direction => {
                    const routeCoordinates = direction.stops
                        .filter(stop => stop.lat && stop.lon)
                        .map(stop => [stop.lat, stop.lon]);

                    if (routeCoordinates.length > 0) {
                        const polyline = L.polyline(routeCoordinates, { color: colors[colorIndex % colors.length] });
                        groupPolylines.push(polyline);
                        routePolylines.push(polyline);
                        colorIndex++;
                    }
                });

                groupPolylines.forEach(p => p.addTo(map));

                let labelText;
                if (group.directions.length === 2) {
                    const [dir1, dir2] = group.directions;
                    const [start1, end1] = [dir1.stops[0].name, dir1.stops[dir1.stops.length - 1].name];
                    const [start2, end2] = [dir2.stops[0].name, dir2.stops[dir2.stops.length - 1].name];
                    if (start1 === end2 && end1 === start2) {
                        labelText = `${start1} <-> ${end1}`;
                    }
                }
                if (!labelText) {
                    labelText = group.directions.map(d => d.direction_name).join(' / ');
                }

                const routeControl = document.createElement('div');
                routeControl.style.display = 'flex';
                routeControl.style.alignItems = 'center';
                routeControl.style.padding = '5px 0';

                const visibilityToggle = document.createElement('i');
                visibilityToggle.className = 'fas fa-eye';
                visibilityToggle.style.cursor = 'pointer';
                visibilityToggle.style.marginRight = '10px';
                visibilityToggle.style.width = '20px';
                visibilityToggle.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const isVisible = visibilityToggle.classList.contains('fa-eye');
                    groupPolylines.forEach(p => {
                        if (isVisible) {
                            if (p && map.hasLayer(p)) map.removeLayer(p);
                        } else {
                            if (p && !map.hasLayer(p)) map.addLayer(p);
                        }
                    });
                    visibilityToggle.classList.toggle('fa-eye');
                    visibilityToggle.classList.toggle('fa-eye-slash');
                });

                const routeName = document.createElement('span');
                routeName.textContent = labelText;

                const groupStopList = document.createElement('ul');
                groupStopList.className = 'stop-list';
                groupStopList.style.display = 'none';
                groupStopList.style.paddingLeft = '30px';

                group.directions.forEach(direction => {
                    const dirHeader = document.createElement('li');
                    dirHeader.innerHTML = `<b>${direction.direction_name}</b>`;
                    groupStopList.appendChild(dirHeader);
                    direction.stops.forEach(stop => {
                        const stopLi = document.createElement('li');
                        stopLi.textContent = stop.name;
                        stopLi.style.paddingLeft = '15px';
                        groupStopList.appendChild(stopLi);
                    });
                });

                const routeContainer = document.createElement('div');
                routeContainer.appendChild(routeName);
                routeContainer.appendChild(groupStopList);
                routeContainer.style.cursor = 'pointer';
                routeContainer.addEventListener('click', () => {
                    const isCollapsed = groupStopList.style.display === 'none';
                    groupStopList.style.display = isCollapsed ? 'block' : 'none';
                });

                routeControl.appendChild(visibilityToggle);
                routeControl.appendChild(routeContainer);
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

            const stopsContainer = document.getElementById('stops-container');
            stopsContainer.innerHTML = `<h3>${data.line}</h3><button id="back-to-lines">Back</button>`;
            stopsContainer.appendChild(routeSelectionContainer);
            document.getElementById('back-to-lines').addEventListener('click', () => {
                document.getElementById('stops-container').style.display = 'none';
                document.getElementById('line-selection-container').style.display = 'block';
                selectedLine = null;
                document.querySelectorAll('#bus-list li, #tram-list li').forEach(item => item.classList.remove('selected'));
                routePolylines.forEach(polyline => { if (polyline) map.removeLayer(polyline); });
                routePolylines = [];
                stopMarkers.forEach(marker => marker.remove());
                stopMarkers = [];
                updateVehicleMarkers();
            });

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
