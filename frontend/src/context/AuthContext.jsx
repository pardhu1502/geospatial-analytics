import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import apiClient, { getStoredToken, setStoredToken } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchCurrentUser = useCallback(async () => {
    try {
      const { data } = await apiClient.get('/auth/me');
      setUser(data);
      return data;
    } catch (err) {
      setStoredToken(null);
      setUser(null);
      throw err;
    }
  }, []);

  useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      setLoading(false);
      return;
    }
    fetchCurrentUser().finally(() => setLoading(false));
  }, [fetchCurrentUser]);

  const login = useCallback(
    async (email, password) => {
      const { data } = await apiClient.post('/auth/login', { email, password });
      setStoredToken(data.access_token);
      await fetchCurrentUser();
      return data;
    },
    [fetchCurrentUser]
  );

  const register = useCallback(
    async (email, password, fullName) => {
      const { data } = await apiClient.post('/auth/register', {
        email,
        password,
        full_name: fullName,
      });
      setStoredToken(data.access_token);
      await fetchCurrentUser();
      return data;
    },
    [fetchCurrentUser]
  );

  const logout = useCallback(() => {
    setStoredToken(null);
    setUser(null);
  }, []);

  const value = {
    user,
    loading,
    isAuthenticated: Boolean(user),
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}
