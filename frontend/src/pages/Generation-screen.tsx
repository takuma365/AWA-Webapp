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
  const [variables, setVariables] = useState<string[]>([]);
  const [variableValues, setVariableValues] = useState<Record<string, string>>({});
  const [siteInfo, setSiteInfo] = useState<any>(null);
  const [rules, setRules] = useState<any[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<any>(null);

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
                  // rulesDataから変数を抽出して一意化
                  const varsArray: string[] = [];
                  rulesData.forEach((r: any) => {
                    varsArray.push(...extractVariables(r.tag));
                  });
                  const extractedVars: string[] = Array.from(new Set(varsArray));
                  setVariables(extractedVars);
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
      console.log('HTML生成結果:', result);

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
        alert(`HTMLファイルが生成されダウンロードされました。\n\nXMLディレクトリ: ${result.xml_directory}\nドキュメント: ${result.document_xml_path}\n出力: ${result.output_html_path}`);
      } else {
        alert(result.message || 'HTML生成が完了しました。');
      }

    } catch (error) {
      console.error('API送信エラー:', error);
      alert('API送信中にエラーが発生しました。');
    }
  };

  const handleWordUpload = async () => {
    // ファイル選択のinput要素を作成
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.docx';
    input.style.display = 'none';
    
    input.onchange = async (event) => {
      const target = event.target as HTMLInputElement;
      const file = target.files?.[0];
      
      if (!file) {
        return;
      }

      if (!file.name.endsWith('.docx')) {
        alert('サポートされていないファイル形式です。.docx形式のみ対応しています。');
        return;
      }

      setIsUploading(true);
      
      try {
        // FormDataを作成してファイルと設定IDを送信
        const formData = new FormData();
        formData.append('file', file);
        
        // サイトの変換設定IDを取得
        if (siteInfo && siteInfo.conversion_settings && siteInfo.conversion_settings.length > 0) {
          formData.append('setting_id', siteInfo.conversion_settings[0].id.toString());
        } else {
          alert('変換設定が見つかりませんでした。');
          return;
        }

        const response = await fetch('http://localhost:8000/api/convert/', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        setUploadResult(result);
        
        console.log('アップロード結果:', result);
        
        // XMLファイル情報が含まれている場合の処理
        if (result.xml_files) {
          console.log('XMLファイル情報:', result.xml_files);
          alert(`変換が完了しました。XMLファイルが解凍されました。\nファイル数: ${result.xml_files.file_count || 0}`);
        } else {
          alert('変換が完了しました。');
        }
        
      } catch (error) {
        console.error('ファイルアップロードエラー:', error);
        alert(`ファイルアップロード中にエラーが発生しました: ${error instanceof Error ? error.message : 'Unknown error'}`);
      } finally {
        setIsUploading(false);
      }
    };
    
    // ファイル選択ダイアログを表示
    document.body.appendChild(input);
    input.click();
    document.body.removeChild(input);
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
        
        {/* アップロード結果を表示 */}
        {uploadResult && (
          <div className="w-full mb-4 p-4 bg-green-100 border border-green-400 rounded">
            <h3 className="text-lg font-semibold text-green-800 mb-2">アップロード完了</h3>
            <p className="text-green-700">ファイル名: {uploadResult.original_filename}</p>
            {uploadResult.xml_files && (
              <div className="mt-2">
                <p className="text-green-700">XML解凍結果:</p>
                <ul className="list-disc list-inside text-green-600">
                  <li>ファイル数: {uploadResult.xml_files.file_count}</li>
                  {uploadResult.xml_files.relative_directory && (
                    <li>保存先: {uploadResult.xml_files.relative_directory}</li>
                  )}
                </ul>
              </div>
            )}
          </div>
        )}
        
        <div className="flex flex-col gap-4 w-full items-center">
          <Button 
            name={isUploading ? "アップロード中..." : "Wordをアップロード"} 
            onClick={handleWordUpload}
            disabled={isUploading}
          />
          <Button name="HTMLを生成" onClick={handleGenerateClick}/>
          <Button name="HTMLをダウンロード" onClick={handleHtmlDownload}/>
        </div>
      </div>
    </div>
  );
};

export default GenerationScreen;