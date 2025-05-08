const App = () => {
  return (
      <div className="flex items-center justify-center p-20">
        <div className="bg-white w-full max-w-3xl p-20 rounded-lg flex flex-col items-center gap-12">

         <div className="w-full max-w-sm pb-20">
          <select className="w-full max-w-sm p-2 text-base border border-gray-300 rounded">
              <option>サイトを選択する</option>
              <option>サイトA</option>
              <option>サイトB</option>
            </select>
         </div>

          <div className="flex flex-col items-center gap-8 w-full max-w-xs">
            <button className="w-full py-2 rounded-full bg-gray-300 hover:bg-gray-400 transition">記事を生成</button>
            <button className="w-full py-2 rounded-full bg-gray-300 hover:bg-gray-400 transition">設定</button>
          </div>
        </div>
      </div>
  );
};

export default App;
