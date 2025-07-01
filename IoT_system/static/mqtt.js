const baseURL = "/mqtt/api/";

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

async function fetchPublisherStatus() {
    const res = await fetch('/mqtt/api/publisher/status/');
    const { running } = await res.json();
    const label = document.getElementById('mqtt_publisher_status');
    label.textContent = running ? "Running" : "Stopped";
    label.className = `status-label ${running ? 'running' : 'stopped'}`;
}

async function startPublisher() {
    await fetch('/mqtt/api/publisher/start/', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrftoken },
        });
    await refreshAll();
}

async function stopPublisher() {
    await fetch('/mqtt/api/publisher/stop/', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrftoken },
        });
    await refreshAll();
}

async function fetchSubscriberStatus() {
    const res = await fetch('/mqtt/api/subscriber/status/');
    const { running } = await res.json();
    const label = document.getElementById('mqtt_subscriber_status');
    label.textContent = running ? "Running" : "Stopped";
    label.className = `status-label ${running ? 'running' : 'stopped'}`;
}

async function startSubscriber() {
    await fetch('/mqtt/api/subscriber/start/', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrftoken },
        });
    await refreshAll();
}

async function stopSubscriber() {
    await fetch('/mqtt/api/subscriber/stop/', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrftoken },
        });
    await refreshAll();
}

async function fetchData() {
    const tableBody = document.querySelector("#data-table tbody");
    tableBody.innerHTML = "<tr><td colspan='4'>Loading data...</td></tr>";

    try {
        const response = await fetch(baseURL + "mqtt-data/");
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        if (data.length === 0) {
            tableBody.innerHTML = "<tr><td colspan='4'>No data available</td></tr>";
            return;
        }

        tableBody.innerHTML = "";
        data.forEach(item => {
            const row = document.createElement("tr");
            const timestamp = new Date(item.timestamp * 1000).toLocaleString();

            row.innerHTML = `
                <td>${timestamp}</td>
                <td>${item.name}</td>
                <td>${item.symbol}</td>
                <td>${item.priceUsd.toFixed(2)}</td>
            `;
            tableBody.appendChild(row);
        });
    } catch (err) {
        console.error("Error fetching data:", err);
        tableBody.innerHTML = `<tr><td colspan='4'>Error loading data: ${err.message}</td></tr>`;
    }
}

async function sendCommand() {
    const serialNumber = document.getElementById("serial_number").value;
    const command = document.getElementById("command").value;
    const qos = document.getElementById("qos").value;
    const statusText = document.getElementById("status");
    const csrfToken = getCookie('csrftoken');

    if (!serialNumber || !command) {
        statusText.textContent = "Error: Both device serial number and command are required!";
        statusText.style.color = "red";
        return;
    }

    statusText.textContent = "Sending command...";
    statusText.style.color = "blue";

    try {
        const response = await fetch(baseURL + "mqtt-control/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                'X-CSRFToken': csrfToken
            },
            credentials: "include",
            body: JSON.stringify({
                serial_number: serialNumber,  // Matches your API field name
                command: command,
                qos: parseInt(qos)
            })
        });

        const result = await response.json();
        
        if (response.ok) {
            statusText.innerHTML = `
                <strong>Command sent successfully!</strong><br>
                Device: ${result.device || 'N/A'}<br>
                Serial: ${result.serial_number || serialNumber}<br>
                Topic: ${result.mqtt_topic || 'N/A'}<br>
                QoS: ${result.qos || qos}
            `;
            statusText.style.color = "green";
        } else {
            throw new Error(result.error || "Failed to send command");
        }
    } catch (err) {
        console.error("Error sending command:", err);
        statusText.textContent = `Error: ${err.message}`;
        statusText.style.color = "red";
    }
}

async function refreshAll() {
    await fetchPublisherStatus();
    await fetchSubscriberStatus();
}

refreshAll();
setInterval(refreshAll, 5000); // Auto-refresh every 5 seconds

// Load data when page loads
document.addEventListener('DOMContentLoaded', fetchData);