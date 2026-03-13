import { useState } from 'react';

export interface MasterOrderItemData {
  tobacco_name: string;
  brand: string;
  weight_grams: number;
}

export interface MasterOrderData {
  id: number;
  public_id: string;
  table_number: number;
  strength: number;
  strength_label: string;
  notes: string;
  status: string;
  source: string;
  guest_name: string | null;
  wait_seconds: number;
  items: MasterOrderItemData[];
  created_at: string;
}

interface OrderCardProps {
  order: MasterOrderData;
  onStatusChange: (orderId: number, status: string) => Promise<void>;
}

const STATUS_LABEL: Record<string, string> = {
  pending: 'Ожидает',
  accepted: 'Принят',
  preparing: 'Готовится',
  served: 'Подан',
  cancelled: 'Отменён',
};

const STATUS_CLASS: Record<string, string> = {
  pending: 'order-card--pending',
  accepted: 'order-card--accepted',
  preparing: 'order-card--preparing',
  served: 'order-card--served',
  cancelled: 'order-card--cancelled',
};

function formatWait(seconds: number): string {
  if (seconds < 60) return `${seconds} с`;
  const m = Math.floor(seconds / 60);
  return `${m} мин`;
}

export default function OrderCard({ order, onStatusChange }: OrderCardProps) {
  const [busy, setBusy] = useState(false);

  async function handle(status: string) {
    setBusy(true);
    try {
      await onStatusChange(order.id, status);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={`order-card ${STATUS_CLASS[order.status] ?? ''}`}>
      <div className="order-card-header">
        <span className="order-card-table">Стол #{order.table_number}</span>
        <span className={`order-card-badge order-badge-${order.status}`}>
          {STATUS_LABEL[order.status] ?? order.status}
        </span>
        <span className="order-card-wait">{formatWait(order.wait_seconds)}</span>
      </div>

      <div className="order-card-meta">
        <span className="order-card-strength">{order.strength_label}</span>
        {order.guest_name && (
          <span className="order-card-guest">{order.guest_name}</span>
        )}
      </div>

      {order.notes && (
        <p className="order-card-notes">{order.notes}</p>
      )}

      <ul className="order-card-items">
        {order.items.map((item) => (
          <li key={`${item.tobacco_name}-${item.brand}`} className="order-card-item">
            <span className="order-item-name">{item.tobacco_name}</span>
            <span className="order-item-brand">{item.brand}</span>
            <span className="order-item-weight">{item.weight_grams} г</span>
          </li>
        ))}
      </ul>

      <div className="order-card-actions">
        {order.status === 'pending' && (
          <>
            <button
              className="btn order-btn-accept"
              disabled={busy}
              onClick={() => handle('accepted')}
            >
              Принять
            </button>
            <button
              className="btn order-btn-cancel"
              disabled={busy}
              onClick={() => handle('cancelled')}
            >
              Отклонить
            </button>
          </>
        )}
        {order.status === 'accepted' && (
          <>
            <button
              className="btn order-btn-prepare"
              disabled={busy}
              onClick={() => handle('preparing')}
            >
              Готовлю
            </button>
            <button
              className="btn order-btn-cancel"
              disabled={busy}
              onClick={() => handle('cancelled')}
            >
              Отклонить
            </button>
          </>
        )}
        {order.status === 'preparing' && (
          <button
            className="btn order-btn-serve"
            disabled={busy}
            onClick={() => handle('served')}
          >
            Подан
          </button>
        )}
      </div>
    </div>
  );
}
