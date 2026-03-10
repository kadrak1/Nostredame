/**
 * OrderStatus — страница статуса QR-заказа (T-064).
 *
 * Маршрут: /order/:publicId
 *
 * STUB: базовый вариант — показывает public_id.
 * T-064 добавит WebSocket и прогресс-бар.
 */

import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import api from '../api/client';

interface OrderStatusData {
  public_id: string;
  status: string;
  table_number: number;
  strength: number;
  items: { tobacco_name: string; weight_grams: number }[];
  created_at: string;
  updated_at: string;
}

const STATUS_LABELS: Record<string, string> = {
  pending: '⏳ Ожидает подтверждения',
  accepted: '✅ Принят',
  preparing: '🔥 Готовится',
  ready: '🎉 Готов!',
  delivered: '🪁 Доставлен',
  cancelled: '❌ Отменён',
};

export default function OrderStatus() {
  const { publicId } = useParams<{ publicId: string }>();

  const { data, isLoading, isError } = useQuery<OrderStatusData>({
    queryKey: ['order-status', publicId],
    queryFn: () => api.get<OrderStatusData>(`/orders/${publicId}/status`).then((r) => r.data),
    enabled: !!publicId,
    // Stop polling once order reaches a terminal state (delivered / cancelled).
    // T-064 will replace this with WebSocket push.
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      if (s === 'delivered' || s === 'cancelled') return false;
      return 10_000;
    },
    retry: 1,
  });

  if (isLoading) {
    return (
      <div className="os-page">
        <div className="os-loading">Загрузка статуса...</div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="os-page">
        <div className="os-error">
          <h2>Заказ не найден</h2>
          <p>Проверьте ссылку или обратитесь к персоналу.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="os-page">
      <div className="os-card">
        <h2 className="os-title">Ваш заказ</h2>
        <div className="os-status-badge">
          {STATUS_LABELS[data.status] ?? data.status}
        </div>
        <div className="os-meta">
          <span>Стол №{data.table_number}</span>
          <span>Крепость {data.strength}/10</span>
        </div>
        <ul className="os-items">
          {data.items.map((item, i) => (
            <li key={i} className="os-item">
              {item.tobacco_name}
              <span className="os-item-weight">{item.weight_grams} г</span>
            </li>
          ))}
        </ul>
        <p className="os-hint">
          Страница автоматически обновляется каждые 10 секунд.<br />
          Живые обновления через WebSocket появятся в T-064.
        </p>
      </div>
    </div>
  );
}
