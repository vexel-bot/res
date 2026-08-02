import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import App from './App.tsx';
import './index.css';
import { GovernanceProvider } from './context/GovernanceContext.tsx';
import { OperationsProvider } from './context/OperationsContext.tsx';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <GovernanceProvider>
      <OperationsProvider>
        <App />
      </OperationsProvider>
    </GovernanceProvider>
  </StrictMode>,
);
