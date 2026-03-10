/**
 * OrderStatus — страница статуса QR-заказа (T-064).
 *
 * Маршрут: /order/:publicId
 *
 * Реализация:
 *  - WebSocket /ws/orders/:publicId — live обновления статуса
 *  - REST GET /api/orders/:publicId/status — метаданные заказа (стол, табаки)
 *    + fallback-поллинг при недоступности WS
 *  - Прогресс-степпер: pending → accepted → preparing → served
 *  - Отдельное состояние для cancelled
 */

import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import api from '../api/client';
import { useOrderWebSocket } from '../hooks/useOrderWebSocket';

/* ── Типы ───────────────────────────────────────────────────────────── */

interface OrderStatusData {
  public_id: string;
  status: string;
  table_number: number;
  strength: number;
  items: { tobacco_name: string; weight_grams: number }[];
  created_at: string;
  updated_at: string;
}

/* ── Конфиг статусов ─────────────────────────────────────────────────── */

const STEP_ORDER = ['pending', 'accepted', 'preparing', 'served'] as const;

const STEP_LABELS: Record<string, string> = {
  pending: 'Ожидает',
  accepted: 'Принят',
  preparing: 'Готовится',
  served: 'Подан',
};

const STEP_ICONS: Record<string, string> = {
  pending: '⏳',
  accepted: '✅',
  preparing: '🔥',
  served: '🪁',
};

const TERMINAL_STATUSES = new Set(['served', 'cancelled']);

/* ── Компонент степпера ─────────────────────────────────────────────── */

function StatusStepper({ status }: { status: string }) {
  const currentIdx = STEP_ORDER.indexOf(status as (typeof STEP_ORDER)[number]);
  // When status is 'served' (terminal positive), all steps are complete
  const isTerminalPositive = status === 'served';

  return (
    <div className="os-stepper">
      {STEP_ORDER.map((step, idx) => {
        const isDone = isTerminalPositive
          ? true // all steps done when served
          : idx < currentIdx;
        const isActive = !isTerminalPositive && idx === currentIdx;
        const stepClass =
          'os-step' + (isDone ? ' done' : isActive ? ' active' : ' upcoming');

        return (
          <div key={step} className="os-step-wrapper">
            {idx > 0 && (
              <div className={`os-connector${isDone || isActive ? ' filled' : ''}`} />
            )}
            <div className={stepClass}>
              <div className="os-step-circle">
                {isDone ? '✓' : isActive ? STEP_ICONS[step] : String(idx + 1)}
              </div>
              <span className="os-step-label">{STEP_LABELS[step]}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ── WS-индикатор соединения ────────────────────────────────────────── */

function WsDot({ connected }: { connected: boolean }) {
  return (
    <span
      className={`os-ws-dot${connected ? ' connected' : ''}`}
      title={connected ? 'Live-обновления активны' : 'Переподключение...'}
    />
  );
}

/* ── Главный компонент ──────────────────────────────────────────────── */

export default function OrderStatus() {
  const { publicId } = useParams<{ publicId: string }>();
  const ws = useOrderWebSocket(publicId);

  const { data, isLoading, isError } = useQuery<OrderStatusData>({
    queryKey: ['order-status', publicId],
    queryFn: () =>
      api.get<OrderStatusData>(`/orders/${publicId}/status`).then((r) => r.data),
    enabled: !!publicId,
    // Поллинг — только если WS не подключён; останавливается при terminal-статусе
    refetchInterval: (query) => {
      if (ws.connected) return false;
      const current = ws.status ?? query.state.data?.status;
      if (current && TERMINAL_STATUSES.has(current)) return false;
      return 10_000;
    },
    retry: 1,
  });

  /* WS-статус приоритетнее REST */
  const status = ws.status ?? data?.status ?? null;

  /* ── Состояния загрузки ────────────────────────── */

  if (isLoading && !status) {
    return (
      <div className="os-page">
        <div className="os-loading">Загрузка статуса...</div>
      </div>
    );
  }

  if ((isError && !data) || !publicId) {
    return (
      <div className="os-page">
        <div className="os-error">
          <h2>Заказ не найден</h2>
          <p>Проверьте ссылку или обратитесь к персоналу.</p>
        </div>
      </div>
    );
  }

  /* ── Основной рендер ───────────────────────────── */

  const isCancelled = status === 'cancelled';

  return (
    <div className="os-page">
      <div className="os-card">
        {/* Заголовок */}
        <div className="os-header">
          <h2 className="os-title">Ваш заказ</h2>
          <WsDot connected={ws.connected} />
        </div>

        {/* Мета */}
        {data && (
          <div className="os-meta">
            <span>Стол №{data.table_number}</span>
            <span>Крепость {data.strength}/10</span>
          </div>
        )}

        {/* Степпер или отменён */}
        {isCancelled ? (
          <div className="os-cancelled">
            <span className="os-cancelled-icon">❌</span>
            <span>Заказ отменён</span>
          </div>
        ) : (
          status && <StatusStepper status={status} />
        )}

        {/* Список табаков */}
        {data && data.items.length > 0 && (
          <ul className="os-items">
            {data.items.map((item, i) => (
              <li key={`${item.tobacco_name}-${item.weight_grams}-${i}`} className="os-item">
                {item.tobacco_name}
                <span className="os-item-weight">{item.weight_grams}&nbsp;г</span>
              </li>
            ))}
          </ul>
        )}

        {/* Подсказка */}
        <p className="os-hint">
          {ws.connected
            ? 'Live-обновления активны — страница обновится автоматически.'
            : ws.hasError
              ? 'Нет соединения — страница обновляется каждые 10 секунд.'
              : 'Подключение...'}
        </p>
      </div>
    </div>
  );
}
