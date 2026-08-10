import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import App from './App.tsx';
import './index.css';
import { GovernanceProvider } from './context/GovernanceContext.tsx';
import { OperationsProvider } from './context/OperationsContext.tsx';
import { AIChatProvider } from './context/AIChatContext.tsx';
import { OfferProvider } from './context/OfferContext.tsx';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <GovernanceProvider>
      <OfferProvider>
        <OperationsProvider>
          <AIChatProvider>
            <App />
          </AIChatProvider>
        </OperationsProvider>
      </OfferProvider>
    </GovernanceProvider>
  </StrictMode>,
);
