/**
 * TobaccoSelector — список табаков с поиском и чекбоксами.
 * Загружает GET /api/tobaccos/public?strength_min=X&strength_max=Y.
 * Максимум 3 табака. Граммовка фиксирована — кальянщик решает сам.
 */

import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../../api/client';
import type { StrengthLevel } from './StrengthSelector';
import { STRENGTH_RANGE } from './StrengthSelector';

export const DEFAULT_WEIGHT = 25; // фиксированный вес для API — кальянщик решает соотношение
export const MAX_TOBACCOS = 3;

export interface TobaccoData {
  id: number;
  name: string;
  brand: string;
  strength: number;
  flavor_profile: string[];
  in_stock: boolean;
}

export interface SelectedItem {
  tobacco: TobaccoData;
}

interface PendingMixItem {
  tobacco_id: number;
  weight_grams: number;
}

interface TobaccoSelectorProps {
  strengthLevel: StrengthLevel | null;
  selected: Map<number, SelectedItem>;
  onToggle: (tobacco: TobaccoData) => void;
  pendingMix: PendingMixItem[] | null;
  onMixApplied: (items: Map<number, SelectedItem>) => void;
}

export default function TobaccoSelector({
  strengthLevel,
  selected,
  onToggle,
  pendingMix,
  onMixApplied,
}: TobaccoSelectorProps) {
  const [search, setSearch] = useState('');

  const [strengthMin, strengthMax] = strengthLevel ? STRENGTH_RANGE[strengthLevel] : [1, 10];

  const { data: tobaccos = [], isLoading, isError } = useQuery({
    queryKey: ['tobaccos-public', strengthMin, strengthMax],
    queryFn: () =>
      api
        .get<TobaccoData[]>('/tobaccos/public', {
          params: { strength_min: strengthMin, strength_max: strengthMax },
        })
        .then((r) => r.data),
    staleTime: 60_000,
    enabled: strengthLevel !== null,
  });

  useEffect(() => {
    if (!pendingMix || tobaccos.length === 0) return;
    const byId = new Map(tobaccos.map((t) => [t.id, t]));
    const resolved = new Map<number, SelectedItem>();
    for (const { tobacco_id } of pendingMix) {
      const tobacco = byId.get(tobacco_id);
      if (tobacco) resolved.set(tobacco_id, { tobacco });
    }
    onMixApplied(new Map(Array.from(resolved.entries()).slice(0, MAX_TOBACCOS)));
  }, [pendingMix, tobaccos, onMixApplied]);

  const filtered = tobaccos.filter((t) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return t.name.toLowerCase().includes(q) || t.brand.toLowerCase().includes(q);
  });

  const reachedMax = selected.size >= MAX_TOBACCOS;

  if (!strengthLevel) {
    return <p className="info-muted hb-tobacco-hint">Сначала выберите крепость</p>;
  }
  if (isLoading) return <p className="info-muted">Загрузка табаков...</p>;
  if (isError) return <p className="error">Не удалось загрузить табаки. Попробуйте обновить страницу.</p>;

  return (
    <div className="hb-tobacco-selector">
      <div className="hb-tobacco-header">
        <p className="hb-section-label">
          Выберите табаки
          <span className="hb-tobacco-counter"> ({selected.size}/{MAX_TOBACCOS})</span>
        </p>
        <input
          type="search"
          className="hb-tobacco-search"
          placeholder="Поиск по названию или бренду..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {filtered.length === 0 && <p className="info-muted">Ничего не найдено</p>}

      <div className="hb-tobacco-list">
        {filtered.map((tobacco) => {
          const isSelected = selected.has(tobacco.id);
          const disabled = !isSelected && reachedMax;
          return (
            <div
              key={tobacco.id}
              className={`hb-tobacco-item ${isSelected ? 'selected' : ''} ${disabled ? 'disabled' : ''}`}
            >
              <label className="hb-tobacco-checkbox-label">
                <input
                  type="checkbox"
                  checked={isSelected}
                  disabled={disabled}
                  onChange={() => onToggle(tobacco)}
                />
                <div className="hb-tobacco-info">
                  <span className="hb-tobacco-name">{tobacco.name}</span>
                  <span className="hb-tobacco-brand">{tobacco.brand}</span>
                  {tobacco.flavor_profile.length > 0 && (
                    <div className="hb-tobacco-flavors">
                      {tobacco.flavor_profile.map((f) => (
                        <span key={f} className="tc-tag">{f}</span>
                      ))}
                    </div>
                  )}
                </div>
                <span className="tc-strength">{tobacco.strength}</span>
              </label>
            </div>
          );
        })}
      </div>

      {reachedMax && (
        <p className="info-muted hb-max-hint">Максимум {MAX_TOBACCOS} табака в одном заказе</p>
      )}
    </div>
  );
}
