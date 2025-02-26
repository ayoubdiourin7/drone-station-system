import React, { useState } from 'react';

const Parameters = ({ drones }) => {
  const [selectedSize, setSelectedSize] = useState('64x64');
  const [selectedDrone, setSelectedDrone] = useState('');

  const imageSizes = [
    '64x64',
    '128x128',
    '256x256',
    '512x512',
    '1024x1024'
  ];

  return (
    <div className="bg-white rounded-lg shadow-md p-8 w-3/4 max-w-2xl">
      <h2 className="text-2xl font-semibold text-gray-900 mb-6">Parameters Configuration</h2>
      
      <div className="space-y-6">
        {/* Drone Selection */}
        <div className="space-y-2">
          <label htmlFor="drone-select" className="block text-sm font-medium text-gray-700">
            Select Drone
          </label>
          <div className="relative">
            <select
              id="drone-select"
              value={selectedDrone}
              onChange={(e) => setSelectedDrone(e.target.value)}
              className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
            >
              <option value="">Select a drone</option>
              {drones.map((drone) => (
                <option key={drone.id} value={drone.id}>
                  {drone.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Image Size Selection */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">
            Image Size
          </label>
          <div className="grid grid-cols-3 gap-3">
            {imageSizes.map((size) => (
              <button
                key={size}
                type="button"
                onClick={() => setSelectedSize(size)}
                className={`
                  ${selectedSize === size
                    ? 'ring-2 ring-offset-2 ring-blue-500 bg-blue-50'
                    : 'bg-white hover:bg-gray-50'
                  }
                  border rounded-md py-3 px-4 flex items-center justify-center text-sm font-medium text-gray-700
                `}
              >
                {size}
              </button>
            ))}
          </div>
        </div>

        {/* Current Configuration Display */}
        <div className="mt-8 p-4 bg-gray-50 rounded-md">
          <h3 className="text-lg font-medium text-gray-900 mb-2">Current Configuration</h3>
          <div className="space-y-2 text-sm text-gray-600">
            <p>Selected Drone: <span className="font-medium">{selectedDrone || 'None'}</span></p>
            <p>Image Size: <span className="font-medium">{selectedSize}</span></p>
          </div>
        </div>

        {/* Save Button */}
        <div className="mt-6">
          <button
            type="button"
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            Save Parameters
          </button>
        </div>
      </div>
    </div>
  );
};

export default Parameters; 