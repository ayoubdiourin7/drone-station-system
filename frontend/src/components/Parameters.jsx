import React, { useState } from 'react';

const Parameters = ({ drones, onExecute }) => {
  const [selectedSize, setSelectedSize] = useState('original');
  const [selectedDroneId, setSelectedDroneId] = useState('');
  const [parametersSet, setParametersSet] = useState(false);

  const imageSizes = [
    'original',  // Default option to keep original size
    '64x64',
    '128x128',
    '256x256',
    '512x512',
    '1024x1024'
  ];

  const getSizeLabel = (size) => {
    return size === 'original' ? 'Original Size' : size;
  };

  const handleSaveParameters = () => {
    if (selectedDroneId && selectedSize) {
      setParametersSet(true);
    }
  };

  const handleExecute = () => {
    if (!parametersSet) {
      alert('Please save parameters before executing');
      return;
    }
    onExecute(selectedDroneId, selectedSize);
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-8 w-3/4 max-w-2xl">
      <h2 className="text-2xl font-semibold text-gray-900 mb-6">Parameters Configuration</h2>
      
      <div className="space-y-6">
        {/* Drone Selection */}
        <div className="space-y-2">
          <label htmlFor="drone-select" className="block text-sm font-medium text-gray-700">
            Select Connected Drone
          </label>
          <div className="relative">
            <select
              id="drone-select"
              value={selectedDroneId}
              onChange={(e) => setSelectedDroneId(e.target.value)}
              className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
            >
              <option value="">Select a drone</option>
              {drones.map((drone) => (
                <option key={drone.id} value={drone.id}>
                  {drone.name} ({drone.status})
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
                {getSizeLabel(size)}
              </button>
            ))}
          </div>
        </div>

        {/* Current Configuration Display */}
        <div className="mt-8 p-4 bg-gray-50 rounded-md">
          <h3 className="text-lg font-medium text-gray-900 mb-2">Current Configuration</h3>
          <div className="space-y-2 text-sm text-gray-600">
            <p>Selected Drone: <span className="font-medium">{selectedDroneId || 'None'}</span></p>
            <p>Image Size: <span className="font-medium">{getSizeLabel(selectedSize)}</span></p>
            <p>Parameters Status: <span className="font-medium">{parametersSet ? 'Saved' : 'Not Saved'}</span></p>
          </div>
        </div>

        {/* Save Button */}
        <div className="mt-6">
          <button
            onClick={handleSaveParameters}
            disabled={!selectedDroneId || !selectedSize}
            className={`w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white 
              ${(!selectedDroneId || !selectedSize) ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'} 
              focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500`}
          >
            Save Parameters
          </button>
        </div>

        {/* Execute Button */}
        <button
          onClick={handleExecute}
          disabled={!parametersSet}
          className={`w-full py-2 px-4 rounded-lg text-white font-medium
            ${!parametersSet ? 'bg-gray-400 cursor-not-allowed' : 'bg-green-600 hover:bg-green-700'} 
            transition-colors`}
        >
          Execute
        </button>
      </div>
    </div>
  );
};

export default Parameters; 