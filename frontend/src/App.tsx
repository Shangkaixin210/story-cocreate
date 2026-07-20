import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { StoryProvider } from './contexts/StoryContext';
import Header from './components/Layout/Header';
import Background from './components/Layout/Background';
import Loading from './components/Shared/Loading';
import LoginPage from './pages/LoginPage';
import HomePage from './pages/HomePage';
import CharacterPage from './pages/CharacterPage';
import StoryPlayPage from './pages/StoryPlayPage';
import GalleryPage from './pages/GalleryPage';
import TalentPage from './pages/TalentPage';
import ChannelPage from './pages/ChannelPage';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <Loading text="加载中..." />;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function ChannelGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <Loading text="加载中..." />;
  if (!user) return <Navigate to="/login" replace />;
  if (!user.age_group) return <Navigate to="/channel" replace />;
  return <>{children}</>;
}

function AppRoutes() {
  const { user, loading } = useAuth();

  if (loading) return <Loading text="正在启动故事世界..." />;

  return (
    <Routes>
      <Route
        path="/login"
        element={user ? <Navigate to="/" replace /> : <LoginPage />}
      />
      <Route
        path="/channel"
        element={
          <ProtectedRoute>
            <ChannelPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <ChannelGuard>
              <HomePage />
            </ChannelGuard>
          </ProtectedRoute>
        }
      />
      <Route
        path="/characters"
        element={
          <ProtectedRoute>
            <CharacterPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/play/:storyId"
        element={
          <ProtectedRoute>
            <StoryProvider>
              <StoryPlayPage />
            </StoryProvider>
          </ProtectedRoute>
        }
      />
      <Route
        path="/gallery"
        element={
          <ProtectedRoute>
            <GalleryPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/talent/:storyId"
        element={
          <ProtectedRoute>
            <TalentPage />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Background />
        <Header />
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
