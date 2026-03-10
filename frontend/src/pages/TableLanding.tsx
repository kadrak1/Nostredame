/**
 * TableLanding — посадочная страница для QR-кода стола (T-063).
 *
 * Маршрут: /table/:tableId
 *
 * Показывает название заведения, номер стола и кнопку «Заказать кальян»,
 * которая ведёт на /table/:tableId/order.
 */

import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import api from '../api/client';

interface TableInfo {
  id: number;
  number: number;
  venue_id: number;
  venue_name: string;
}

export default function TableLanding() {
  const { tableId } = useParams<{ tableId: string }>();
  const navigate = useNavigate();

  const { data, isLoading, isError } = useQuery<TableInfo>({
    queryKey: ['table-info', tableId],
    queryFn: () => api.get<TableInfo>(`/tables/${tableId}/info`).then((r) => r.data),
    enabled: !!tableId,
    retry: 1,
  });

  if (isLoading) {
    return (
      <div className="tl-page">
        <div className="tl-loading">Загрузка...</div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="tl-page">
        <div className="tl-error">
          <h2>Стол не найден</h2>
          <p>Попробуйте отсканировать QR-код заново или обратитесь к персоналу.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="tl-page">
      <div className="tl-card">
        <div className="tl-venue-name">{data.venue_name}</div>
        <div className="tl-table-badge">
          <span className="tl-table-label">Стол</span>
          <span className="tl-table-number">№{data.number}</span>
        </div>
        <p className="tl-hint">
          Сделайте заказ кальяна прямо сейчас — кальянщик получит его моментально
        </p>
        <button
          type="button"
          className="btn btn-primary tl-order-btn"
          onClick={() => navigate(`/table/${tableId}/order`)}
        >
          Заказать кальян
        </button>
      </div>
    </div>
  );
}
