import React, { useEffect, useState } from 'react';
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
  const [tag, setTag] = useState<string>('');
  const [variables, setVariables] = useState<string[]>([]);
  const [variableValues, setVariableValues] = useState<Record<string, string>>({});

  useEffect(() => {
    // 例: APIからtagを取得
    fetch('http://localhost:8000/api/rules/1/')
      .then(res => res.json())
      .then(data => {
        setTag(data.tag);
        setVariables(extractVariables(data.tag));
      });
  }, []);

  const handleGenerateClick = () => {
    // HTMLの生成処理
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
    <div className="min-h-screen bg-gray-100 py-8">
      <div className="max-w-4xl mx-auto">
        <SiteNameDisplay />
        <VariableDisplay
          variables={variables}
          variableValues={variableValues}
          setVariableValues={setVariableValues}
        />
        <div className="flex flex-col gap-4">
          <Button name="Wordをアップロード" onClick={handleWordUpload}/>
          <Button name="HTMLを生成" onClick={handleGenerateClick}/>
          <Button name="HTMLをダウンロード" onClick={handleHtmlDownload}/>
        </div>
      </div>
    </div>
  );
};

export default GenerationScreen;