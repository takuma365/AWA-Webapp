import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';

const SiteNameDisplay = () => {
  const { site } = useParams<{ site: string }>();
  const [siteName, setSiteName] = useState<string>('');

  useEffect(() => {
    // URLパラメータのsiteはurlなので、それを使ってサイト名を取得
    fetch(`/api/sites/?url=${site}`)
      .then(response => response.json())
      .then(data => {
        if (data.length > 0) {
          setSiteName(data[0].name);  // APIから返ってきたサイトのnameを使用
        }
      })
      // .catch(error => console.error('Error:', error));
  }, [site]);

  return (
    <div className="w-full text-center mb-4">
      <h1 className="text-3xl font-bold">{siteName}</h1>
    </div>
  );
};

export default SiteNameDisplay;