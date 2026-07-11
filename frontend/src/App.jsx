import React from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './pages/Login';
import AdminDashboard from './pages/AdminDashboard';
import HodDashboard from './pages/HodDashboard';
import FacultyDashboard from './pages/FacultyDashboard';

function DashboardSwitch() {
  const { isAuthenticated, user } = useAuth();

  if (!isAuthenticated || !user) {
    return <Login />;
  }

  // Role-based Router gating
  switch (user.role) {
    case 'ADMIN':
      return <AdminDashboard />;
    case 'HOD':
      return <HodDashboard />;
    case 'COORDINATOR':
    case 'FACULTY':
    default:
      return <FacultyDashboard />;
  }
}

export default function App() {
  return (
    <AuthProvider>
      <DashboardSwitch />
    </AuthProvider>
  );
}
