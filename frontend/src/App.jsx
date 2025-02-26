import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import Navigation from './components/Navigation';
import DroneTable from './components/DroneTable';
import Parameters from './components/Parameters';

function App() {
  const [activeTab, setActiveTab] = useState('connection');
  const [drones, setDrones] = useState([]);
  const [ws, setWs] = useState(null);
  const [connectionAttempts, setConnectionAttempts] = useState({});

  useEffect(() => {
    const websocket = new WebSocket("ws://localhost:8000/ws/ui");

    websocket.onopen = () => {
      console.log("[CLIENT] ✅ Connected to WebSocket server");
      setWs(websocket);
    };

    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("[CLIENT] Received WebSocket message:", data);

      if (data.type === "drone_list") {
        console.log("[CLIENT] 📥 Received drone list", data.drones);
        setDrones(prevDrones => {
          const existingDronesMap = new Map(
            prevDrones.map(drone => [drone.id, drone])
          );
          
          return data.drones.map(drone_id => ({
            ...(existingDronesMap.get(drone_id) || {
              id: drone_id,
              name: drone_id,
              signal: "N/A",
              battery: "N/A",
              storage: "N/A",
              connectionTime: new Date().toLocaleTimeString(),
              status: 'available'
            })
          }));
        });
      } else if (data.type === "telemetry") {
        console.log("[CLIENT] 📡 Received telemetry for drone:", data.drone_id);
        setDrones(prevDrones => prevDrones.map(drone =>
          drone.id === data.drone_id ? {
            ...drone,
            signal: data.signal_strength,
            battery: `${data.battery}%`,
            storage: `${data.storage_used.toFixed(1)}GB`,
            connectionTime: new Date(data.timestamp * 1000).toLocaleTimeString(),
            status: 'connected'
          } : drone
        ));
      } else if (data.type === "connection_success") {
        setDrones(prevDrones => prevDrones.map(drone =>
          drone.id === data.drone_id ? {
            ...drone,
            status: 'connected',
            connectionTime: new Date().toLocaleTimeString()
          } : drone
        ));
        setConnectionAttempts(prev => ({ ...prev, [data.drone_id]: false }));
      } else if (data.type === "connection_error") {
        setDrones(prevDrones => prevDrones.map(drone =>
          drone.id === data.drone_id ? {
            ...drone,
            status: 'error'
          } : drone
        ));
        setConnectionAttempts(prev => ({ ...prev, [data.drone_id]: false }));
      } else if (data.type === "drone_disconnected") {
        setDrones(prevDrones => prevDrones.map(drone =>
          drone.id === data.drone_id ? {
            ...drone,
            status: 'available',
            signal: "N/A",
            battery: "N/A",
            storage: "N/A"
          } : drone
        ));
      }
    };

    websocket.onclose = () => {
      console.log("[CLIENT] ❌ Disconnected from WebSocket server");
      setWs(null);
    };

    return () => websocket.close();
  }, []);

  const handleDroneConnection = async (droneId, connect) => {
    if (!ws) {
      console.error('WebSocket connection not available');
      return;
    }

    try {
      if (connect) {
        setDrones(prevDrones => prevDrones.map(drone =>
          drone.id === droneId ? { ...drone, status: 'connecting' } : drone
        ));
        setConnectionAttempts(prev => ({ ...prev, [droneId]: true }));
      }

      ws.send(JSON.stringify({
        type: connect ? 'connect_drone' : 'disconnect_drone',
        drone_id: droneId
      }));
    } catch (error) {
      console.error('Error sending connection command:', error);
      setDrones(prevDrones => prevDrones.map(drone =>
        drone.id === droneId ? { ...drone, status: 'error' } : drone
      ));
      setConnectionAttempts(prev => ({ ...prev, [droneId]: false }));
    }
  };

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
      <Header />
      <Navigation activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="w-full flex flex-col items-center justify-center flex-grow mt-8">
        {activeTab === 'connection' && (
          <DroneTable 
            drones={drones} 
            onConnect={(droneId) => handleDroneConnection(droneId, true)}
            onDisconnect={(droneId) => handleDroneConnection(droneId, false)}
          />
        )}
        {activeTab === 'parameters' && <Parameters drones={drones.filter(d => d.status === 'connected')} />}
        {activeTab === 'database' && (
          <div className="bg-white rounded-lg shadow-md p-6 w-3/4 text-center">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Database Management</h2>
            <p className="text-gray-600">Database management features coming soon...</p>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
