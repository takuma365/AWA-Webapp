// src/components/TabModal.tsx
import React, { useState } from 'react';

interface TabModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (name: string, id: string) => void;
}

const TabModal: React.FC<TabModalProps> = ({ isOpen, onClose, onSubmit }) => {
  const [tabName, setTabName] = useState('');
  const [tabId, setTabId] = useState('');

  const handleSubmit = () => {
    if (tabName.trim() && tabId.trim()) {
      onSubmit(tabName.trim(), tabId.trim());
      setTabName('');
      setTabId('');
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 flex justify-center items-center bg-gray-500 bg-opacity-50">
      <div className="bg-white p-6 rounded-lg w-80">
        <h2 className="text-xl mb-4">新しい案件名を入力</h2>
        <input
          type="text"
          value={tabName}
          onChange={(e) => setTabName(e.target.value)}
          className="border p-2 mb-2 w-full"
          placeholder="表示名（例：アイプ）"
        />
        <input
          type="text"
          value={tabId}
          onChange={(e) => setTabId(e.target.value)}
          className="border p-2 mb-4 w-full"
          placeholder="URL用ID（例：ipe）半角英数字のみ"
        />
        <div className="flex justify-between">
          <button onClick={onClose} className="px-4 py-2 bg-gray-300 rounded">キャンセル</button>
          <button onClick={handleSubmit} className="px-4 py-2 bg-blue-500 text-white rounded">追加</button>
        </div>
      </div>
    </div>
  );
};

export default TabModal;
