/**
 * OrderQueue — страница активной очереди заказов кальянщика (T-093).
 * Данные загружаются через React Query, обновляются по WS.
 */

import { useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../../api/client';
import { useAuth } from '../../auth';
import { useMasterWebSocket } from '../../hooks/useMasterWebSocket';
import { useOrderNotification } from '../../hooks/useOrderNotification';
import OrderCard, { type MasterOrderData } from '../../components/master/OrderCard';

interface OrderListResponse {
  orders: MasterOrderData[];
  total: number;
}

export default function OrderQueue() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const { notify } = useOrderNotification();

  const { data, isLoading, isError } = useQuery<OrderListResponse>({
    queryKey: ['master-orders-active'],
    queryFn: () => api.get<OrderListResponse>('/master/orders').then((r) => r.data),
    refetchInterval: 30_000, // fallback polling if WS is down
  });

  // Invalidate query and play notification when new order arrives via WS
  const handleWsEvent = useCallback(
    (event: { type: string }) => {
      if (event.type === 'order.new') {
        notify();
      }
      void qc.invalidateQueries({ queryKey: ['master-orders-active'] });
    },
    [qc, notify],
  );

  const { connected } = useMasterWebSocket(user?.venue_id, handleWsEvent);

  const statusMutation = useMutation({
    mutationFn: ({ orderId, status }: { orderId: number; status: string }) =>
      api.put(`/master/orders/${orderId}/status`, { status }).then((r) => r.data),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['master-orders-active'] });
    },
  });

  const handleStatusChange = useCallback(
    (orderId: number, status: string) =>
      statusMutation.mutateAsync({ orderId, status }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [statusMutation.mutateAsync],
  );

  return (
    <div className="master-page">
      <div className="master-page-header">
        <h2>Очередь заказов</h2>
        <span className={`ws-indicator ${connected ? 'ws-indicator--on' : 'ws-indicator--off'}`}>
          {connected ? '● Онлайн' : '○ Оффлайн'}
        </span>
      </div>

      {isLoading && <p className="info-muted">Загрузка...</p>}
      {isError && <p className="error">Не удалось загрузить заказы</p>}

      {!isLoading && !isError && (
        <>
          {data?.orders.length === 0 ? (
            <p className="info-muted master-empty">Активных заказов нет</p>
          ) : (
            <div className="order-queue">
              {data?.orders.map((order) => (
                <OrderCard
                  key={order.id}
                  order={order}
                  onStatusChange={handleStatusChange}
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
