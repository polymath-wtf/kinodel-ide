import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { Workspace } from './pages/workspace/Workspace';
import './style.css';

createRoot(document.getElementById('root')!).render(<StrictMode><Workspace /></StrictMode>);
