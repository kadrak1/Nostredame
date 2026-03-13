/**
 * OrderHistory — история заказов за выбранную дату (T-094).
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../../api/client';
import type { MasterOrderData } from '../../components/master/OrderCard';

interface OrderListResponse {
  orders: MasterOrderData[];
  total: number;
}

function todayDate(): string {
  return new Date().toISOString().split('T')[0]!;
}

const STATUS_LABEL: Record<string, string> = {
  pending: 'Ожидает',
  accepted: 'Принят',
  preparing: 'Готовится',
  served: 'Подан',
  cancelled: 'Отменён',
};

export default function OrderHistory() {
  const [date, setDate] = useState(todayDate);

  const { data, isLoading, isError } = useQuery<OrderListResponse>({
    queryKey: ['master-orders-history', date],
    queryFn: () =>
      api.get<OrderListResponse>('/master/orders', { params: { date } }).then((r) => r.data),
  });

  return (
    <div className="master-page">
      <div className="master-page-header">
        <h2>История заказов</h2>
        <input
          type="date"
          className="master-date-input"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          max={todayDate()}
        />
      </div>

      {isLoading && <p className="info-muted">Загрузка...</p>}
      {isError && <p className="error">Не удалось загрузить историю</p>}

      {!isLoading && !isError && (
        <>
          {data?.orders.length === 0 ? (
            <p className="info-muted master-empty">Заказов за этот день нет</p>
          ) : (
            <div className="history-table-wrapper">
              <table className="history-table">
                <thead>
                  <tr>
                    <th>Стол</th>
                    <th>Гость</th>
                    <th>Крепость</th>
                    <th>Табаки</th>
                    <th>Статус</th>
                    <th>Ожидание</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.orders.map((order) => (
                    <tr key={order.id} className={`history-row history-row--${order.status}`}>
                      <td>#{order.table_number}</td>
                      <td>{order.guest_name ?? '—'}</td>
                      <td>{order.strength_label}</td>
                      <td>
                        {order.items
                          .map((it) => `${it.tobacco_name} ${it.weight_grams}г`)
                          .join(', ')}
                      </td>
                      <td>
                        <span className={`order-badge order-badge-${order.status}`}>
                          {STATUS_LABEL[order.status] ?? order.status}
                        </span>
                      </td>
                      <td>{Math.round(order.wait_seconds / 60)} мин</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="history-total">Всего: {data?.total ?? 0}</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
