import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { Workspace } from './pages/workspace/Workspace';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import './style.css';

const queryClient = new QueryClient();
createRoot(document.getElementById('root')!).render(<StrictMode><QueryClientProvider client={queryClient}><Workspace /></QueryClientProvider></StrictMode>);
