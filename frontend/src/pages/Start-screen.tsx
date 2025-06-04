import { useState, useEffect } from 'react'; 
import { useNavigate } from 'react-router-dom';

// サイトの型定義を追加
interface Site {
  name: string;
  url: string;
  active: boolean;
}

const StartScreen = () => {
  const navigate = useNavigate();
  const [selectedSite, setSelectedSite] = useState('');
  const [error, setError] = useState('');
  const [sites, setSites] = useState<Site[]>([]);

  const validateSelection = () => {
    if (!selectedSite || selectedSite === 'サイトを選択する') {
      setError('サイトを選択してください');
      return false;
    }
    setError('');
    return true;
  };

  // handleGenerateClic名前変える
  const handleGenerateClick = () => {
    if (validateSelection()) {
    }
  };

  const handleSettingsClick = () => {
    if (validateSelection()) {
      navigate(`/settings/${selectedSite}`);
    }
  };
  useEffect(() => {
    const fetchSites = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/sites/');
        if (!response.ok) {
          throw new Error('サイトデータの取得に失敗しました');
        }
        const data = await response.json();
        // アクティブなサイトのみをフィルタリング
        const activeSites = data.filter((site: Site) => site.active);
        setSites(activeSites);
      } catch (error) {
        console.error('Error fetching sites:', error);
        setError('サイト情報の取得に失敗しました');
      }
    };

    fetchSites();
  }, []);

  return (
    <div className="flex items-center justify-center p-20">
      <div className="bg-white w-full max-w-3xl p-20 rounded-lg flex flex-col items-center gap-12">
     <div className="w-full max-w-sm pb-4">
          <select
            value={selectedSite}
            onChange={(e) => {
              setSelectedSite(e.target.value);
              setError('');
            }}
            className="w-full p-2 text-base border border-gray-300 rounded"
          >
            <option value="">サイトを選択する</option>
            {/* サイト一覧を動的に生成 */}
            {sites.map((site) => (
              <option key={site.url} value={site.url}>
                {site.name}
              </option>
            ))}
          </select>
          {error && (
            <p className="mt-2 text-sm text-red-600">{error}</p>
          )}
        </div>

        <div className="flex flex-col items-center gap-8 w-full max-w-xs pt-8">
          <button
            className="w-full py-2 rounded-full bg-gray-300 hover:bg-gray-400 transition"
            onClick={handleGenerateClick}
          >
            記事を生成
          </button>
          <button
            className="w-full py-2 rounded-full bg-gray-300 hover:bg-gray-400 transition"
            onClick={handleSettingsClick}
          >
            設定
          </button>
        </div>
      </div>
    </div>
  );
};

export default StartScreen;
