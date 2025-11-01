import React from 'react';
import ReactDOM from 'react-dom/client';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './pages/AppShell';
import Dashboard from './pages/Dashboard';
import Agent from './pages/Agent';
import Workflows from './pages/Workflows';
import Settings from './pages/Settings';
import './styles.css';

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'agent', element: <Agent /> },
      { path: 'workflows', element: <Workflows /> },
      { path: 'settings', element: <Settings /> }
    ]
  }
]);

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </React.StrictMode>
);
