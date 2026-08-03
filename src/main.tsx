import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import App from './App.tsx';
import './index.css';
import { GovernanceProvider } from './context/GovernanceContext.tsx';
import { OperationsProvider } from './context/OperationsContext.tsx';
import { AIChatProvider } from './context/AIChatContext.tsx';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <GovernanceProvider>
      <OperationsProvider>
        <AIChatProvider>
          <App />
        </AIChatProvider>
      </OperationsProvider>
    </GovernanceProvider>
  </StrictMode>,
);
