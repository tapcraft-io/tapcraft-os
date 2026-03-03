import { useState, useEffect, useCallback, createContext, useContext, type ReactNode } from 'react';

const API_KEY_STORAGE_KEY = 'tapcraft_api_key';

interface AuthContextValue {
  apiKey: string;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthGate');
  return ctx;
}

/** Return the stored API key (for use outside React, e.g. in apiFetch). */
export function getStoredApiKey(): string | null {
  return localStorage.getItem(API_KEY_STORAGE_KEY);
}

export function AuthGate({ children }: { children: ReactNode }) {
  const [apiKey, setApiKey] = useState<string | null>(() => localStorage.getItem(API_KEY_STORAGE_KEY));
  const [checking, setChecking] = useState(!!apiKey);
  const [valid, setValid] = useState(false);

  // Validate a key against the backend
  const validate = useCallback(async (key: string): Promise<boolean> => {
    try {
      const res = await fetch('/api/auth/validate', {
        headers: { 'X-API-Key': key },
      });
      return res.ok;
    } catch {
      return false;
    }
  }, []);

  // On mount, check stored key
  useEffect(() => {
    if (!apiKey) {
      setChecking(false);
      return;
    }
    let cancelled = false;
    validate(apiKey).then((ok) => {
      if (cancelled) return;
      if (ok) {
        setValid(true);
      } else {
        localStorage.removeItem(API_KEY_STORAGE_KEY);
        setApiKey(null);
      }
      setChecking(false);
    });
    return () => { cancelled = true; };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const logout = useCallback(() => {
    localStorage.removeItem(API_KEY_STORAGE_KEY);
    setApiKey(null);
    setValid(false);
  }, []);

  if (checking) {
    return (
      <div className="flex items-center justify-center h-screen bg-background-dark">
        <div className="text-zinc-400 text-sm">Checking authentication...</div>
      </div>
    );
  }

  if (!apiKey || !valid) {
    return <LoginScreen onLogin={(key) => {
      localStorage.setItem(API_KEY_STORAGE_KEY, key);
      setApiKey(key);
      setValid(true);
    }} validate={validate} />;
  }

  return (
    <AuthContext.Provider value={{ apiKey, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

function LoginScreen({ onLogin, validate }: {
  onLogin: (key: string) => void;
  validate: (key: string) => Promise<boolean>;
}) {
  const [key, setKey] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = key.trim();
    if (!trimmed) return;

    setLoading(true);
    setError('');

    const ok = await validate(trimmed);
    if (ok) {
      onLogin(trimmed);
    } else {
      setError('Invalid API key');
    }
    setLoading(false);
  };

  return (
    <div className="flex items-center justify-center h-screen bg-background-dark">
      <div className="w-full max-w-sm mx-4">
        <div className="bg-surface-dark border border-border-dark rounded-xl p-8">
          {/* Logo */}
          <div className="text-center mb-8">
            <h1 className="text-white text-2xl font-bold tracking-tight flex items-center justify-center gap-2">
              <span className="material-symbols-outlined text-primary icon-filled text-3xl">terminal</span>
              Tapcraft
            </h1>
            <p className="text-zinc-500 text-xs font-medium tracking-wider uppercase mt-1">Automation OS</p>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label htmlFor="api-key" className="block text-sm font-medium text-zinc-400 mb-2">
                API Key
              </label>
              <input
                id="api-key"
                type="password"
                value={key}
                onChange={(e) => setKey(e.target.value)}
                placeholder="tc_..."
                autoFocus
                className="w-full px-3 py-2 bg-surface-light border border-border-dark rounded-lg text-white placeholder-zinc-600 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50"
              />
            </div>

            {error && (
              <p className="text-red-400 text-sm">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading || !key.trim()}
              className="w-full h-10 bg-primary text-zinc-950 rounded-lg text-sm font-bold hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Checking...' : 'Sign In'}
            </button>
          </form>

          <p className="text-zinc-600 text-xs text-center mt-6">
            Find your API key in the server logs or <code className="text-zinc-500">data/api_key</code> file.
          </p>
        </div>
      </div>
    </div>
  );
}
