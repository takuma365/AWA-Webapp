import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import Button from '../components/Button';
import SiteNameDisplay from '../components/SiteNameDisplay';
import VariableDisplay from '../components/VariableDisplay';

function extractVariables(template: string): string[] {
  const regex = /\{([a-zA-Z0-9_\-]+)\}/g;
  const variables = new Set<string>();
  let match;
  while ((match = regex.exec(template)) !== null) {
    variables.add(match[1]);
  }
  return Array.from(variables);
}

const GenerationScreen: React.FC = () => {
  const { site } = useParams<{ site: string }>();
  const [tag, setTag] = useState<string>('');
  const [variables, setVariables] = useState<string[]>([]);
  const [variableValues, setVariableValues] = useState<Record<string, string>>({});
  const [siteInfo, setSiteInfo] = useState<any>(null);
  const [rules, setRules] = useState<any[]>([]);

  useEffect(() => {
    // サイト情報を取得
    if (site) {
      fetch(`http://localhost:8000/api/sites/?url=${site}`)
        .then(res => res.json())
        .then(data => {
          if (data.length > 0) {
            setSiteInfo(data[0]);
            console.log('現在のサイト情報:', data[0]);
            
            // サイトの変換設定からrulesを取得
            if (data[0].conversion_settings && data[0].conversion_settings.length > 0) {
              const settingId = data[0].conversion_settings[0].id;
              fetch(`http://localhost:8000/api/rules/?setting_id=${settingId}`)
                .then(res => res.json())
                .then(rulesData => {
                  setRules(rulesData);
                  console.log('取得したrules:', rulesData);
                  // rulesDataから変数を抽出して一意化
                  const varsArray: string[] = [];
                  rulesData.forEach((r: any) => {
                    varsArray.push(...extractVariables(r.tag));
                  });
                  const extractedVars: string[] = Array.from(new Set(varsArray));
                  setVariables(extractedVars);
                  console.log('抽出された変数:', extractedVars);
                });
            }
          }
        })
        .catch(error => console.error('サイト情報の取得に失敗:', error));
    }
  }, [site]);

  // 変数の値が変更されたときに実行される関数
  const handleVariableChange = (variable: string, value: string) => {
    setVariableValues(prev => {
      const newValues = { ...prev, [variable]: value };
      console.log('更新された変数の値:', newValues);
      return newValues;
    });
  };

  const handleGenerateClick = async () => {
    const newData = {
      ...siteInfo,
      rules: rules,
      variable_values: variableValues
    };
    console.log('送信するJSONデータ:', newData);

    try {
      const response = await fetch('http://localhost:8000/api/generate-html/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newData),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();

      // 生成されたHTMLコンテンツをダウンロード
      if (result.generated_html) {
        const blob = new Blob([result.generated_html], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `generated_html_${new Date().getTime()}.html`; // ダウンロードファイル名
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        alert('HTMLファイルがダウンロードされました。');
      }

    } catch (error) {
      console.error('API送信エラー:', error);
      alert('API送信中にエラーが発生しました。');
    }
  };

  const handleWordUpload = () => {
    // Your logic here
    console.log('Generate button clicked');
  };

  const handleHtmlDownload = () => {
    // Your logic here
    console.log('Generate button clicked');
  };

  return (
    <div className="min-h-screen bg-gray-100 pt-16 pb-8 flex justify-center">
      <div className="max-w-3xl w-full flex flex-col items-center">
        <SiteNameDisplay />
        <VariableDisplay
          variables={variables}
          variableValues={variableValues}
          setVariableValues={handleVariableChange}
        />
        <div className="flex flex-col gap-4 w-full items-center">
          <Button name="Wordをアップロード" onClick={handleWordUpload}/>
          <Button name="HTMLを生成" onClick={handleGenerateClick}/>
          <Button name="HTMLをダウンロード" onClick={handleHtmlDownload}/>
        </div>
      </div>
    </div>
  );
};

export default GenerationScreen;