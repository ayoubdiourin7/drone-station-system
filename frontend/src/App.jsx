import React, { useState, useEffect } from 'react';
import { Wifi, Battery, HardDrive, Clock } from 'lucide-react';

function App() {
  const [activeTab, setActiveTab] = useState('connection');
  const [drones, setDrones] = useState([]);

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws/control");

    ws.onopen = () => {
      console.log("[CLIENT] ✅ Connected to WebSocket server");
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "drone_list") {
        console.log("[CLIENT] 📥 Received drone list", data.drones);
        setDrones(data.drones.map(drone_id => ({ name: drone_id, signal: "N/A", battery: "N/A", storage: "N/A", connectionTime: "N/A" })));
      } else if (data.type === "telemetry") {
        setDrones(prevDrones => prevDrones.map(drone =>
          drone.name === data.drone_id
            ? { ...drone, signal: data.signal_strength, battery: `${data.battery}%`, storage: `${data.storage_used}GB`, connectionTime: new Date(data.timestamp * 1000).toLocaleTimeString() }
            : drone
        ));
      }
    };

    ws.onclose = () => {
      console.log("[CLIENT] ❌ Disconnected from WebSocket server");
    };

    return () => ws.close();
  }, []);

  const getSignalColor = (signal) => {
    if (signal === "N/A") return "text-gray-500";
    if (signal >= 80) return "text-green-500";
    if (signal >= 50) return "text-yellow-500";
    return "text-red-500";
  };

  const tabs = [
    { id: 'connection', label: 'Connection' },
    { id: 'parameters', label: 'Parameters' },
    { id: 'database', label: 'Database' },
  ];

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center">
      <header className="bg-white shadow-sm w-full">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8 flex justify-between items-center">
          <h1 className="text-2xl font-semibold text-gray-900"> 
            𖥂 Drone Control Station 𖥂 
          </h1>
        </div>
      </header>

      <nav className="w-full flex justify-center mt-6">
        <div className="border-b border-gray-200 flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-4 px-6 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      <main className="w-full flex flex-col items-center justify-center flex-grow mt-8">
        {activeTab === 'connection' && (
          <div className="bg-white rounded-lg shadow-md p-6 w-3/4 text-center">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Connected Drones</h2>
            {drones.length === 0 ? (
              <p className="text-gray-600">No drones are currently connected.</p>
            ) : (
              <table className="min-w-full bg-white border border-gray-200 rounded-lg">
                <thead>
                  <tr className="bg-gray-100">
                    <th className="py-2 px-4 border-b">Name</th>
                    <th className="py-2 px-4 border-b">Signal Strength</th>
                    <th className="py-2 px-4 border-b">Battery</th>
                    <th className="py-2 px-4 border-b">Storage Available</th>
                    <th className="py-2 px-4 border-b">Connection Time</th>
                  </tr>
                </thead>
                <tbody>
                  {drones.map((drone) => (
                    <tr key={drone.name} className="text-center border-b">
                      <td className="py-2 px-4">{drone.name}</td>
                      <td className="py-2 px-4">
                        <div className="flex items-center space-x-2 justify-center">
                          <Wifi className={`w-5 h-5 ${getSignalColor(drone.signal)}`} />
                          <span>{drone.signal === "N/A" ? "N/A" : `${drone.signal}%`}</span>
                        </div>
                      </td>
                      <td className="py-2 px-4">
                        <div className="flex items-center space-x-2 justify-center">
                          <Battery className="w-5 h-5 text-gray-500" />
                          <span>{drone.battery}</span>
                        </div>
                      </td>
                      <td className="py-2 px-4">
                        <div className="flex items-center space-x-2 justify-center">
                          <HardDrive className="w-5 h-5 text-gray-500" />
                          <span>{drone.storage}</span>
                        </div>
                      </td>
                      <td className="py-2 px-4">
                        <div className="flex items-center space-x-2 justify-center">
                          <Clock className="w-5 h-5 text-gray-500" />
                          <span>{drone.connectionTime}</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
