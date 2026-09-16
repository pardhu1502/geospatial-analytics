import { Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login/Login';
import Register from './pages/Register/Register';
import ProjectDashboard from './pages/ProjectDashboard/ProjectDashboard';
import ProjectMap from './pages/ProjectMap/ProjectMap';
import SiteDetail from './pages/SiteDetail/SiteDetail';

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <ProjectDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/projects/:projectId"
          element={
            <ProtectedRoute>
              <ProjectMap />
            </ProtectedRoute>
          }
        />
        <Route
          path="/projects/:projectId/sites/:siteId"
          element={
            <ProtectedRoute>
              <SiteDetail />
            </ProtectedRoute>
          }
        />
      </Routes>
    </Layout>
  );
}
