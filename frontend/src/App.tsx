// src/App.tsx
import React from 'react';
import { Routes, Route } from 'react-router-dom';
import StartScreen from './pages/Start-screen';
import SettingsScreen from './pages/Setting-screen';
import Header from './components/Header'; 
import GenerationScreen from './pages/Generation-screen';

function App() {
  return (
    <>
      <Header /> 
      <Routes>
        <Route path="/" element={<StartScreen />} />
        <Route path="/generation/:site" element={<GenerationScreen />} />
        <Route path="/settings" element={<SettingsScreen />} />
        <Route path="/settings/:tabId" element={<SettingsScreen />} />
      </Routes>
    </>
  );
}

export default App;
