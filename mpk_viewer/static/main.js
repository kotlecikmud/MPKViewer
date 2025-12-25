const map = L.map('map').setView([51.1079, 17.0385], 13);
let vehicleMarkers = [];
let currentBaseLayer;
let selectedLine = null;

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
                    fetchAndDisplayStops(line.line);
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
                    fetchAndDisplayStops(line.line);
                });
                tramList.appendChild(li);
            });
        });
}


function fetchAndDisplayStops(lineId) {
    fetch(`/api/routes/${lineId}`)
        .then(response => response.json())
        .then(data => {
            const stopsContainer = document.getElementById('stops-container');
            stopsContainer.innerHTML = '<h3>Directions & Stops</h3>';

            if (data && data.directions) {
                data.directions.forEach(direction => {
                    const directionEl = document.createElement('div');
                    directionEl.className = 'direction';
                    
                    const header = document.createElement('h4');
                    header.textContent = direction.direction;
                    header.addEventListener('click', () => {
                        // Logic to show stops for this direction
                        selectedLine = lineId;
                        updateVehicleMarkers();
                        
                        // Collapse other direction lists
                        document.querySelectorAll('.stop-list').forEach(list => list.style.display = 'none');
                        // Expand this direction's list
                        const stopList = directionEl.querySelector('.stop-list');
                        stopList.style.display = 'block';
                    });
                    directionEl.appendChild(header);

                    const stopList = document.createElement('ul');
                    stopList.className = 'stop-list';
                    stopList.style.display = 'none'; // Initially hidden
                    direction.stops.forEach(stop => {
                        const stopLi = document.createElement('li');
                        stopLi.textContent = stop;
                        stopList.appendChild(stopLi);
                    });
                    directionEl.appendChild(stopList);

                    stopsContainer.appendChild(directionEl);
                });
            } else {
                stopsContainer.innerHTML += '<p>No stop information available.</p>';
            }
            document.getElementById('right-sidebar').classList.add('open');
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
    document.getElementById('right-sidebar').classList.remove('open');
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
