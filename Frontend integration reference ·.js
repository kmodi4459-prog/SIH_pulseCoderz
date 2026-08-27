

 // Install (in frontend): npm install socket.io-client


import { io } from "socket.io-client";
import { useEffect, useState } from "react";

const API_BASE = "http://localhost:3000"; 

//  1. LOGIN 
async function loginOfficial(officialId, password) {
  const res = await fetch(`${API_BASE}/official/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ officialId, password })
  });
  return res.json();
}

//  2. GET PRIORITY CASES (dashboard's "urgent victims" list) 
async function getPriorityCases(n = 5) {
  const res = await fetch(`${API_BASE}/priority-cases?n=${n}`);
  return res.json();
}

//  3. GET ALERTS 
async function getAlerts(status = "open") {
  const res = await fetch(`${API_BASE}/alerts?status=${status}`);
  return res.json();
}

//  4. REACT COMPONENT EXAMPLE — Dashboard with live alerts 
function DashboardExample() {
  const [alerts, setAlerts] = useState([]);
  const [priorityCases, setPriorityCases] = useState([]);
  const [liveNotification, setLiveNotification] = useState(null);

  useEffect(() => {
    // Initial load
    getAlerts("open").then(data => setAlerts(data.alerts || []));
    getPriorityCases(5).then(data => setPriorityCases(data.topCases || []));

    // Real-time connection — listens for new alerts as they happen
    const socket = io(API_BASE);

    socket.on("connect", () => {
      console.log("Connected to real-time alert feed");
    });

    socket.on("newAlert", (alertData) => {
      console.log("New alert received:", alertData);
      setLiveNotification(alertData);       // show a popup/toast in the UI
      setAlerts(prev => [alertData, ...prev]); // add to the alert list
      getPriorityCases(5).then(data => setPriorityCases(data.topCases || [])); // refresh ranking
    });

    return () => socket.disconnect(); // cleanup when component unmounts
  }, []);

  return (
    <div>
      {liveNotification && (
        <div style={{ background: "red", color: "white", padding: "10px" }}>
          🚨 New {liveNotification.riskLevel} alert for {liveNotification.victimId} (score: {liveNotification.score})
        </div>
      )}

      <h2>Priority Cases</h2>
      {priorityCases.map(c => (
        <div key={c.victimId}>{c.victimId} — Score: {c.score} — Risk: {c.riskLevel}</div>
      ))}

      <h2>Open Alerts</h2>
      {alerts.map((a, i) => (
        <div key={i}>{a.victimId} — {a.riskLevel} — {a.status}</div>
      ))}
    </div>
  );
}

export default DashboardExample;