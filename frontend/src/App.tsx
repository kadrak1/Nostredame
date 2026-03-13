import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, MasterRoute, PrivateRoute } from './auth';
import { GuestAuthProvider } from './guest-auth';
import Home from './pages/Home';
import Booking from './pages/Booking';
import HookahBuilderTest from './pages/HookahBuilderTest';
import TableLanding from './pages/TableLanding';
import TableOrder from './pages/TableOrder';
import OrderStatus from './pages/OrderStatus';
import AdminLogin from './pages/admin/Login';
import AdminLayout from './layouts/AdminLayout';
import AdminDashboard from './pages/admin/Dashboard';
import FloorPlan from './pages/admin/FloorPlan';
import Tobaccos from './pages/admin/Tobaccos';
import AdminBookings from './pages/admin/Bookings';
import QRCodes from './pages/admin/QRCodes';
import MasterLogin from './pages/master/Login';
import MasterLayout from './layouts/MasterLayout';
import OrderQueue from './pages/master/OrderQueue';
import OrderHistory from './pages/master/OrderHistory';
import MasterRecommendationsPage from './pages/master/Recommendations';
import './App.css';
import './master.css';

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
            <Route path="/hookah-test" element={<HookahBuilderTest />} />

            {/* QR-table flow (T-063) */}
            <Route path="/table/:tableId" element={<TableLanding />} />
            <Route path="/table/:tableId/order" element={<TableOrder />} />
            <Route path="/order/:publicId" element={<OrderStatus />} />

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
              <Route path="qr-codes" element={<QRCodes />} />
            </Route>

            {/* Master — login is public */}
            <Route path="/master/login" element={<MasterLogin />} />

            {/* Master — protected with role guard */}
            <Route
              path="/master"
              element={
                <MasterRoute>
                  <MasterLayout />
                </MasterRoute>
              }
            >
              <Route index element={<OrderQueue />} />
              <Route path="orders" element={<OrderQueue />} />
              <Route path="history" element={<OrderHistory />} />
              <Route path="recommendations" element={<MasterRecommendationsPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
        </GuestAuthProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
