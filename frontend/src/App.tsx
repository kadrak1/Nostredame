import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, PrivateRoute } from './auth';
import { GuestAuthProvider } from './guest-auth';
import Home from './pages/Home';
import Booking from './pages/Booking';
import AdminLogin from './pages/admin/Login';
import AdminLayout from './layouts/AdminLayout';
import AdminDashboard from './pages/admin/Dashboard';
import FloorPlan from './pages/admin/FloorPlan';
import Tobaccos from './pages/admin/Tobaccos';
import AdminBookings from './pages/admin/Bookings';
import './App.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <GuestAuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Guest pages */}
            <Route path="/" element={<Home />} />
            <Route path="/booking" element={<Booking />} />

            {/* Admin — login is public */}
            <Route path="/admin/login" element={<AdminLogin />} />

            {/* Admin — protected, with sidebar layout */}
            <Route
              path="/admin"
              element={
                <PrivateRoute>
                  <AdminLayout />
                </PrivateRoute>
              }
            >
              <Route index element={<AdminDashboard />} />
              <Route path="floor-plan" element={<FloorPlan />} />
              <Route path="tobaccos" element={<Tobaccos />} />
              <Route path="bookings" element={<AdminBookings />} />
            </Route>
          </Routes>
        </BrowserRouter>
        </GuestAuthProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
