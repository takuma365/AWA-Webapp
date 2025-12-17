// src/components/SectionModal.tsx
import React, { useState } from 'react';

interface SectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (title: string, action: string) => void; // actionを追加（add/remove）
  actionType: 'add' | 'remove'; // 'add' または 'remove'
}

const SectionModal: React.FC<SectionModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  actionType
}) => {
  const [selectedSection, setSelectedSection] = useState<string>('');

  const sections = [
    '大見出し',
    '中見出し',
    '小見出し',
    '内部リンク',
    '外部リンク',
    '太字',
    'ハイライト',
    '赤字',
    '箱の枠',
    '箱内テキスト（中点）',
    '箱内リンクテキスト（中点）',
    '箱内テキスト（番号）',
    '表',
    'テキスト',
    'ショートコード',
    '文頭',
    '文末',
  ];

  const handleSubmit = () => {
    console.log('[DEBUG] SectionModal handleSubmit called with:', { selectedSection, actionType });
    
    if (actionType === 'remove') {
      const confirmDelete = window.confirm(`本当に「${selectedSection}」セクションを削除しますか？`);
      if (!confirmDelete) return; // ユーザーがキャンセルした場合、処理を終了
    }

    if (selectedSection) {
      console.log('[DEBUG] SectionModal calling onSubmit with:', { selectedSection, actionType });
      onSubmit(selectedSection, actionType);
      setSelectedSection('');
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 flex justify-center items-center bg-gray-500 bg-opacity-50">
      <div className="bg-white p-6 rounded-lg w-80">
        <h2 className="text-xl mb-4">
          {actionType === 'add' ? '新しいセクションを選択' : '削除するセクションを選択'}
        </h2>

        {/* セクションの選択 */}
        <select
          value={selectedSection}
          onChange={(e) => setSelectedSection(e.target.value)}
          className="border p-2 mb-4 w-full"
        >
          <option value="">選択してください</option>
          {sections.map((section) => (
            <option key={section} value={section}>
              {section}
            </option>
          ))}
        </select>

        <div className="flex justify-between">
          <button onClick={onClose} className="px-4 py-2 bg-gray-300 rounded">
            キャンセル
          </button>
          <button
            onClick={handleSubmit}
            className="px-4 py-2 bg-blue-500 text-white rounded"
          >
            {actionType === 'add' ? '追加' : '削除'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SectionModal;