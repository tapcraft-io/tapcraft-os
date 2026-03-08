import React from 'react';
import ReactDOM from 'react-dom/client';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './pages/AppShell';
import Dashboard from './pages/Dashboard';
import Workflows from './pages/Workflows';
import Settings from './pages/Settings';
import Secrets from './pages/Secrets';
import OAuthProviders from './pages/OAuthProviders';
import Activities from './pages/Activities';
import ActivityDetail from './pages/ActivityDetail';
import Runs from './pages/Runs';
import RunDetail from './pages/RunDetail';
import WorkflowEditor from './pages/WorkflowEditor';
import Webhooks from './pages/Webhooks';
import { ToastProvider } from './components/Toast';
import { ErrorBoundary } from './components/ErrorBoundary';
import { AuthGate } from './components/AuthGate';
import './styles.css';

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <ErrorBoundary><Dashboard /></ErrorBoundary> },
      { path: 'activities', element: <ErrorBoundary><Activities /></ErrorBoundary> },
      { path: 'activities/:id', element: <ErrorBoundary><ActivityDetail /></ErrorBoundary> },
      { path: 'workflows', element: <ErrorBoundary><Workflows /></ErrorBoundary> },
      { path: 'workflows/:id', element: <ErrorBoundary><WorkflowEditor /></ErrorBoundary> },
      { path: 'runs', element: <ErrorBoundary><Runs /></ErrorBoundary> },
      { path: 'runs/:id', element: <ErrorBoundary><RunDetail /></ErrorBoundary> },
      { path: 'webhooks', element: <ErrorBoundary><Webhooks /></ErrorBoundary> },
      { path: 'secrets', element: <ErrorBoundary><Secrets /></ErrorBoundary> },
      { path: 'oauth', element: <ErrorBoundary><OAuthProviders /></ErrorBoundary> },
      { path: 'settings', element: <ErrorBoundary><Settings /></ErrorBoundary> }
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
      <ToastProvider>
        <AuthGate>
          <RouterProvider router={router} />
        </AuthGate>
      </ToastProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
