import Button from '../components/Button';
import SiteNameDisplay from '../components/SiteNameDisplay';

const GenerationScreen: React.FC = () => {
  const handleGenerateClick = () => {
    // Your logic here
    console.log('Generate button clicked');
  };

  return (
    <div className="h-auto flex flex-col items-center justify-center overflow-hidden gap-8 mt-60">
			<SiteNameDisplay />
      <Button name="Wordをアップロード" onClick={handleGenerateClick}/>
			<Button name="HTMLを生成" onClick={handleGenerateClick}/>
			<Button name="HTMLをダウンロード" onClick={handleGenerateClick}/>
    </div>
  );
};


export default GenerationScreen;