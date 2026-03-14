/**
 * HookahBuilder — контейнер предзаказа кальяна.
 *
 * Props:
 *   bookingId     — ID брони, к которой привязывается предзаказ
 *   guestPhone    — телефон гостя (для верификации на бэкенде)
 *   onComplete    — callback при успешной отправке заказа
 *   onSkip        — callback при нажатии «Пропустить»
 *   repeatOrderSlot — слот для RepeatOrderButton (T-100), опционально
 */

import { useState, useCallback, type ReactNode } from 'react';
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

function strengthToNumber(level: StrengthLevel): number {
  switch (level) {
    case 'light':  return 3;
    case 'medium': return 6;
    case 'strong': return 9;
  }
}

interface HookahBuilderProps {
  bookingId: number;
  guestPhone: string;
  onComplete: () => void;
  onSkip: () => void;
  repeatOrderSlot?: ReactNode;
}

export default function HookahBuilder({
  bookingId,
  guestPhone,
  onComplete,
  onSkip,
  repeatOrderSlot,
}: HookahBuilderProps) {
  const [strength, setStrength] = useState<StrengthLevel | null>(null);
  const [selected, setSelected] = useState<Map<number, SelectedItem>>(new Map());
  const [pendingMix, setPendingMix] = useState<OrderItem[] | null>(null);
  const [submitError, setSubmitError] = useState('');

  // HIGH-2 fix: enforce MAX_TOBACCOS in state (not just in UI)
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

  // HIGH-1 + HIGH-3 fix: reset selection AND pendingMix when strength changes
  const handleStrengthChange = useCallback((level: StrengthLevel) => {
    setStrength(level);
    setSelected(new Map());
    setPendingMix(null);
  }, []);

  // Apply a master recommendation mix — clear current selection, let TobaccoSelector resolve IDs
  // Accept any object with tobacco_id (RecommendationItem from MasterRecommendations),
  // then convert to OrderItem by injecting the fixed DEFAULT_WEIGHT.
  const handleApplyMix = useCallback((items: { tobacco_id: number }[]) => {
    setSelected(new Map());
    setPendingMix(items.map((i) => ({ tobacco_id: i.tobacco_id, weight_grams: DEFAULT_WEIGHT })));
  }, []);

  // TobaccoSelector resolved pendingMix → SelectedItem entries
  const handleMixApplied = useCallback((items: Map<number, SelectedItem>) => {
    setSelected(items);
    setPendingMix(null);
  }, []);

  const selectedItems = Array.from(selected.values());

  const createMutation = useMutation({
    mutationFn: (payload: { guest_phone: string; strength: number; items: OrderItem[] }) =>
      api.post(`/bookings/${bookingId}/orders`, payload).then((r) => r.data),
    onSuccess: () => {
      onComplete();
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Ошибка при создании предзаказа. Попробуйте ещё раз.';
      setSubmitError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    },
  });

  const handleSubmit = () => {
    if (!strength || selectedItems.length === 0) return;
    setSubmitError('');
    createMutation.mutate({
      guest_phone: guestPhone,
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
        <h2 className="hb-title">Предзаказ кальяна</h2>
        <p className="hb-subtitle">
          Выберите табаки заранее — кальянщик подготовит всё к вашему приходу
        </p>
      </div>

      {repeatOrderSlot && <div className="hb-repeat-slot">{repeatOrderSlot}</div>}

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
          className="btn fp-btn-secondary hb-skip-btn"
          onClick={onSkip}
          disabled={createMutation.isPending}
        >
          Пропустить
        </button>
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
