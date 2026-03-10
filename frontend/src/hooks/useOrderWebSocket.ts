/**
 * useOrderWebSocket — хук WebSocket для страницы статуса QR-заказа (T-064).
 *
 * Подключается к WS /ws/orders/{publicId}.
 *
 * Протокол (бэкенд → клиент):
 *   {"type": "status",        "public_id": ..., "status": ...}  — начальный снапшот
 *   {"type": "status_update", "status": ...}                    — обновление статуса
 *   {"type": "ping"}                                            — keepalive (каждые 25 с)
 *
 * Клиент → бэкенд:
 *   {"type": "pong"}  — ответ на ping (необязательно, но желательно)
 *
 * Логика переподключения:
 *   - Экспоненциальный backoff: 1 с → 2 с → 4 с → … → 30 с max
 *   - При terminal-статусе (served / cancelled) или коде закрытия 4004 — не переподключаться
 *   - При анмаунте компонента — закрыть соединение без попытки переподключиться
 */

import { useCallback, useEffect, useRef, useState } from 'react';

export type OrderStatusValue =
  | 'pending'
  | 'accepted'
  | 'preparing'
  | 'served'
  | 'cancelled'
  | (string & Record<never, never>); // fallback для неизвестных статусов

const TERMINAL_STATUSES = new Set<string>(['served', 'cancelled']);
const MAX_BACKOFF_MS = 30_000;
const INITIAL_BACKOFF_MS = 1_000;

export interface OrderWebSocketState {
  /** Текущий статус заказа (null — ещё не получен) */
  status: OrderStatusValue | null;
  /** WS-соединение установлено */
  connected: boolean;
  /** Последнее соединение завершилось с ошибкой (не будет сброшено при переподключении) */
  hasError: boolean;
}

export function useOrderWebSocket(publicId: string | undefined): OrderWebSocketState {
  const [state, setState] = useState<OrderWebSocketState>({
    status: null,
    connected: false,
    hasError: false,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const retryCountRef = useRef(0);
  /** Флаг «не переподключаться» — terminal статус или анмаунт */
  const stopRef = useRef(false);

  /**
   * Ref, указывающий на актуальную функцию connect. Используется внутри
   * ws.onclose, чтобы избежать прямой ссылки на `connect` до завершения
   * её объявления (иначе ESLint no-use-before-define выдаёт ошибку).
   * Обновляется в useEffect ниже каждый раз, когда connect пересоздаётся.
   */
  const connectRef = useRef<() => void>(() => undefined);

  const connect = useCallback(() => {
    if (!publicId || stopRef.current) return;

    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${proto}//${window.location.host}/ws/orders/${publicId}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      retryCountRef.current = 0;
      setState((s) => ({ ...s, connected: true, hasError: false }));
    };

    ws.onmessage = (event: MessageEvent) => {
      try {
        const msg: unknown = JSON.parse(event.data as string);
        if (typeof msg !== 'object' || msg === null) return;
        const m = msg as Record<string, unknown>;

        if (m['type'] === 'status' || m['type'] === 'status_update') {
          const newStatus = m['status'] as string;
          if (TERMINAL_STATUSES.has(newStatus)) {
            stopRef.current = true;
          }
          setState((s) => ({ ...s, status: newStatus }));
        } else if (m['type'] === 'ping') {
          // Reply pong (optional but courteous)
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'pong' }));
          }
        }
      } catch {
        // Ignore malformed JSON
      }
    };

    ws.onerror = () => {
      setState((s) => ({ ...s, hasError: true }));
      // onclose fires immediately after onerror — reconnect handled there
    };

    ws.onclose = (event: CloseEvent) => {
      wsRef.current = null;
      setState((s) => ({ ...s, connected: false }));

      // 4004 = order not found; terminal = no more updates expected
      if (stopRef.current || event.code === 4004) return;

      // Exponential backoff reconnect via connectRef to avoid a direct
      // self-reference inside useCallback that ESLint flags as
      // no-use-before-define (connect closure capturing itself).
      const backoff = Math.min(
        INITIAL_BACKOFF_MS * Math.pow(2, retryCountRef.current),
        MAX_BACKOFF_MS,
      );
      retryCountRef.current += 1;
      retryTimerRef.current = setTimeout(() => {
        retryTimerRef.current = null;
        connectRef.current();
      }, backoff);
    };
  }, [publicId]);

  // Keep connectRef pointing at the latest connect instance so that the
  // onclose timer callback always calls the freshest version.
  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    // Note: In React StrictMode (dev), effects run twice (mount → cleanup → mount).
    // The cleanup correctly sets stopRef=true and nullifies onclose, preventing a
    // ghost reconnect. The second mount resets stopRef=false and reconnects cleanly.
    // This causes two WS handshakes in dev but is harmless in production.
    stopRef.current = false;
    retryCountRef.current = 0;
    connect();

    return () => {
      // Prevent reconnect on component unmount
      stopRef.current = true;
      if (retryTimerRef.current !== null) {
        clearTimeout(retryTimerRef.current);
        retryTimerRef.current = null;
      }
      if (wsRef.current !== null) {
        wsRef.current.onclose = null; // suppress reconnect triggered by close
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return state;
}
