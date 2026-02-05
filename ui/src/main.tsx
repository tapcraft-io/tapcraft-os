import React from 'react';
import ReactDOM from 'react-dom/client';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './pages/AppShell';
import Dashboard from './pages/Dashboard';
import Agent from './pages/Agent';
import Workflows from './pages/Workflows';
import Settings from './pages/Settings';
import Apps from './pages/Apps';
import Runs from './pages/Runs';
import './styles.css';

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'apps', element: <Apps /> },
      { path: 'workflows', element: <Workflows /> },
      { path: 'agent', element: <Agent /> },
      { path: 'runs', element: <Runs /> },
      { path: 'settings', element: <Settings /> }
    ]
  }
]);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,
      refetchOnWindowFocus: false,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </React.StrictMode>
);
