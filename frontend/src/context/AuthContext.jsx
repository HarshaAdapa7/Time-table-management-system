import React, { createContext, useState, useEffect, useContext } from 'react';

const AuthContext = createContext(null);
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(() => localStorage.getItem('token') || null);
  const [user, setUser] = useState(() => {
    try {
      const cachedUser = localStorage.getItem('user');
      return cachedUser ? JSON.parse(cachedUser) : null;
    } catch (e) {
      console.error("Error parsing cached user from localStorage:", e);
      return null;
    }
  });

  const isAuthenticated = !!token;

  const login = async (email, password) => {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'bypass-tunnel-reminder': 'true'
      },
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Login failed. Please verify credentials.');
    }

    const data = await response.json();
    setToken(data.access_token);
    const userData = {
      email: data.email,
      name: data.name,
      role: data.role,
      department_id: data.department_id,
      department_name: data.department_name,
      faculty_id: data.faculty_id,
    };
    setUser(userData);
    
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('user', JSON.stringify(userData));
    return userData;
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  };

  const authenticatedFetch = async (url, options = {}) => {
    const headers = {
      ...options.headers,
      'bypass-tunnel-reminder': 'true'
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(`${API_BASE_URL}${url}`, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      logout();
      throw new Error('Session expired. Please log in again.');
    }

    return response;
  };

  return (
    <AuthContext.Provider value={{ token, user, isAuthenticated, login, logout, authenticatedFetch }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
