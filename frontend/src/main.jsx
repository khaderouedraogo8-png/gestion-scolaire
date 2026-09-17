import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './index.css';
import { registerOfflineSync } from './utils/offlineQueue';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);

registerOfflineSync();

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    const register = () =>
      navigator.serviceWorker.register('/sw.js').catch(() => {});
    if (import.meta.env.PROD || import.meta.env.VITE_ENABLE_SW === 'true') {
      register();
    }
  });
}
