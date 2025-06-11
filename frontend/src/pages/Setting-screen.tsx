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

// サイトデータの型定義を修正
interface Site {
  id: number;
  name: string;
  url: string; // 修正: code → url
  active: boolean;
  conversion_settings: {
    id: number;
    name: string;
    css_class_prefix: string;
    remove_empty_paragraphs: boolean;
    preserve_images: boolean;
    image_dir: string;
    active: boolean;
    rules: any[];
  }[];
}

// タブの型定義を更新
interface Tab {
  name: string;
  id: string;
}

const SettingsScreen = () => {
  const { tabId } = useParams();
  const navigate = useNavigate();

  const [tabs, setTabs] = useState<Tab[]>([]);
  const [activeTabId, setActiveTabId] = useState<string>('');
  const [sectionMap, setSectionMap] = useState<Record<string, string[]>>({});
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({});
  const [errors, setErrors] = useState<Record<string, Record<string, FieldErrors>>>({});
  const [formData, setFormData] = useState<Record<string, Record<string, SectionFields>>>({});
  const [isTabModalOpen, setIsTabModalOpen] = useState(false);
  const [isSectionModalOpen, setIsSectionModalOpen] = useState(false);
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState(false);
  const [confirmAction, setConfirmAction] = useState<'save' | 'delete-tab' | 'delete-tab-data'>();
  const [actionType, setActionType] = useState<'add' | 'remove'>('add');
  const [targetTabId, setTargetTabId] = useState<string>('');

  const scrollRef = useRef<HTMLDivElement>(null);
  
  // サイトデータを取得する関数
  const fetchSites = async () => {
    await new Promise(resolve => setTimeout(resolve, 3000)); 
    try {
      const response = await fetch('http://localhost:8000/api/sites/');
      if (!response.ok) {
        throw new Error('サイトデータの取得に失敗しました');
      }
      const sites: Site[] = await response.json();
      
      // アクティブなサイトのみをタブとして設定
      const activeSites = sites
        .filter(site => site.active)
        .map(site => ({
          name: site.name,
          id: site.url || site.name.toLowerCase() // 修正: code → url
        }))
        .filter(site => site.id); // id が存在するもののみ
      
      setTabs(activeSites);
    } catch (error) {
      console.error('Error fetching sites:', error);
      // エラー時のフォールバック
      setTabs([
        { name: 'チアジョブ', id: 'cheerjob' },
        { name: 'ナースステップ', id: 'nursestep' },
        { name: 'ソニー', id: 'sony' },
        { name: 'zoff', id: 'zoff' },
      ]);
    }
  };

  // コンポーネントマウント時にサイトデータを取得
  useEffect(() => {
    fetchSites();
  }, []);

  useEffect(() => {
    if (tabs.length > 0) {
      // 初期化時は空の配列を設定
      const initialSections = Object.fromEntries(tabs.map((tab) => [tab.id, []]));
      setSectionMap(initialSections);
      const openState: Record<string, boolean> = {};
      setOpenSections(openState);

      const initialForm: Record<string, Record<string, SectionFields>> = {};
      for (const tab of tabs) {
        initialForm[tab.id] = {};
      }
      setFormData(initialForm);
      
      const initialId = tabId && tabs.some(t => t.id === tabId)
        ? tabId
        : tabs.length > 0 ? tabs[0].id : '';
      
      if (initialId) {
        setActiveTabId(initialId);
        
        // URL と同期（param がない場合だけリダイレクト）
        if (!tabId || !tabs.some(t => t.id === tabId)) {
          navigate(`/settings/${initialId}`, { replace: true });
        }
      }
    }
  }, [tabId, tabs, navigate]);

  useEffect(() => {
    const fetchAndSetRules = async () => {
      if (!activeTabId) return;

      // サイト情報から変換設定IDを取得
      const siteRes = await fetch(`http://localhost:8000/api/sites/?url=${activeTabId}`);
      const sites = await siteRes.json();
      if (!sites.length) return;
      const site = sites[0];
      const settingId = site.conversion_settings[0]?.id;
      console.log('settingId:', settingId, 'site:', site.name);
      if (!settingId) return;

      // ルール一覧を取得
      const rulesRes = await fetch(`http://localhost:8000/api/rules/?setting_id=${settingId}`);
      const rules = await rulesRes.json();

      // sectionMapとformDataを初期化
      const sectionList = rules.map((rule: any) => rule.section);
      setSectionMap((prev) => ({ ...prev, [activeTabId]: sectionList }));

      const newFormData: Record<string, SectionFields> = {};
      rules.forEach((rule: any) => {
        newFormData[rule.section] = {
          tag: rule.tag,
          wordStyle: rule.word_style,
          bold: rule.bold ? 'true' : '',
          extraStyle: rule.marker ? 'marker' : '',
          prefix: rule.prefix_text || '',
          suffix: rule.suffix_text || '',
        };
      });
      setFormData((prev) => ({ ...prev, [activeTabId]: newFormData }));
    };

    fetchAndSetRules();
  }, [activeTabId]);

  useEffect(() => {
    setErrors(prev => ({
      ...prev,
      [activeTabId]: {}
    }));
  }, [activeTabId]);
  const handleTabSubmit = async (name: string, id: string) => {
    console.log('[DEBUG] handleTabSubmit called with:', { name, id });
    
    // ローカルでの重複チェック
    if (tabs.some((tab) => tab.id === id)) {
      alert('同じURLのサイトが既に存在します。');
      return;
    }
    
    try {
      // バックエンドでの重複チェック
      const checkResponse = await fetch(`http://localhost:8000/api/sites/?url=${encodeURIComponent(id)}`);
      if (checkResponse.ok) {
        const existingSites = await checkResponse.json();
        if (existingSites.length > 0) {
          alert('同じURLのサイトが既にデータベースに存在します。');
          return;
        }
      }

      // バックエンドに新しいサイトを作成
      const response = await fetch('http://localhost:8000/api/sites/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: name,
          url: id,
          active: true
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error('サイト作成エラー:', errorData);
        
        // より詳細なエラーメッセージ
        if (response.status === 400) {
          alert('入力データが正しくありません。サイト名とURLを確認してください。');
        } else {
          alert('サイトの作成に失敗しました。');
        }
        return;
      }

      const newSite = await response.json();
      
      // 成功したらローカルステートを更新
      const newTab = { name, id };
      setTabs((prev) => [...prev, newTab]);
      setSectionMap((prev) => ({ ...prev, [id]: [] }));

      const newFormData: Record<string, SectionFields> = {};
      setFormData((prev) => ({ ...prev, [id]: newFormData }));
      navigate(`/settings/${id}`);
      
      alert(`サイト「${name}」を作成しました。`);
      
    } catch (error) {
      console.error('サイト作成エラー:', error);
      alert('サイトの作成中にエラーが発生しました。ネットワーク接続を確認してください。');
    }
  };

  const handleTabDelete = async (id: string) => {
    try {
      // まずバックエンドから削除対象のサイトを検索
      const sitesResponse = await fetch('http://localhost:8000/api/sites/');
      if (sitesResponse.ok) {
        const sites = await sitesResponse.json();
        const targetSite = sites.find((site: any) => site.url === id);
        
        if (targetSite) {
          // バックエンドからサイトを削除（論理削除: active = false）
          const deleteResponse = await fetch(`http://localhost:8000/api/sites/${targetSite.id}/`, {
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              active: false
            })
          });

          if (!deleteResponse.ok) {
            console.error('サイト削除エラー');
            alert('サイトの削除に失敗しました。');
            return;
          }
        }
      }

      // バックエンド処理が成功したらローカルステートを更新
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
      
    } catch (error) {
      console.error('サイト削除エラー:', error);
      alert('サイトの削除中にエラーが発生しました。');
    }
  };
  

  const handleSectionSubmit = (name: string, action: string) => {
    console.log('[DEBUG] handleSectionSubmit called with:', { name, action });
    
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
      if (section !== '文頭' && section !== '文末') {
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

  const handleSaveClick = async () => {
    // バリデーションチェック（文頭・文末以外のセクション）
    const newErrors: Record<string, FieldErrors> = {};
    (sectionMap[activeTabId] || []).forEach(section => {
      if (section !== '文頭' && section !== '文末') {
        const data = formData[activeTabId][section];
        if (!data.wordStyle) {
          newErrors[section] = {
            ...(errors[activeTabId]?.[section] || {}),
            wordStyle: '未設定です',
          };
        }
        if (data.tag) {
          const hasId = data.tag.includes('id="');
          const idMatch = data.tag.match(/id="([^"]*)"/);
          const isInvalidId = hasId && (!idMatch || !idMatch[1].includes('1'));
          const tagStructureError = validateTagStructure(data.tag);
          
          if (isInvalidId || tagStructureError) {
            newErrors[section] = {
              ...(newErrors[section] || {}),
              tag: isInvalidId ? 'id属性には1を含めてください。' : tagStructureError,
            };
          }
        }
      }
    });

    if (Object.keys(newErrors).length > 0) {
      setErrors(prev => ({
        ...prev,
        [activeTabId]: {
          ...prev[activeTabId],
          ...newErrors,
        },
      }));
      alert('入力内容にエラーがあります。修正してください。');
      return;
    }

    try {
      console.log('保存開始:', activeTabId);
      
      // サイト→変換設定ID取得
      const siteRes = await fetch(`http://localhost:8000/api/sites/?url=${activeTabId}`);
      console.log('サイトAPIレスポンス:', { status: siteRes.status });
      
      const sites = await siteRes.json();
      console.log('取得したサイト:', sites);
      
      if (!sites.length) {
        console.error('サイトが見つかりません:', activeTabId);
        throw new Error('サイトが見つかりません');
      }
      
      const site = sites[0];
      const settingId = site.conversion_settings[0]?.id;
      console.log('変換設定ID:', settingId);
      
      if (!settingId) {
        console.error('変換設定が見つかりません:', site);
        throw new Error('変換設定が見つかりません');
      }

      // 既存ルール一覧を取得
      const rulesRes = await fetch(`http://localhost:8000/api/rules/?setting_id=${settingId}`);
      const rules = await rulesRes.json();
      console.log('既存ルール:', rules);

      // 各セクションごとにAPIリクエスト
      for (const section of sectionMap[activeTabId] || []) {
        console.log(`セクション「${section}」の処理開始`);
        
        const data = formData[activeTabId][section];
        const existing = rules.find((r: any) => r.section === section);
        console.log('既存ルール:', existing);

        // ペイロードの基本構造を作成
        const basePayload = {
          setting: settingId,
          section,
          tag: data.tag || existing?.tag || '',
          word_style: data.wordStyle || existing?.word_style || '',
          bold: data.bold === 'true',
          marker: data.extraStyle === 'marker',
          prefix_text: data.prefix || existing?.prefix_text || '',
          suffix_text: data.suffix || existing?.suffix_text || '',
          active: true,
        };

        let payload = { ...basePayload };

        // 文頭・文末の場合のみ特別な処理を適用
        if (section === '文頭' || section === '文末') {
          try {
            // タグの内容を処理（改行を保持）
            let tagContent = payload.tag;
            
            // 文頭・文末の場合はHTMLエスケープ処理を行わない
            payload.tag = tagContent;
            
            // word_styleが空の場合はデフォルト値を設定
            if (!payload.word_style) {
              payload.word_style = 'Wordに記載なし';
            }

            console.log('文頭・文末の処理後のペイロード:', payload);
          } catch (error) {
            console.error('ペイロード処理エラー:', error);
            throw new Error(`セクション「${section}」のデータ処理に失敗しました`);
          }
        } else {
          // 文頭・文末以外の場合は元のタグをそのまま使用
          console.log('通常セクションのペイロード:', payload);
        }

        try {
          if (existing) {
            console.log(`セクション「${section}」を更新`);
            const response = await fetch(`http://localhost:8000/api/rules/${existing.id}/`, {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(payload),
            });
            
            if (!response.ok) {
              const errorData = await response.json();
              console.error('更新エラー詳細:', errorData);
              throw new Error(`セクション「${section}」の更新に失敗しました: ${JSON.stringify(errorData)}`);
            }
            
            console.log(`セクション「${section}」の更新完了`);
          } else {
            console.log(`セクション「${section}」を新規作成`);
            const response = await fetch('http://localhost:8000/api/rules/', {
              method: 'POST',
              headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
              },
              body: JSON.stringify(payload),
            });
            
            if (!response.ok) {
              let errorMessage = `ステータスコード: ${response.status}`;
              try {
                // まずJSONとしてパースを試みる
                const errorData = await response.json();
                if (errorData.tag) {
                  errorMessage = `タグエラー: ${errorData.tag.join(', ')}`;
                } else {
                  errorMessage = JSON.stringify(errorData);
                }
              } catch (jsonError) {
                // JSONパースに失敗した場合はテキストとして読み取る
                try {
                  const textError = await response.text();
                  errorMessage = textError;
                } catch (textError) {
                  errorMessage = '不明なエラーが発生しました';
                }
              }
              console.error('APIエラー:', errorMessage);
              throw new Error(`セクション「${section}」の作成に失敗しました: ${errorMessage}`);
            }
            
            console.log(`セクション「${section}」の作成完了`);
          }
        } catch (error) {
          console.error(`セクション「${section}」の保存エラー:`, error);
          throw error;
        }
      }

      console.log('全セクションの保存完了');
      alert('保存しました');
    } catch (error: any) {
      console.error('保存エラー:', error);
      alert(error.message || '保存中にエラーが発生しました');
    }
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
          <button className="px-4 py-2 text-lg font-bold border-l border-black bg-white" onClick={() => {
            console.log('[DEBUG] Tab add button clicked');
            setIsTabModalOpen(true);
          }}>＋</button>
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
                    <textarea
                      className="w-full border p-1 mt-1 mb-2 font-mono"
                      rows={10}
                      value={formData[activeTabId]?.[title]?.tag || ''}
                      onChange={(e) => handleChange(title, 'tag', e.target.value)}
                      placeholder="例: <h1></h1>など"
                      style={{ whiteSpace: 'pre', overflowWrap: 'normal', overflowX: 'auto' }}
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
        <button onClick={() => { 
          console.log('[DEBUG] Section remove button clicked'); 
          setActionType('remove'); 
          setIsSectionModalOpen(true); 
        }} className="px-4 py-2 bg-red-100 text-red-700 hover:bg-red-200 rounded">－ セクションを削除</button>
        <button onClick={() => { 
          console.log('[DEBUG] Section add button clicked'); 
          setActionType('add'); 
          setIsSectionModalOpen(true); 
        }} className="px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded">＋ セクションを追加</button>
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
