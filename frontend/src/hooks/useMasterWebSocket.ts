/**
 * useMasterWebSocket — хук WebSocket для панели кальянщика (T-093).
 *
 * Подключается к WS /ws/master/orders?venue_id=<id>.
 *
 * Протокол (бэкенд → клиент):
 *   {"type": "connected",   "venue_id": ...}
 *   {"type": "order.new",   "order_id": ..., "public_id": ..., "table_number": ..., "strength": ..., "status": ...}
 *   {"type": "order.updated","order_id": ..., "public_id": ..., "table_number": ..., "status": ...}
 *   {"type": "ping"}                                    — keepalive каждые 25 с
 *
 * Клиент → бэкенд:
 *   {"type": "pong"}  — ответ на ping
 */

import { useCallback, useEffect, useRef, useState } from 'react';

export interface MasterOrderEvent {
  type: 'order.new' | 'order.updated';
  order_id: number;
  public_id: string;
  table_number: number;
  strength?: number;
  status: string;
}

export interface MasterWsState {
  connected: boolean;
  lastEvent: MasterOrderEvent | null;
}

const MAX_BACKOFF_MS = 30_000;
const INITIAL_BACKOFF_MS = 1_000;

export function useMasterWebSocket(
  venueId: number | undefined,
  onEvent?: (event: MasterOrderEvent) => void,
): MasterWsState {
  const [state, setState] = useState<MasterWsState>({ connected: false, lastEvent: null });

  const wsRef = useRef<WebSocket | null>(null);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const retryCountRef = useRef(0);
  const stopRef = useRef(false);
  const connectRef = useRef<() => void>(() => undefined);

  // Keep onEvent in a ref to avoid stale closures without re-creating connect
  const onEventRef = useRef(onEvent);
  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  const connect = useCallback(() => {
    if (!venueId || stopRef.current) return;

    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${proto}//${window.location.host}/ws/master/orders?venue_id=${venueId}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      retryCountRef.current = 0;
      setState((s) => ({ ...s, connected: true }));
    };

    ws.onmessage = (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data as string) as Record<string, unknown>;

        if (
          (msg['type'] === 'order.new' || msg['type'] === 'order.updated') &&
          typeof msg['order_id'] === 'number' &&
          typeof msg['status'] === 'string'
        ) {
          const ev = msg as unknown as MasterOrderEvent;
          setState((s) => ({ ...s, lastEvent: ev }));
          onEventRef.current?.(ev);
        } else if (msg['type'] === 'ping' && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'pong' }));
        }
      } catch {
        // Ignore malformed JSON
      }
    };

    ws.onerror = () => {
      // onclose fires immediately after — reconnect handled there
    };

    ws.onclose = () => {
      wsRef.current = null;
      setState((s) => ({ ...s, connected: false }));
      if (stopRef.current) return;

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
  }, [venueId]);

  // Keep connectRef pointing at the latest connect instance
  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    stopRef.current = false;
    retryCountRef.current = 0;
    connect();

    return () => {
      stopRef.current = true;
      if (retryTimerRef.current !== null) {
        clearTimeout(retryTimerRef.current);
        retryTimerRef.current = null;
      }
      if (wsRef.current !== null) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return state;
}
