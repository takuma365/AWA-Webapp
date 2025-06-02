// src/components/TabModal.tsx
import React, { useState } from 'react';

interface TabModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (name: string, id: string) => void;
}

const TabModal: React.FC<TabModalProps> = ({ isOpen, onClose, onSubmit }) => {
  const [tabName, setTabName] = useState('');
  const [tabUrl, setTabUrl] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = () => {
    console.log('[DEBUG] TabModal handleSubmit called with:', { tabName, tabUrl });
    
    // 入力値の検証
    if (!tabName.trim()) {
      setError('サイト名を入力してください。');
      return;
    }
    if (!tabUrl.trim()) {
      setError('URLを入力してください。');
      return;
    }
    if (!/^[a-z0-9-]+$/.test(tabUrl)) {
      setError('URLは英小文字、数字、ハイフンのみ使用できます。');
      return;
    }

    console.log('[DEBUG] TabModal calling onSubmit with:', { tabName: tabName.trim(), tabUrl: tabUrl.trim().toLowerCase() });
    onSubmit(tabName.trim(), tabUrl.trim().toLowerCase());
    setTabName('');
    setTabUrl('');
    setError('');
    onClose();
  };

  const handleClose = () => {
    setTabName('');
    setTabUrl('');
    setError('');
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 flex justify-center items-center bg-gray-500 bg-opacity-50">
      <div className="bg-white p-6 rounded-lg w-96">
        <h2 className="text-xl mb-4">新しいサイトを追加</h2>
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            サイト名
          </label>
          <input
            type="text"
            value={tabName}
            onChange={(e) => setTabName(e.target.value)}
            className="border p-2 w-full rounded"
            placeholder="例：アイプ"
          />
        </div>
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            URL（英小文字、数字、ハイフンのみ）
          </label>
          <input
            type="text"
            value={tabUrl}
            onChange={(e) => setTabUrl(e.target.value.toLowerCase())}
            className="border p-2 w-full rounded"
            placeholder="例：ipe"
          />
        </div>
        {error && (
          <div className="text-red-500 text-sm mb-4">
            {error}
          </div>
        )}
        <div className="flex justify-between">
          <button 
            onClick={handleClose} 
            className="px-4 py-2 bg-gray-300 rounded hover:bg-gray-400"
          >
            キャンセル
          </button>
          <button 
            onClick={handleSubmit} 
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            追加
          </button>
        </div>
      </div>
    </div>
  );
};

export default TabModal;
