/**
 * TableOrder — страница оформления QR-заказа кальяна (T-063).
 *
 * Маршрут: /table/:tableId/order
 *
 * Встраивает QrHookahBuilder. После успешного создания заказа
 * перенаправляет на /order/:publicId (страница статуса, T-064).
 */

import { useParams, useNavigate } from 'react-router-dom';
import QrHookahBuilder from '../components/hookah-builder/QrHookahBuilder';

export default function TableOrder() {
  const { tableId } = useParams<{ tableId: string }>();
  const navigate = useNavigate();

  const numericTableId = Number(tableId);
  if (!tableId || !Number.isInteger(numericTableId) || numericTableId <= 0) {
    return (
      <div style={{ maxWidth: 480, margin: '60px auto', padding: 24, textAlign: 'center' }}>
        <h2>Неверный номер стола</h2>
        <p style={{ color: 'var(--text-muted)' }}>
          Отсканируйте QR-код заново или обратитесь к персоналу.
        </p>
      </div>
    );
  }

  const handleComplete = (publicId: string) => {
    navigate(`/order/${publicId}`);
  };

  return (
    <div style={{ maxWidth: 640, margin: '0 auto', padding: '24px 16px' }}>
      <QrHookahBuilder tableId={numericTableId} onComplete={handleComplete} />
    </div>
  );
}
