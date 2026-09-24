import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  getMyProfile,
  loginUser,
  signupUser,
  removeStoredToken,
  redeemCode
} from '../services/auth';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Restore authenticated session on app mount
  useEffect(() => {
    let isMounted = true;
    async function hydrateAuth() {
      try {
        const profile = await getMyProfile();
        if (isMounted) {
          setUser(profile);
        }
      } catch (err) {
        if (isMounted) {
          setUser(null);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }
    hydrateAuth();
    return () => {
      isMounted = false;
    };
  }, []);

  const login = async (email, password) => {
    const res = await loginUser({ email, password });
    setUser(res.user);
    return res;
  };

  const signup = async (name, email, password) => {
    const res = await signupUser({ name, email, password });
    setUser(res.user);
    return res;
  };

  const logout = () => {
    removeStoredToken();
    setUser(null);
  };

  const redeem = async (code) => {
    const res = await redeemCode({ code });
    if (res.user) {
      setUser(res.user);
    }
    return res;
  };

  const isPro = Boolean(user?.is_pro);

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isLoggedIn: Boolean(user),
        isPro,
        login,
        signup,
        logout,
        redeem,
        setUser
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
