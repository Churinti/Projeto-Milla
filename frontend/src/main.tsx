import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { PortaoAcesso } from './components/PortaoAcesso.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <PortaoAcesso>
      <App />
    </PortaoAcesso>
  </StrictMode>,
)
