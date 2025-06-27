const csrftoken = document.querySelector('[name=csrf-token]').content;

async function fetchDevices() {
    const res = await fetch('/modbus/api/devices/');
    const devices = await res.json();
    const tbody = document.querySelector('#devices-table tbody');
    tbody.innerHTML = '';

    devices
        .forEach(device => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${device.id}</td>
                <td>${device.name}</td>
                <td>${device.is_active}</td>
                <td>${device.is_running}</td>
                <td>
                    ${device.is_running
                        ? `<button onclick="stopDevice(${device.id})">Stop</button>`
                        : `<button onclick="startDevice(${device.id})">Start</button>`}
                </td>
            `;
            tbody.appendChild(tr);
        });
}

async function startDevice(id) {
    await fetch(`/modbus/api/devices/${id}/start/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrftoken },
    });
    await refreshAll();
}

async function stopDevice(id) {
    await fetch(`/modbus/api/devices/${id}/stop/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrftoken },
    });
    await refreshAll();
}

async function fetchServerStatus() {
    const res = await fetch('/modbus/api/server/status/');
    const { running } = await res.json();
    const label = document.getElementById('server_status');
    label.textContent = running ? "Running" : "Stopped";
    label.className = `status-label ${running ? 'running' : 'stopped'}`;
}

async function startServer() {
    await fetch('/modbus/api/server/start/', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrftoken },
    });
    await refreshAll();
}

async function stopServer() {
    await fetch('/modbus/api/server/stop/', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrftoken },
    });
    await refreshAll();
}

async function refreshAll() {
    await fetchDevices();
    await fetchServerStatus();
}

refreshAll();
setInterval(refreshAll, 5000); // Auto-refresh every 5 seconds

document.addEventListener('DOMContentLoaded', async () => {
    const deviceSelect = document.getElementById('device-select');

    try {
        const response = await fetch('/modbus/api/devices/active/');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const devices = await response.json();

        if (devices.length === 0) {
            deviceSelect.innerHTML = '<option disabled>No active devices</option>';
        return;
        }

    deviceSelect.innerHTML = devices.map(device =>
        `<option value="${device.id}">${device.name}</option>`
    ).join('');

    } catch (error) {
        console.error('Failed to load devices:', error);
        deviceSelect.innerHTML = '<option disabled>Error loading devices</option>';
    }
});


document.getElementById('refresh-btn').addEventListener('click', async () => {
    const deviceSelect = document.getElementById('device-select');
    const deviceId = deviceSelect.value;

    const tableBody = document.querySelector('#logs-table tbody');
    const logsContainer = document.getElementById('logs-container'); // Optional message container

    // Clear previous table data
    tableBody.innerHTML = '';
    logsContainer.innerHTML = 'Loading...';

    try {
        const response = await fetch(`/modbus/api/devices/${deviceId}/logs/`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const logs = await response.json();

        logsContainer.innerHTML = ''; // Clear loading or previous messages

    if (logs.length === 0) {
        logsContainer.innerHTML = '<p>No logs found for this device.</p>';
        return;
    }

    // Populate table
    logs.forEach(log => {
        const row = document.createElement('tr');
        const timestamp = new Date(log.timestamp * 1000).toLocaleString();
        const value = JSON.stringify(log.value);

        row.innerHTML = `
            <td>${timestamp}</td>
            <td>${value}</td>
        `;
        tableBody.appendChild(row);
    });

    } catch (error) {
        logsContainer.innerHTML = `<p style="color:red;">Failed to load logs: ${error.message}</p>`;
    }
});