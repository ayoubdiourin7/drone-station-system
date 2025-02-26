import React from 'react';
import { Wifi, Battery, HardDrive, Clock, Power, AlertCircle } from 'lucide-react';

const DroneTable = ({ drones, onConnect, onDisconnect }) => {
  const getSignalColor = (signal) => {
    if (signal === "N/A") return "text-gray-500";
    if (signal >= 80) return "text-green-500";
    if (signal >= 50) return "text-yellow-500";
    return "text-red-500";
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      connected: {
        bgColor: 'bg-green-100',
        textColor: 'text-green-800',
        icon: <Wifi className="w-4 h-4 mr-1" />,
        label: 'Connected'
      },
      connecting: {
        bgColor: 'bg-yellow-100',
        textColor: 'text-yellow-800',
        icon: <AlertCircle className="w-4 h-4 mr-1 animate-pulse" />,
        label: 'Connecting...'
      },
      available: {
        bgColor: 'bg-gray-100',
        textColor: 'text-gray-800',
        icon: <Power className="w-4 h-4 mr-1" />,
        label: 'Available'
      },
      error: {
        bgColor: 'bg-red-100',
        textColor: 'text-red-800',
        icon: <AlertCircle className="w-4 h-4 mr-1" />,
        label: 'Connection Error'
      }
    };

    const config = statusConfig[status] || statusConfig.available;

    return (
      <span className={`
        inline-flex items-center px-3 py-1 rounded-full text-sm font-medium
        ${config.bgColor} ${config.textColor}
        transition-all duration-200 ease-in-out
      `}>
        {config.icon}
        {config.label}
      </span>
    );
  };

  const getConnectionButton = (drone) => {
    const isConnected = drone.status === 'connected';
    const isConnecting = drone.status === 'connecting';

    return (
      <button
        onClick={() => isConnected ? onDisconnect(drone.id) : onConnect(drone.id)}
        disabled={isConnecting}
        className={`
          flex items-center justify-center px-4 py-2 rounded-md text-sm font-medium
          transition-all duration-200 ease-in-out
          ${isConnected 
            ? 'bg-red-100 text-red-700 hover:bg-red-200 focus:ring-red-500' 
            : 'bg-green-100 text-green-700 hover:bg-green-200 focus:ring-green-500'}
          ${isConnecting ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
          focus:outline-none focus:ring-2 focus:ring-offset-2
        `}
      >
        <Power className={`w-4 h-4 mr-2 ${isConnecting ? 'animate-spin' : ''}`} />
        {isConnecting ? 'Connecting...' : (isConnected ? 'Disconnect' : 'Connect')}
      </button>
    );
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 w-3/4 text-center">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-semibold text-gray-900">Drone Management</h2>
        <div className="flex items-center space-x-2">
          <span className="text-sm text-gray-500">Status Legend:</span>
          {getStatusBadge('connected')}
          {getStatusBadge('available')}
        </div>
      </div>

      {drones.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gray-100 mb-4">
            <Wifi className="w-8 h-8 text-gray-400" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Drones Available</h3>
          <p className="text-gray-500 max-w-sm mx-auto">
            Turn on your drones and make sure they're within range to see them here.
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Signal</th>
                <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Battery</th>
                <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Storage</th>
                <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Connected Since</th>
                <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {drones.map((drone) => (
                <tr 
                  key={drone.id}
                  className={`
                    ${drone.status === 'connected' ? 'bg-green-50' : 'hover:bg-gray-50'}
                    transition-colors duration-150 ease-in-out
                  `}
                >
                  <td className="py-4 px-4">{getStatusBadge(drone.status)}</td>
                  <td className="py-4 px-4 font-medium text-gray-900">{drone.name}</td>
                  <td className="py-4 px-4">
                    <div className="flex items-center space-x-2">
                      <Wifi className={`w-5 h-5 ${getSignalColor(drone.signal)}`} />
                      <span>{drone.signal === "N/A" ? "N/A" : `${drone.signal}%`}</span>
                    </div>
                  </td>
                  <td className="py-4 px-4">
                    <div className="flex items-center space-x-2">
                      <Battery className={`w-5 h-5 ${drone.battery === "N/A" ? "text-gray-400" : "text-gray-600"}`} />
                      <span>{drone.battery}</span>
                    </div>
                  </td>
                  <td className="py-4 px-4">
                    <div className="flex items-center space-x-2">
                      <HardDrive className={`w-5 h-5 ${drone.storage === "N/A" ? "text-gray-400" : "text-gray-600"}`} />
                      <span>{drone.storage}</span>
                    </div>
                  </td>
                  <td className="py-4 px-4">
                    <div className="flex items-center space-x-2">
                      <Clock className="w-5 h-5 text-gray-500" />
                      <span>{drone.connectionTime}</span>
                    </div>
                  </td>
                  <td className="py-4 px-4">
                    {getConnectionButton(drone)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default DroneTable; 