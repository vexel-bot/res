import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import App from './App.tsx';
import './index.css';
import './components/PageAtmosphere.css';
import './components/InterfaceRefinement.css';
import './motion/MotionSystem.css';
import './components/SettingsView.css';
// Resolve the theme contract after legacy styles; the workspace layer below
// only overrides authenticated non-media routes.
import './components/ThemeSystem.css';
// Scoped to authenticated routes other than Image and Video.
import './components/CreativeWorkspace.css';
import './components/ResponsiveLayout.css';
import { GovernanceProvider } from './context/GovernanceContext.tsx';
import { OperationsProvider } from './context/OperationsContext.tsx';
import { AIChatProvider } from './context/AIChatContext.tsx';
import { OfferProvider } from './context/OfferContext.tsx';
import { AuthProvider } from './context/AuthContext.tsx';
import { ThemeProvider } from './context/ThemeContext.tsx';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider>
      <ThemeProvider>
        <GovernanceProvider>
          <OfferProvider>
            <OperationsProvider>
              <AIChatProvider>
                <App />
              </AIChatProvider>
            </OperationsProvider>
          </OfferProvider>
        </GovernanceProvider>
      </ThemeProvider>
    </AuthProvider>
  </StrictMode>,
);
