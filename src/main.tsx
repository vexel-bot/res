import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import App from './App.tsx';
import '@fontsource-variable/manrope';
import '@fontsource-variable/bricolage-grotesque';
import '@fontsource/ibm-plex-mono/400.css';
import '@fontsource/ibm-plex-mono/600.css';
import './index.css';
import './design-system/lab.css';
import { GovernanceProvider } from './context/GovernanceContext.tsx';
import { OperationsProvider } from './context/OperationsContext.tsx';
import { AIChatProvider } from './context/AIChatContext.tsx';
import { OfferProvider } from './context/OfferContext.tsx';
import { ServerStateProvider } from './context/ServerStateContext.tsx';
import { ProductDataProvider } from './context/ProductDataContext.tsx';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <GovernanceProvider>
      <OfferProvider>
        <ServerStateProvider>
          <ProductDataProvider>
            <OperationsProvider>
              <AIChatProvider>
                <App />
              </AIChatProvider>
            </OperationsProvider>
          </ProductDataProvider>
        </ServerStateProvider>
      </OfferProvider>
    </GovernanceProvider>
  </StrictMode>,
);
