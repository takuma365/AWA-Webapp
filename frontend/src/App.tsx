// src/App.tsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import StartScreen from './pages/Start-screen';
import SettingsScreen from './pages/Setting-screen';
import Header from './components/Header'; 

function App() {
  return (
    <Router>
      <Header /> 
      <Routes>
        <Route path="/" element={<StartScreen />} />
        <Route path="/settings/:tabId" element={<SettingsScreen />} />
      </Routes>
    </Router>
  );
}

export default App;
