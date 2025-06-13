import React from 'react';

interface VariableDisplayProps {
  variables: string[];
  variableValues: Record<string, string>;
  setVariableValues: (variable: string, value: string) => void;
}

const VariableDisplay: React.FC<VariableDisplayProps> = ({
  variables,
  variableValues,
  setVariableValues
}) => {
  return (
    <div className="mb-4 p-4 bg-white rounded shadow w-full">
      <h2 className="text-lg font-bold mb-2">変数</h2>
      <div className="grid grid-cols-2 gap-4">
        {variables.map(variable => (
          <div key={variable}>
            <label className="block text-gray-700">{variable}</label>
            <input
              className="border rounded px-2 py-1 w-full"
              type="text"
              value={variableValues[variable] || ''}
              onChange={e => setVariableValues(variable, e.target.value)}
            />
          </div>
        ))}
      </div>
    </div>
  );
};

export default VariableDisplay;