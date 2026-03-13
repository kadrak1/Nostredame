/**
 * Recommendations — страница управления миксами кальянщика (T-095).
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../../api/client';
import RecommendationForm, {
  type RecommendationFormValues,
} from '../../components/master/RecommendationForm';

type StrengthLevel = 'light' | 'medium' | 'strong';

interface RecItem {
  tobacco_id: number;
  weight_grams: number;
}

interface Recommendation {
  id: number;
  name: string;
  strength_level: StrengthLevel;
  items: RecItem[];
  created_at: string;
}

const STRENGTH_LABEL: Record<StrengthLevel, string> = {
  light: 'Лёгкий',
  medium: 'Средний',
  strong: 'Крепкий',
};

type Mode = { type: 'list' } | { type: 'create' } | { type: 'edit'; rec: Recommendation };

export default function MasterRecommendationsPage() {
  const qc = useQueryClient();
  const [mode, setMode] = useState<Mode>({ type: 'list' });

  const { data: recs = [], isLoading, isError } = useQuery<Recommendation[]>({
    queryKey: ['master-recommendations'],
    queryFn: () =>
      api
        .get<Recommendation[]>('/admin/master/recommendations', {
          params: { include_inactive: false },
        })
        .then((r) => r.data),
  });

  const createMut = useMutation({
    mutationFn: (values: RecommendationFormValues) =>
      api.post('/master/recommendations', values).then((r) => r.data),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['master-recommendations'] });
      setMode({ type: 'list' });
    },
  });

  const updateMut = useMutation({
    mutationFn: ({ id, values }: { id: number; values: RecommendationFormValues }) =>
      api.put(`/master/recommendations/${id}`, values).then((r) => r.data),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['master-recommendations'] });
      setMode({ type: 'list' });
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => api.delete(`/master/recommendations/${id}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['master-recommendations'] });
    },
  });

  if (mode.type === 'create') {
    return (
      <div className="master-page">
        <div className="master-page-header">
          <h2>Новый микс</h2>
        </div>
        <RecommendationForm
          onSubmit={async (values) => { await createMut.mutateAsync(values); }}
          onCancel={() => setMode({ type: 'list' })}
        />
      </div>
    );
  }

  if (mode.type === 'edit') {
    const rec = mode.rec;
    return (
      <div className="master-page">
        <div className="master-page-header">
          <h2>Редактировать микс</h2>
        </div>
        <RecommendationForm
          initial={{
            name: rec.name,
            strength_level: rec.strength_level,
            items: rec.items.map((it) => ({
              tobacco_id: it.tobacco_id,
              tobacco_name: '',
              weight_grams: it.weight_grams,
            })),
          }}
          onSubmit={async (values) => { await updateMut.mutateAsync({ id: rec.id, values }); }}
          onCancel={() => setMode({ type: 'list' })}
        />
      </div>
    );
  }

  return (
    <div className="master-page">
      <div className="master-page-header">
        <h2>Рекомендации</h2>
        <button
          className="btn btn-primary"
          onClick={() => setMode({ type: 'create' })}
          disabled={recs.length >= 10}
        >
          + Добавить микс
        </button>
      </div>

      {isLoading && <p className="info-muted">Загрузка...</p>}
      {isError && <p className="error">Не удалось загрузить рекомендации</p>}

      {!isLoading && !isError && recs.length === 0 && (
        <p className="info-muted master-empty">Рекомендаций пока нет. Добавьте первый микс!</p>
      )}

      <div className="rec-list">
        {recs.map((rec) => (
          <div key={rec.id} className="rec-card">
            <div className="rec-card-header">
              <span className="rec-card-name">{rec.name}</span>
              <span className={`rec-card-strength rec-strength-${rec.strength_level}`}>
                {STRENGTH_LABEL[rec.strength_level]}
              </span>
            </div>
            <p className="rec-card-items-count">
              {rec.items.length} {rec.items.length === 1 ? 'табак' : rec.items.length < 5 ? 'табака' : 'табаков'}
            </p>
            <div className="rec-card-actions">
              <button
                className="btn rec-btn-edit"
                onClick={() => setMode({ type: 'edit', rec })}
              >
                Изменить
              </button>
              <button
                className="btn rec-btn-delete"
                disabled={deleteMut.isPending}
                onClick={() => {
                  if (confirm(`Удалить микс «${rec.name}»?`)) {
                    deleteMut.mutate(rec.id);
                  }
                }}
              >
                Удалить
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
