// src/pages/SettingsScreen.tsx
import React, { useRef, useState } from 'react';

interface SectionData {
  [title: string]: {
    tag: string;
    wordStyle: string;
    size: string;
    bold: string;
    color: string;
    extraStyle: string;
    id: string;
    className: string;
    prefix: string;
    suffix: string;
  };
}

const SettingsScreen = () => {
  const [tabs, setTabs] = useState<string[]>(['チアジョブ', 'ナースステップ', 'ソニー', 'zoff']);
  const [activeTab, setActiveTab] = useState('チアジョブ');
  const [sections, setSections] = useState<string[]>(['大見出し', '中見出し', '太字']);
  const [openSections, setOpenSections] = useState<{ [key: string]: boolean }>({
    大見出し: true,
    中見出し: false,
    太字: false,
  });
  const [formData, setFormData] = useState<SectionData>({});

  const scrollRef = useRef<HTMLDivElement>(null);

  const scrollLeft = () => {
    if (scrollRef.current) scrollRef.current.scrollBy({ left: -100, behavior: 'smooth' });
  };

  const scrollRight = () => {
    if (scrollRef.current) scrollRef.current.scrollBy({ left: 100, behavior: 'smooth' });
  };

  const toggleSection = (title: string) => {
    setOpenSections((prev) => ({ ...prev, [title]: !prev[title] }));
  };

  const addSection = () => {
    const title = prompt('新しいセクション名を入力してください');
    if (title && !sections.includes(title)) {
      setSections((prev) => [...prev, title]);
      setOpenSections((prev) => ({ ...prev, [title]: true }));
    }
  };

  const removeSection = () => {
    const title = prompt('削除するセクション名を入力してください');
    if (title && sections.includes(title)) {
      setSections((prev) => prev.filter((t) => t !== title));
      setOpenSections((prev) => {
        const updated = { ...prev };
        delete updated[title];
        return updated;
      });
      setFormData((prev) => {
        const updated = { ...prev };
        delete updated[title];
        return updated;
      });
    }
  };

  const addTab = () => {
    const name = prompt('新しいタブ名を入力してください');
    if (name && !tabs.includes(name)) {
      setTabs((prev) => [...prev, name]);
      setActiveTab(name);
    }
  };

  const handleChange = (title: string, key: keyof SectionData[string], value: string) => {
    setFormData((prev) => ({
      ...prev,
      [title]: {
        ...prev[title],
        [key]: value,
      },
    }));
  };

  const handleSave = () => {
    console.log('保存されたデータ:', formData);
    alert('設定を保存しました（仮）');
  };

  return (
    <div className="p-4 max-w-4xl mx-auto">
      {/* Scroll Buttons and Tab Bar */}
      <div className="relative flex items-center border-t border-l border-r border-black bg-gray-300">
        <button onClick={scrollLeft} className="px-2">◀</button>
        <div ref={scrollRef} className="flex overflow-x-hidden whitespace-nowrap flex-1">
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 border-r border-black text-sm ${
                activeTab === tab ? 'bg-gray-100' : 'bg-gray-300'
              }`}
            >
              {tab}
            </button>
          ))}
          <button
            className="px-4 py-2 text-lg font-bold border-l border-black bg-white "
            onClick={addTab}
          >
            ＋
          </button>
        </div>
        <button onClick={scrollRight} className="px-2">▶</button>
      </div>

      {/* Sections */}
      {sections.map((title) => (
        <div key={title} className="border border-black border-t-0">
          <button
            className="w-full flex justify-between items-center px-4 py-2 bg-gray-100"
            onClick={() => toggleSection(title)}
          >
            <span>{title}</span>
            <span>{openSections[title] ? '▲' : '▼'}</span>
          </button>
          {openSections[title] && (
            <div className="p-4 bg-gray-50">
              <form className="grid grid-cols-2 gap-4 text-sm">
                <label className="col-span-2">
                  タグ：
                  <select className="w-full border p-1 mt-1" value={formData[title]?.tag || ''} onChange={(e) => handleChange(title, 'tag', e.target.value)}>
                    <option value="">選択してください</option>
                    <option>&lt;h1&gt;&lt;/h1&gt;</option>
                    <option>&lt;h2&gt;&lt;/h2&gt;</option>
                    <option>&lt;h3&gt;&lt;/h3&gt;</option>
                    <option>&lt;h4&gt;&lt;/h4&gt;</option>
                    <option>&lt;h5&gt;&lt;/h5&gt;</option>
                  </select>
                </label>
                <label>
                  Wordにおけるスタイル：
                  <select className="w-full border p-1 mt-1" value={formData[title]?.wordStyle || ''} onChange={(e) => handleChange(title, 'wordStyle', e.target.value)}>
                    <option value="">選択してください</option>
                    <option>見出し１</option>
                    <option>見出し２</option>
                    <option>見出し３</option>
                    <option>見出し４</option>
                    <option>見出し５</option>
                  </select>
                </label>
                <label>
                  サイズ：
                  <input type="text" className="w-full border p-1 mt-1" placeholder="なし" value={formData[title]?.size || ''} onChange={(e) => handleChange(title, 'size', e.target.value)} />
                </label>
                <label>
                  太字：
                  <select className="w-full border p-1 mt-1" value={formData[title]?.bold || ''} onChange={(e) => handleChange(title, 'bold', e.target.value)}>
                    <option>あり</option>
                    <option>なし</option>
                  </select>
                </label>
                <label>
                  色：
                  <input type="text" className="w-full border p-1 mt-1" placeholder="なし" value={formData[title]?.color || ''} onChange={(e) => handleChange(title, 'color', e.target.value)} />
                </label>
                <label className="col-span-2">
                  その他のstyle：
                  <input type="text" className="w-full border p-1 mt-1" placeholder="なし" value={formData[title]?.extraStyle || ''} onChange={(e) => handleChange(title, 'extraStyle', e.target.value)} />
                </label>
                <label className="col-span-2">
                  id名：
                  <input type="text" className="w-full border p-1 mt-1" value={formData[title]?.id || ''} onChange={(e) => handleChange(title, 'id', e.target.value)} />
                </label>
                <label className="col-span-2">
                  クラス名：
                  <input type="text" className="w-full border p-1 mt-1" placeholder="なし" value={formData[title]?.className || ''} onChange={(e) => handleChange(title, 'className', e.target.value)} />
                </label>
                <label className="col-span-2">
                  前にある文字列：
                  <input type="text" className="w-full border p-1 mt-1" placeholder="なし" value={formData[title]?.prefix || ''} onChange={(e) => handleChange(title, 'prefix', e.target.value)} />
                </label>
                <label className="col-span-2">
                  後ろにある文字列：
                  <input type="text" className="w-full border p-1 mt-1" placeholder="なし" value={formData[title]?.suffix || ''} onChange={(e) => handleChange(title, 'suffix', e.target.value)} />
                </label>
              </form>
            </div>
          )}
        </div>
      ))}

      {/* Add/Delete Section Buttons */}
      <div className="mt-4 flex justify-between">
        <button
          onClick={removeSection}
          className="px-4 py-2 bg-red-100 text-red-700 hover:bg-red-200 rounded"
        >
          － セクションを削除
        </button>
        <button
          onClick={addSection}
          className="px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded"
        >
          ＋ セクションを追加
        </button>
      </div>

      {/* Footer Buttons */}
      <div className="flex justify-between mt-6">
        <button className="text-red-500 border border-red-500 px-4 py-2 rounded" onClick={removeSection}>削除する</button>
        <button className="border px-4 py-2 rounded" onClick={handleSave}>保存する</button>
      </div>
    </div>
  );
};

export default SettingsScreen;