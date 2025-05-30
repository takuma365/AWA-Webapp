import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App.tsx'
import './index.css'
// import App from './Start-screen.tsx'

// React Router v7の将来の変更に対応するための設定
const router = {
  future: {
    v7_startTransition: true,
    v7_relativeSplatPath: true
  }
};

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter future={router.future}>
    <App />
    </BrowserRouter>
  </React.StrictMode>,
)
