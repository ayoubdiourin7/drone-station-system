import React, { useState, useEffect, useRef } from 'react';
import Header from './components/Header';
import Navigation from './components/Navigation';
import DroneTable from './components/DroneTable';
import Parameters from './components/Parameters';

function App() {
  const [activeTab, setActiveTab] = useState('connection');
  const [drones, setDrones] = useState([]);
  const [ws, setWs] = useState(null);
  const [connectionAttempts, setConnectionAttempts] = useState({});
  const [selectedDrone, setSelectedDrone] = useState(null);
  const [currentImage, setCurrentImage] = useState(null);
  const [lastFrameTime, setLastFrameTime] = useState(null);
  const [fps, setFps] = useState(0);
  const [frameCount, setFrameCount] = useState(0);
  const fpsUpdateInterval = useRef(null);
  const frameTimestamps = useRef([]);
  const MAX_TIMESTAMPS = 30; // Keep last 30 frames for FPS calculation

  const calculateFPS = (timestamps) => {
    if (timestamps.length < 2) return 0;
    
    // Calculate time difference between oldest and newest frame
    const timeWindow = timestamps[timestamps.length - 1] - timestamps[0];
    // Calculate FPS based on number of frames in the window
    return Math.round((timestamps.length - 1) / (timeWindow / 1000));
  };

  const updateFPS = (timestamp) => {
    const timestamps = frameTimestamps.current;
    
    // Add new timestamp
    timestamps.push(timestamp);
    
    // Remove old timestamps (keep only last MAX_TIMESTAMPS frames)
    while (timestamps.length > MAX_TIMESTAMPS) {
      timestamps.shift();
    }
    
    // Calculate and update FPS
    setFps(calculateFPS(timestamps));
  };

  useEffect(() => {
    const websocket = new WebSocket("ws://localhost:8000/ws/ui");

    websocket.onopen = () => {
      console.log("[CLIENT] ✅ Connected to WebSocket server");
      setWs(websocket);
    };

    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("[CLIENT] Received WebSocket message:", data.type);

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
        console.log("[CLIENT] Connection successful for drone:", data.drone_id);
      } else if (data.type === "connection_error") {
        console.log("[CLIENT] Connection error for drone:", data.drone_id);
        setDrones(prevDrones => prevDrones.map(drone =>
          drone.id === data.drone_id ? {
            ...drone,
            status: 'available',
            signal: "N/A",
            battery: "N/A",
            storage: "N/A",
            connectionTime: null
          } : drone
        ));
        setConnectionAttempts(prev => ({ ...prev, [data.drone_id]: false }));
      } else if (data.type === "drone_disconnected") {
        console.log("[CLIENT] Drone disconnected:", data.drone_id);
        setDrones(prevDrones => {
          const updatedDrones = prevDrones.map(drone =>
            drone.id === data.drone_id ? {
              ...drone,
              status: 'available',
              signal: "N/A",
              battery: "N/A",
              storage: "N/A",
              connectionTime: null
            } : drone
          );
          console.log("[CLIENT] Updated drones after disconnection:", updatedDrones);
          return updatedDrones;
        });

        if (selectedDrone === data.drone_id) {
          console.log("[CLIENT] Clearing selected drone after disconnection");
          setSelectedDrone(null);
        }
      } else if (data.type === "video_frame") {
        try {
          const now = Date.now();
          updateFPS(now); // Update FPS with new frame timestamp
          
          if (lastFrameTime) {
            const frameInterval = now - lastFrameTime;
            console.log(`[FRONTEND] ⏱️ Frame interval: ${frameInterval}ms`);
          }
          setLastFrameTime(now);
          setCurrentImage(`data:image/jpeg;base64,${data.frame}`);
          setFrameCount(prev => prev + 1);
        } catch (error) {
          console.error("[FRONTEND] ❌ Error processing frame:", error);
        }
      } else if (data.type === "stream_error") {
        console.error(`[FRONTEND] 🚫 Stream error for drone ${data.drone_id}:`, data.error);
      }
    };

    websocket.onclose = () => {
      console.log("[CLIENT] ❌ Disconnected from WebSocket server");
      setWs(null);
    };

    return () => {
      frameTimestamps.current = []; // Clear timestamps on unmount
      websocket.close();
    };
  }, []);

  const handleDroneConnection = async (droneId, connect) => {
    if (!ws) {
      console.error('WebSocket connection not available');
      return;
    }

    try {
      if (connect) {
        console.log("[CLIENT] Attempting to connect to drone:", droneId);
        setDrones(prevDrones => prevDrones.map(drone =>
          drone.id === droneId ? { ...drone, status: 'connecting' } : drone
        ));
        setConnectionAttempts(prev => ({ ...prev, [droneId]: true }));
      } else {
        console.log("[CLIENT] Disconnecting drone:", droneId);
        setDrones(prevDrones => prevDrones.map(drone =>
          drone.id === droneId ? { ...drone, status: 'disconnecting' } : drone
        ));
      }

      ws.send(JSON.stringify({
        type: connect ? 'connect_drone' : 'disconnect_drone',
        drone_id: droneId
      }));
    } catch (error) {
      console.error('Error handling drone connection:', error);
      setDrones(prevDrones => prevDrones.map(drone =>
        drone.id === droneId ? {
          ...drone,
          status: 'available',
          signal: "N/A",
          battery: "N/A",
          storage: "N/A",
          connectionTime: null
        } : drone
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
    { id: 'database', label: 'Live View & Database' },
  ];

  const handleExecute = (droneId, imageSize) => {
    console.log('[CLIENT] Starting execution for drone:', droneId, 'with size:', imageSize);
    
    if (!ws) {
      console.error('WebSocket connection not available');
      return;
    }

    try {
      setSelectedDrone(droneId);
      setCurrentImage(null); // Reset current image
      
      const streamCommand = {
        type: 'start_streaming',
        drone_id: droneId,
        parameters: {
          image_size: imageSize
        }
      };
      
      console.log('[CLIENT] Sending stream command:', streamCommand);
      ws.send(JSON.stringify(streamCommand));
      setActiveTab('database');
    } catch (error) {
      console.error('Error starting streaming:', error);
    }
  };

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
        {activeTab === 'parameters' && <Parameters drones={drones.filter(d => d.status === 'connected')} onExecute={handleExecute} />}
        {activeTab === 'database' && (
          <div className="w-full max-w-7xl mx-auto px-4">
            <div className="grid grid-cols-1 gap-6">
              <div className="bg-gray-900 rounded-lg shadow-xl p-6 relative">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-xl font-semibold text-white flex items-center">
                    <div className="w-2 h-2 bg-red-500 rounded-full mr-2 animate-pulse"></div>
                    Live Image Stream
                  </h2>
                  <div className="flex items-center space-x-4">
                    {lastFrameTime && (
                      <span className="text-gray-400 text-sm">
                        Last frame: {new Date(lastFrameTime).toLocaleTimeString()}
                      </span>
                    )}
                    <div className="bg-gray-800 px-4 py-2 rounded-full">
                      <span className="text-2xl font-bold text-green-500">{fps}</span>
                      <span className="text-gray-400 text-sm ml-1">FPS</span>
                    </div>
                  </div>
                </div>
                {currentImage ? (
                  <div className="relative group">
                    <div className="absolute inset-0 bg-gradient-to-t from-gray-900 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                    <img 
                      src={currentImage} 
                      alt="Live stream" 
                      className="w-full h-auto rounded-lg shadow-2xl border-2 border-gray-800"
                      style={{
                        maxHeight: '70vh',
                        objectFit: 'contain'
                      }}
                    />
                    <div className="absolute bottom-0 left-0 right-0 p-4 text-white opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <div className="flex items-center">
                            <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse mr-2"></div>
                            <span className="text-sm font-medium">Live</span>
                          </div>
                          {selectedDrone && (
                            <span className="text-sm bg-gray-800 px-2 py-1 rounded">
                              Drone ID: {selectedDrone}
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-gray-300">
                          {new Date().toLocaleDateString()}
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-96 bg-gray-800 rounded-lg border-2 border-gray-700 border-dashed">
                    <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-green-500 mb-4"></div>
                    <p className="text-gray-400 text-lg">Waiting for image stream...</p>
                    <p className="text-gray-500 text-sm mt-2">Connect to a drone to start streaming</p>
                  </div>
                )}
              </div>
              <div className="bg-white rounded-lg shadow-md p-6">
                <h2 className="text-lg font-medium text-gray-900 mb-4">Recorded Footage</h2>
                <p className="text-gray-600">This section will contain the recorded video database.</p>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
