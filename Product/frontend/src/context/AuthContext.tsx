import React, { createContext, useContext, useState, useEffect } from 'react';
import { authApi } from '../services/api';
import type { UserResponse, PreferenceResponse, PreferenceUpdate } from '../services/api';

interface AuthContextType {
  user: UserResponse | null;
  preferences: PreferenceResponse | null;
  loading: boolean;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, storeName?: string) => Promise<void>;
  logout: () => void;
  updatePreferences: (pref: PreferenceUpdate) => Promise<void>;
  refreshPreferences: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [preferences, setPreferences] = useState<PreferenceResponse | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('burger_agent_token'));
  const [loading, setLoading] = useState<boolean>(true);

  // Load user profile and preferences if token exists
  const loadUserData = async () => {
    try {
      setLoading(true);
      // Fetch user profile and preferences in parallel
      const [userProfile, userPrefs] = await Promise.all([
        authApi.getMe(),
        authApi.getPreference()
      ]);
      setUser(userProfile);
      setPreferences(userPrefs);
    } catch (error) {
      console.error('Failed to load user info', error);
      // Token might be invalid or expired
      logout();
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      loadUserData();
    } else {
      setLoading(false);
    }

    // Handle unauthorized event dispatched by axios response interceptor
    const handleUnauthorized = () => {
      logout();
    };

    window.addEventListener('auth-unauthorized', handleUnauthorized);
    return () => {
      window.removeEventListener('auth-unauthorized', handleUnauthorized);
    };
  }, [token]);

  const login = async (email: string, password: string) => {
    const data = await authApi.login(email, password);
    localStorage.setItem('burger_agent_token', data.access_token);
    setToken(data.access_token);
  };

  const register = async (email: string, password: string, storeName?: string) => {
    const data = await authApi.register(email, password, storeName);
    localStorage.setItem('burger_agent_token', data.access_token);
    setToken(data.access_token);
  };

  const logout = () => {
    localStorage.removeItem('burger_agent_token');
    setToken(null);
    setUser(null);
    setPreferences(null);
  };

  const refreshPreferences = async () => {
    if (token) {
      try {
        const prefs = await authApi.getPreference();
        setPreferences(prefs);
      } catch (error) {
        console.error('Failed to refresh preferences', error);
      }
    }
  };

  const updatePreferences = async (pref: PreferenceUpdate) => {
    if (token) {
      const updatedPrefs = await authApi.updatePreference(pref);
      setPreferences(updatedPrefs);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        preferences,
        loading,
        token,
        login,
        register,
        logout,
        updatePreferences,
        refreshPreferences
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
