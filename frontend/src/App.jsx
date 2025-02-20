import React, { useState } from 'react';
import { Wifi, Battery, Database, HardDrive } from 'lucide-react';

function App() {
  const [isConnected, setIsConnected] = useState(false);
  const [activeTab, setActiveTab] = useState('connection');

  const tabs = [
    { id: 'connection', label: 'Connection' },
    { id: 'parameters', label: 'Parameters' },
    { id: 'database', label: 'Database' },
  ];

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center">
      {/* Header */}
      <header className="bg-white shadow-sm w-full">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8 flex justify-between items-center">
          <h1 className="text-2xl font-semibold text-gray-900"> 
            𖥂 Drone Control Station 𖥂 
          </h1>
          <div className="flex items-center space-x-2">
            <span className="text-sm">Status: {isConnected ? 'Connected' : 'Disconnected'}</span>
            <Wifi className={`w-5 h-5 ${isConnected ? 'text-green-500' : 'text-red-500'}`} />
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
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

      {/* Main Content */}
      <main className="w-full flex flex-col items-center justify-center flex-grow mt-8">
        {activeTab === 'connection' && (
          <div className="bg-white rounded-lg shadow-md p-6 w-96 text-center">
            <h2 className="text-lg font-medium text-gray-900 mb-4">WiFi Connection</h2>
            <button
              onClick={() => setIsConnected(!isConnected)}
              className="w-full bg-gray-900 text-white py-3 px-4 rounded-md hover:bg-gray-800 transition-colors duration-200"
            >
              {isConnected ? 'Disconnect' : 'Connect'}
            </button>
          </div>
        )}
        
        {isConnected && activeTab === 'connection' && (
          <div className="bg-white rounded-lg shadow-md p-6 w-96 text-center mt-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Drone Status</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Wifi className="w-5 h-5 text-gray-500" />
                  <span className="text-sm text-gray-600">Signal Strength</span>
                </div>
                <span className="text-sm font-medium">Excellent</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Battery className="w-5 h-5 text-gray-500" />
                  <span className="text-sm text-gray-600">Battery</span>
                </div>
                <span className="text-sm font-medium">85%</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <HardDrive className="w-5 h-5 text-gray-500" />
                  <span className="text-sm text-gray-600">Storage Available</span>
                </div>
                <span className="text-sm font-medium">2.1GB</span>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
} 

export default App;
