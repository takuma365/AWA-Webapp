// src/App.tsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import StartScreen from './Start-screen';
import SettingScreen from './Setting-screen';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<StartScreen />} />
        <Route path="/settings" element={<SettingScreen />} />
      </Routes>
    </Router>
  );
}

export default App;
