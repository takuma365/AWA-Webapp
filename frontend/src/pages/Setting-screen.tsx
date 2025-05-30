import { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import TabModal from '../components/TabModal';
import SectionModal from '../components/SectionModal';
import ConfirmModal from '../components/ConfirmModal';

type FieldErrors = {
  tag?: string;
  wordStyle?: string;
};
type SectionFields = {
  tag: string;
  wordStyle: string;
  bold: string;
  extraStyle: string;
  prefix: string;
  suffix: string;
};
const DEFAULT_SECTIONS = ['大見出し', '中見出し'];

const selfClosingTags = new Set([
  'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
  'link', 'meta', 'source', 'track', 'wbr'
]);

function validateTagStructure(input: string): string {
  const tagRegex = /<\/?([a-zA-Z][a-zA-Z0-9]*)\b[^>]*\/?\>/g;
  const stack: string[] = [];

  let match: RegExpExecArray | null;
  while ((match = tagRegex.exec(input)) !== null) {
    const fullTag = match[0];
    const tagName = match[1].toLowerCase();

    const isClosing = fullTag.startsWith('</');
    const isSelfClosing = fullTag.endsWith('/>') || selfClosingTags.has(tagName);

    if (isSelfClosing) continue;

    if (isClosing) {
      const last = stack.pop();
      if (last !== tagName) {
        return `<${last}> を開いているのに、</${tagName}> で閉じようとしています。同じタグで閉じてください。`;
      }
    } else {
      stack.push(tagName);
    }
  }

  if (stack.length > 0) {
    return `<${stack[stack.length - 1]}> タグを開いたまま閉じていません。閉じタグ </${stack[stack.length - 1]}> を追加してください。`;
  }

  return '';
}

const SettingsScreen = () => {
  const { tabId } = useParams();
  const navigate = useNavigate();

  const [tabs, setTabs] = useState<{ name: string; id: string }[]>([]);
  const [activeTabId, setActiveTabId] = useState<string>('');
  const [sectionMap, setSectionMap] = useState<Record<string, string[]>>({});
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({});
  const [errors, setErrors] = useState<Record<string, Record<string, FieldErrors>>>({});
  const [formData, setFormData] = useState<Record<string, Record<string, SectionFields>>>({});  const [isTabModalOpen, setIsTabModalOpen] = useState(false);
  const [isSectionModalOpen, setIsSectionModalOpen] = useState(false);
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState(false);
  const [confirmAction, setConfirmAction] = useState<'save' | 'delete-tab' | 'delete-tab-data'>();
  const [actionType, setActionType] = useState<'add' | 'remove'>('add');
  const [targetTabId, setTargetTabId] = useState<string>('');

  const scrollRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    if (tabs.length === 0) {
      const initialTabs = [
        { name: 'チアジョブ', id: 'cheerjob' },
        { name: 'ナースステップ', id: 'nursestep' },
        { name: 'ソニー', id: 'sony' },
        { name: 'zoff', id: 'zoff' },
      ];
      setTabs(initialTabs);
      const initialSections = Object.fromEntries(initialTabs.map((tab) => [tab.id, DEFAULT_SECTIONS]));
      setSectionMap(initialSections);
      const openState: Record<string, boolean> = {};
      DEFAULT_SECTIONS.forEach((section, i) => {
        openState[section] = i === 0;
      });
      setOpenSections(openState);

      const initialForm: Record<string, Record<string, SectionFields>> = {};
      for (const tab of initialTabs) {
        initialForm[tab.id] = {};
        for (const section of DEFAULT_SECTIONS) {
          initialForm[tab.id][section] = {
            tag: '',
            wordStyle: '',
            bold: '',
            extraStyle: '',
            prefix: '',
            suffix: '',
          };
        }
      }
      setFormData(initialForm);
      const initialId = tabId && initialTabs.some(t => t.id === tabId)
        ? tabId
        : initialTabs[0].id;
      setActiveTabId(initialId);
      // URL と同期（param がない場合だけリダイレクト）
      if (!tabId || !initialTabs.some(t => t.id === tabId)) {
        navigate(`/settings/${initialId}`, { replace: true });
      }
    } else {
      const matched = tabs.find((tab) => tab.id === tabId);
      if (matched) setActiveTabId(matched.id);
    }
  }, [tabId, tabs, navigate]);
  useEffect(() => {
    setErrors(prev => ({
      ...prev,
      [activeTabId]: {}
    }));
  }, [activeTabId]);
  const handleTabSubmit = (name: string, id: string) => {
    if (tabs.some((tab) => tab.id === id)) return;
    const newTab = { name, id };
    setTabs((prev) => [...prev, newTab]);
    setSectionMap((prev) => ({ ...prev, [id]: DEFAULT_SECTIONS }));

    const newFormData: Record<string, SectionFields> = {};
    for (const section of DEFAULT_SECTIONS) {
      newFormData[section] = {
        tag: '',
        wordStyle: '',
        bold: '',
        extraStyle: '',
        prefix: '',
        suffix: '',
      };
    }
    setFormData((prev) => ({ ...prev, [id]: newFormData }));
    navigate(`/settings/${id}`);
  };

  const handleTabDelete = (id: string) => {
    setTabs((prev) => prev.filter((tab) => tab.id !== id));
    setSectionMap((prev) => {
      const updated = { ...prev };
      delete updated[id];
      return updated;
    });
    setFormData((prev) => {
      const updated = { ...prev };
      delete updated[id];
      return updated;
    });
    setErrors((prev) => {
      const updated = { ...prev };
      delete updated[id];
      return updated;
    });
  
    // 削除後の遷移先を決定（残っていれば最初のタブへ遷移）
    const remaining = tabs.filter((tab) => tab.id !== id);
    if (remaining.length > 0) {
      const nextTab = remaining[0].id;
      setActiveTabId(nextTab);
      navigate(`/settings/${nextTab}`);
    } else {
      setActiveTabId('');
      navigate(`/settings`);
    }
  };
  

  const handleSectionSubmit = (name: string, action: string) => {
    if (!name || !activeTabId) return;
    setSectionMap((prev) => {
      const current = prev[activeTabId] || [];
      const updated = action === 'add'
        ? [...current, name]
        : current.filter((section) => section !== name);
      return { ...prev, [activeTabId]: updated };
    });
    setOpenSections((prev) => {
      const updated = { ...prev };
      if (action === 'add') updated[name] = true;
      else delete updated[name];
      return updated;
    });
    setIsSectionModalOpen(false);
  };


  const handleConfirm = () => {
    // ① 「削除」のケース
    if (confirmAction === 'delete-tab') {
      handleTabDelete(targetTabId);
      alert(`「${tabs.find(tab => tab.id === targetTabId)?.name}」を削除しました`);
      setIsConfirmModalOpen(false);
      return;
    }
  
    // ② （もしあれば）「タブとそのデータを丸ごと消す」ケース
    if (confirmAction === 'delete-tab-data') {
      handleTabDelete(targetTabId);
      // たとえば formData や errors をまるごと消したいならここでセットし直す
      alert(`「${tabs.find(tab => tab.id === targetTabId)?.name}」とそのデータを削除しました`);
      setIsConfirmModalOpen(false);
      return;
    }
  
    // ③ 「保存」のケース
    if (confirmAction === 'save') {
      // 保存前のバリデーションチェック
      const hasError = (sectionMap[activeTabId] || []).some(section => {
        if (!formData[activeTabId][section].wordStyle) return true;
        if (errors[activeTabId]?.[section]?.tag) return true;
        return false;
      });
      if (hasError) {
        alert('エラーがあります。修正してください。');
        return;
      }
  
      // エラーなければ保存処理
      alert(`「${tabs.find(tab => tab.id === activeTabId)?.name}」の設定を保存しました`);
  
      // エラークリア＆モーダル閉じる
      setErrors(prev => ({ ...prev, [activeTabId]: {} }));
      setIsConfirmModalOpen(false);
      return;
    }
  };
  const scrollLeft = () => scrollRef.current?.scrollBy({ left: -100, behavior: 'smooth' });
  const scrollRight = () => scrollRef.current?.scrollBy({ left: 100, behavior: 'smooth' });

  const toggleSection = (title: string) => {
    setOpenSections((prev) => ({ ...prev, [title]: !prev[title] }));
  };

  const handleChange = (
    section: string,
    key: keyof SectionFields,
    value: string
  ) => {
    let error = '';
    if (key === 'wordStyle') {
      error = value ? '' : '未設定です';
    }
    if (key === 'tag') {
      const hasId = value.includes('id="');
      const idMatch = value.match(/id="([^"]*)"/);
      // id属性はあるけど、値に「1」が含まれていない場合はエラー
      const isInvalidId = hasId && (!idMatch || !idMatch[1].includes('1'));
  
      // タグのネスト構造チェック
      const tagStructureError = validateTagStructure(value);
  
      // id属性エラーを優先
      error = isInvalidId
        ? 'id属性には1を含めてください。'
        : tagStructureError;
    }

    setFormData(prev => ({
      ...prev,
      [activeTabId]: {
        ...prev[activeTabId],
        [section]: {
          ...prev[activeTabId][section],
          [key]: value,
        },
      },
    }));
    setErrors(prev => ({
      ...prev,
      [activeTabId]: {
        ...prev[activeTabId],
        [section]: {
          ...(prev[activeTabId]?.[section] || {}),
          [key]: error,
        },
      },
    }));
  };

  const handleSaveClick = () => {
    const newErrors: Record<string, FieldErrors> = {};
    (sectionMap[activeTabId] || []).forEach(section => {
      if (!formData[activeTabId][section].wordStyle) {
        newErrors[section] = {
          ...(errors[activeTabId]?.[section] || {}),
          wordStyle: '未設定です',
        };
      }
    });
  
    // エラーがあれば state にセットして終了
    if (Object.keys(newErrors).length > 0) {
      setErrors(prev => ({
        ...prev,
        [activeTabId]: {
          ...prev[activeTabId],
          ...newErrors,
        },
      }));
      return;
    }
    // エラーなしなら確認モーダルを開く
    setConfirmAction('save');
    setIsConfirmModalOpen(true);
  };
  useEffect(() => {
  }, [isConfirmModalOpen]);
  const targetTabName = tabs.find(tab => tab.id === targetTabId)?.name;

  return (
    <div className="p-4 max-w-4xl mx-auto">
      <TabModal isOpen={isTabModalOpen} onClose={() => setIsTabModalOpen(false)} onSubmit={handleTabSubmit} />
      <SectionModal isOpen={isSectionModalOpen} onClose={() => setIsSectionModalOpen(false)} onSubmit={handleSectionSubmit} actionType={actionType} />
      <ConfirmModal
        isOpen={isConfirmModalOpen}
        onClose={() => setIsConfirmModalOpen(false)}
        onConfirm={handleConfirm}
        message={
          confirmAction === 'delete-tab'
            ? `「${targetTabName}」のタブを削除してもよろしいですか？`
            : confirmAction === 'delete-tab-data'
            ? `「${targetTabName}」とそのすべてのデータを削除してもよろしいですか？`
            : `「${tabs.find(tab => tab.id === activeTabId)?.name}」の設定を保存してもよろしいですか？`
        }
      />
      <div className="relative flex items-center border-t border-l border-r border-black bg-gray-300">
        <button onClick={scrollLeft} className="px-2">◀</button>
        <div ref={scrollRef} className="flex overflow-x-auto whitespace-nowrap flex-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => navigate(`/settings/${tab.id}`)}
              className={`px-4 py-2 border-r border-black text-sm ${activeTabId === tab.id ? 'bg-gray-100' : 'bg-gray-300'}`}
            >
              {tab.name}
            </button>
          ))}
          <button className="px-4 py-2 text-lg font-bold border-l border-black bg-white" onClick={() => setIsTabModalOpen(true)}>＋</button>
        </div>
        <button onClick={scrollRight} className="px-2">▶</button>
      </div>

      {sectionMap[activeTabId]?.map((title) => (
        <div key={title} className="border border-black border-t-0">
          <button className="w-full flex justify-between items-center px-4 py-2 bg-gray-100" onClick={() => toggleSection(title)}>
            <span>{title}</span>
            <span>{openSections[title] ? '▲' : '▼'}</span>
          </button>
          {openSections[title] && (
            <div className="p-4 bg-gray-50">
              <form className="grid grid-cols-2 gap-4 text-sm">
                <div className="col-span-2">
                  <label className="block border-b-2 border-gray-500 mb-2 pb-4">
                    タグ：
                    <input
                      className="w-full border p-1 mt-1 mb-2"
                      type="text"
                      value={formData[activeTabId]?.[title]?.tag || ''}
                      onChange={(e) => handleChange(title, 'tag', e.target.value)}
                      placeholder="例: <h1></h1>など"
                    />
                    {errors[activeTabId]?.[title]?.tag && (
                      <p className="text-red-500 text-xs mb-2"> {errors[activeTabId][title].tag}</p>
                    )}
                  </label>
                </div>

                <div className="col-span-1">
                  <label className="block">
                    Wordにおけるスタイル：
                    <select
                      className="w-full border p-1 mt-1"
                      value={formData[activeTabId]?.[title]?.wordStyle || ''}
                      onChange={(e) => handleChange(title, 'wordStyle', e.target.value)}
                    >
                      <option value="">選択してください</option>
                      <option>見出し１</option>
                      <option>見出し２</option>
                      <option>見出し３</option>
                      <option>見出し４</option>
                      <option>標準</option>
                      <option>Wordに記載なし</option>
                    </select>
                  </label>
                  {errors[activeTabId]?.[title]?.wordStyle && (
                    <p className="text-red-500 text-xs mt-1">
                      {errors[activeTabId][title].wordStyle}
                    </p>
                  )}
                  <div className="flex gap-4 mt-5">
                    <label className="inline-flex items-center">
                      <input
                        type="checkbox"
                        className="mr-1"
                        checked={formData[activeTabId]?.[title]?.bold === 'true'}
                        onChange={(e) => handleChange(title, 'bold', e.target.checked ? 'true' : '')}
                      />
                      太字
                    </label>
                    <label className="inline-flex items-center">
                      <input
                        type="checkbox"
                        className="mr-1"
                        checked={formData[activeTabId]?.[title]?.extraStyle === 'marker'}
                        onChange={(e) => handleChange(title, 'extraStyle', e.target.checked ? 'marker' : '')}
                      />
                      マーカー
                    </label>
                  </div>
                </div>

                <div className="col-span-2 mt-5">
                  <div className="w-full h-[1px] bg-gray-500" />
                </div>

                <label className="col-span-2">
                  前にある文字列：
                  <input
                    type="text"
                    className="w-full border p-1 mt-1"
                    placeholder="なし ※改行は￥n"
                    value={formData[activeTabId]?.[title]?.prefix || ''}
                    onChange={(e) => handleChange(title, 'prefix', e.target.value)}
                  />
                </label>
                <label className="col-span-2">
                  後ろにある文字列：
                  <input
                    type="text"
                    className="w-full border p-1 mt-1"
                    placeholder="なし ※改行は￥n"
                    value={formData[activeTabId]?.[title]?.suffix || ''}
                    onChange={(e) => handleChange(title, 'suffix', e.target.value)}
                  />
                </label>
              </form>
            </div>
          )}
        </div>
      ))}

      <div className="mt-4 flex justify-between">
        <button onClick={() => { setActionType('remove'); setIsSectionModalOpen(true); }} className="px-4 py-2 bg-red-100 text-red-700 hover:bg-red-200 rounded">－ セクションを削除</button>
        <button onClick={() => { setActionType('add'); setIsSectionModalOpen(true); }} className="px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded">＋ セクションを追加</button>
      </div>

      <div className="flex justify-between mt-6">
  <button
    className="text-red-500 border border-red-500 px-4 py-2 rounded"
    onClick={() => {
      setTargetTabId(activeTabId);
      setConfirmAction('delete-tab');
      setIsConfirmModalOpen(true);
    }}
  >
    削除する
  </button>
  <button
    className="border px-4 py-2 rounded"
    onClick={handleSaveClick}
  >
    保存する
  </button>
</div>
    </div>
  );
};


export default SettingsScreen;
