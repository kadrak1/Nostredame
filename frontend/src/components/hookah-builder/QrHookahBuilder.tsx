/**
 * QrHookahBuilder — контейнер QR-заказа кальяна (T-063).
 *
 * Аналог HookahBuilder, но для гостей, зашедших по QR-коду стола.
 * Отличия от HookahBuilder:
 *   - Не требует bookingId / guestPhone
 *   - Отправляет POST /api/orders с { table_id, strength, items[] }
 *   - После успешной отправки вызывает onComplete(publicId) с public_id заказа
 *
 * Props:
 *   tableId    — ID стола (из URL /table/:tableId)
 *   onComplete — callback с public_id заказа (для редиректа на страницу статуса)
 */

import { useState, useCallback } from 'react';
import { useMutation } from '@tanstack/react-query';
import api from '../../api/client';
import StrengthSelector, { type StrengthLevel } from './StrengthSelector';
import MasterRecommendations from './MasterRecommendations';
import TobaccoSelector, {
  DEFAULT_WEIGHT,
  MAX_TOBACCOS,
  type TobaccoData,
  type SelectedItem,
} from './TobaccoSelector';
import OrderPreview from './OrderPreview';

interface OrderItem {
  tobacco_id: number;
  weight_grams: number;
}

interface QrOrderResponse {
  id: number;
  public_id: string;
  table_id: number;
  status: string;
  source: string;
  created_at: string;
}

interface QrHookahBuilderProps {
  tableId: number;
  onComplete: (publicId: string) => void;
}

export default function QrHookahBuilder({ tableId, onComplete }: QrHookahBuilderProps) {
  const [strength, setStrength] = useState<StrengthLevel | null>(null);
  const [selected, setSelected] = useState<Map<number, SelectedItem>>(new Map());
  const [pendingMix, setPendingMix] = useState<OrderItem[] | null>(null);
  const [submitError, setSubmitError] = useState('');

  const handleToggle = useCallback((tobacco: TobaccoData) => {
    setSelected((prev) => {
      if (!prev.has(tobacco.id) && prev.size >= MAX_TOBACCOS) return prev;
      const next = new Map(prev);
      if (next.has(tobacco.id)) {
        next.delete(tobacco.id);
      } else {
        next.set(tobacco.id, { tobacco });
      }
      return next;
    });
  }, []);

  const handleStrengthChange = useCallback((level: StrengthLevel) => {
    setStrength(level);
    setSelected(new Map());
    setPendingMix(null);
  }, []);

  const handleApplyMix = useCallback((items: { tobacco_id: number }[]) => {
    setSelected(new Map());
    setPendingMix(items.map((i) => ({ tobacco_id: i.tobacco_id, weight_grams: DEFAULT_WEIGHT })));
  }, []);

  const handleMixApplied = useCallback((items: Map<number, SelectedItem>) => {
    setSelected(items);
    setPendingMix(null);
  }, []);

  const selectedItems = Array.from(selected.values());

  const createMutation = useMutation({
    mutationFn: (payload: { table_id: number; strength: number; items: OrderItem[] }) =>
      api.post<QrOrderResponse>('/orders', payload).then((r) => r.data),
    onSuccess: (data) => {
      onComplete(data.public_id);
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Ошибка при создании заказа. Попробуйте ещё раз.';
      setSubmitError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    },
  });

  const handleSubmit = () => {
    if (!strength || selectedItems.length === 0) return;
    setSubmitError('');
    createMutation.mutate({
      table_id: tableId,
      strength: strengthToNumber(strength),
      items: selectedItems.map((i) => ({
        tobacco_id: i.tobacco.id,
        weight_grams: DEFAULT_WEIGHT,
      })),
    });
  };

  return (
    <div className="hb-container">
      <div className="hb-header">
        <h2 className="hb-title">Заказать кальян</h2>
        <p className="hb-subtitle">
          Выберите табаки — кальянщик получит заказ и приготовит кальян
        </p>
      </div>

      <StrengthSelector value={strength} onChange={handleStrengthChange} />

      {strength && (
        <MasterRecommendations strengthLevel={strength} onApplyMix={handleApplyMix} />
      )}

      <TobaccoSelector
        strengthLevel={strength}
        selected={selected}
        onToggle={handleToggle}
        pendingMix={pendingMix}
        onMixApplied={handleMixApplied}
      />

      {selectedItems.length > 0 && <OrderPreview items={selectedItems} />}

      {submitError && <div className="error">{submitError}</div>}

      <div className="hb-actions">
        <button
          type="button"
          className="btn btn-primary hb-submit-btn"
          onClick={handleSubmit}
          disabled={!strength || selectedItems.length === 0 || createMutation.isPending}
        >
          {createMutation.isPending ? 'Отправляем...' : 'Заказать кальян'}
        </button>
      </div>
    </div>
  );
}

/** Map StrengthLevel label to a numeric value for the API (mid-range). */
function strengthToNumber(level: StrengthLevel): number {
  switch (level) {
    case 'light':  return 3;
    case 'medium': return 6;
    case 'strong': return 9;
  }
}
