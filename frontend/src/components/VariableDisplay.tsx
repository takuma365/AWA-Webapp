import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

function extractVariables(template: string): string[] {
  const regex = /\{([a-zA-Z0-9_\-]+)\}/g;
  const variables = new Set<string>();
  let match;
  while ((match = regex.exec(template)) !== null) {
    variables.add(match[1]);
  }
  return Array.from(variables);
}

const VariableDisplay: React.FC = () => {
  const { site } = useParams<{ site: string }>();
  const [siteName, setSiteName] = useState<string>('');
  const [variables, setVariables] = useState<string[]>([]);
  const [variableValues, setVariableValues] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!site) return;
    fetch('http://localhost:8000/api/sites/')
      .then(res => res.json())
      .then(sites => {
        // URLが一致するサイトのみ取得
        const currentSite = sites.find((s: any) => s.url === site);
        if (currentSite) {
          setSiteName(currentSite.name);
          // そのサイトのconversion_settingsだけを使う
          if (
            currentSite.conversion_settings &&
            currentSite.conversion_settings.length > 0
          ) {
            // すべてのrulesを横断して、section: "文頭" のtagを探す
            let found = false;
            for (const setting of currentSite.conversion_settings) {
              if (setting.rules && setting.rules.length > 0) {
                const headRule = setting.rules.find((rule: any) => rule.section === "文頭");
                if (headRule && headRule.tag) {
                  const extracted = extractVariables(headRule.tag);
                  setVariables(extracted);
                  found = true;
                  break;
                }
              }
            }
            if (!found) {
              setVariables([]);
            }
          } else {
            setVariables([]);
          }
        } else {
          setSiteName(site);
          setVariables([]);
        }
      });
  }, [site]);

  return (
    <div className="bg-white shadow rounded-lg p-6 mb-6">
      <h2 className="text-xl font-semibold mb-4">変数一覧</h2>
      <div className="space-y-4">
       {/* ↓最後に消す */}
        {/* <p className="text-gray-600">サイト: {siteName}（{site}）</p> */}
        {variables.length === 0 && <p className="text-gray-500">テンプレートに変数がありません</p>}
        <div className="grid grid-cols-2 gap-4">
          {variables.map((variable) => (
            <div key={variable}>
              <label className="block text-gray-700">{variable}</label>
              <input
                className="border rounded px-2 py-1 w-full"
                type="text"
                value={variableValues[variable] || ''}
                onChange={e =>
                  setVariableValues((prev) => ({ ...prev, [variable]: e.target.value }))
                }
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default VariableDisplay;