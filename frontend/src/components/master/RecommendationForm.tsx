/**
 * RecommendationForm — форма создания/редактирования микса кальянщика (T-095).
 */

import { useState, type FormEvent } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../../api/client';

type StrengthLevel = 'light' | 'medium' | 'strong';

interface TobaccoOption {
  id: number;
  name: string;
  brand: string;
}

interface RecItem {
  tobacco_id: number;
  tobacco_name: string;
  weight_grams: number;
}

export interface RecommendationFormValues {
  name: string;
  strength_level: StrengthLevel;
  items: Array<{ tobacco_id: number; weight_grams: number }>;
}

interface Props {
  initial?: { name: string; strength_level: StrengthLevel; items: RecItem[] };
  onSubmit: (values: RecommendationFormValues) => Promise<void>;
  onCancel: () => void;
}

const STRENGTH_LABELS: Record<StrengthLevel, string> = {
  light: 'Лёгкий (1–4)',
  medium: 'Средний (5–7)',
  strong: 'Крепкий (8–10)',
};

export default function RecommendationForm({ initial, onSubmit, onCancel }: Props) {
  const [name, setName] = useState(initial?.name ?? '');
  const [strengthLevel, setStrengthLevel] = useState<StrengthLevel>(
    initial?.strength_level ?? 'medium',
  );
  const [items, setItems] = useState<RecItem[]>(initial?.items ?? []);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [tobaccoSearch, setTobaccoSearch] = useState('');

  const { data: tobaccos = [] } = useQuery<TobaccoOption[]>({
    queryKey: ['tobaccos-simple'],
    queryFn: () =>
      api
        .get<TobaccoOption[]>('/tobaccos', { params: { limit: 200 } })
        .then((r) => r.data),
    staleTime: 60_000,
  });

  const filteredTobaccos = tobaccos.filter(
    (t) =>
      !items.find((i) => i.tobacco_id === t.id) &&
      (tobaccoSearch === '' ||
        t.name.toLowerCase().includes(tobaccoSearch.toLowerCase()) ||
        t.brand.toLowerCase().includes(tobaccoSearch.toLowerCase())),
  );

  function addTobacco(t: TobaccoOption) {
    setItems((prev) => [
      ...prev,
      { tobacco_id: t.id, tobacco_name: t.name, weight_grams: 25 },
    ]);
    setTobaccoSearch('');
  }

  function removeItem(idx: number) {
    setItems((prev) => prev.filter((_, i) => i !== idx));
  }

  function updateWeight(idx: number, weight: number) {
    setItems((prev) => prev.map((it, i) => (i === idx ? { ...it, weight_grams: weight } : it)));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (items.length === 0) {
      setError('Добавьте хотя бы один табак');
      return;
    }
    setError('');
    setBusy(true);
    try {
      await onSubmit({
        name,
        strength_level: strengthLevel,
        items: items.map(({ tobacco_id, weight_grams }) => ({ tobacco_id, weight_grams })),
      });
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Ошибка сохранения';
      setError(msg);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="rec-form">
      {error && <div className="error">{error}</div>}

      <label className="rec-form-label">
        Название микса
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          maxLength={100}
          className="rec-form-input"
        />
      </label>

      <label className="rec-form-label">
        Крепость
        <select
          value={strengthLevel}
          onChange={(e) => setStrengthLevel(e.target.value as StrengthLevel)}
          className="rec-form-input"
        >
          {(Object.keys(STRENGTH_LABELS) as StrengthLevel[]).map((lvl) => (
            <option key={lvl} value={lvl}>
              {STRENGTH_LABELS[lvl]}
            </option>
          ))}
        </select>
      </label>

      <div className="rec-form-items">
        <p className="rec-form-label">Табаки ({items.length}/5)</p>
        {items.map((it, idx) => (
          <div key={it.tobacco_id} className="rec-item-row">
            <span className="rec-item-name">
              {tobaccos.find((t) => t.id === it.tobacco_id)?.name ?? it.tobacco_name}
            </span>
            <input
              type="number"
              min={5}
              max={40}
              step={5}
              value={it.weight_grams}
              onChange={(e) => updateWeight(idx, Number(e.target.value))}
              className="rec-item-weight"
            />
            <span className="rec-item-unit">г</span>
            <button
              type="button"
              className="rec-item-remove"
              onClick={() => removeItem(idx)}
            >
              ✕
            </button>
          </div>
        ))}

        {items.length < 5 && (
          <div className="rec-tobacco-search">
            <input
              type="text"
              placeholder="Поиск табака..."
              value={tobaccoSearch}
              onChange={(e) => setTobaccoSearch(e.target.value)}
              className="rec-form-input"
            />
            {tobaccoSearch && filteredTobaccos.length > 0 && (
              <ul className="rec-tobacco-dropdown">
                {filteredTobaccos.slice(0, 8).map((t) => (
                  <li key={t.id} onClick={() => addTobacco(t)} className="rec-tobacco-option">
                    {t.name} <span className="rec-tobacco-brand">{t.brand}</span>
                  </li>
                ))}
              </ul>
            )}
            {tobaccoSearch && filteredTobaccos.length === 0 && (
              <p className="info-muted rec-no-results">Табаки не найдены</p>
            )}
          </div>
        )}
      </div>

      <div className="rec-form-actions">
        <button type="submit" disabled={busy} className="btn btn-primary">
          {busy ? 'Сохранение...' : 'Сохранить'}
        </button>
        <button type="button" onClick={onCancel} className="btn rec-btn-cancel">
          Отмена
        </button>
      </div>
    </form>
  );
}
