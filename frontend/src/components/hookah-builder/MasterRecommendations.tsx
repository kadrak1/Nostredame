/**
 * MasterRecommendations — блок «Рекомендует кальянщик».
 * Загружает активные рекомендации для выбранного strength_level,
 * кнопка «Выбрать этот микс» предзаполняет TobaccoSelector.
 */

import { useQuery } from '@tanstack/react-query';
import api from '../../api/client';
import type { StrengthLevel } from './StrengthSelector';

interface RecommendationItem {
  tobacco_id: number;
  tobacco_name: string;
  flavor_profile: string[];
}

interface Recommendation {
  id: number;
  name: string;
  strength_level: StrengthLevel;
  items: RecommendationItem[];
  created_at: string;
}

interface MasterRecommendationsProps {
  strengthLevel: StrengthLevel;
  onApplyMix: (items: RecommendationItem[]) => void;
}

export default function MasterRecommendations({ strengthLevel, onApplyMix }: MasterRecommendationsProps) {
  const { data: recommendations = [], isLoading, isError } = useQuery({
    queryKey: ['master-recommendations', strengthLevel],
    queryFn: () =>
      api
        .get<Recommendation[]>('/master/recommendations', { params: { strength_level: strengthLevel } })
        .then((r) => r.data),
    staleTime: 60_000,
  });

  if (isLoading) {
    return <p className="info-muted hb-rec-loading">Загрузка рекомендаций...</p>;
  }

  if (isError) {
    return null; // Молча игнорируем — раздел опциональный
  }

  if (recommendations.length === 0) {
    return null;
  }

  return (
    <div className="hb-rec-block">
      <p className="hb-section-label">Рекомендует кальянщик</p>
      <div className="hb-rec-list">
        {recommendations.map((rec) => (
          <div key={rec.id} className="hb-rec-card">
            <div className="hb-rec-info">
              <span className="hb-rec-name">{rec.name}</span>
              <span className="hb-rec-items">
                {rec.items.length} {rec.items.length === 1 ? 'табак' : rec.items.length < 5 ? 'табака' : 'табаков'}
              </span>
              {(() => {
                const tags = [...new Set(rec.items.flatMap((i) => i.flavor_profile))];
                return tags.length > 0 ? (
                  <div className="hb-rec-flavors">
                    {tags.map((f) => (
                      <span key={f} className="tc-tag">{f}</span>
                    ))}
                  </div>
                ) : null;
              })()}
            </div>
            <button
              type="button"
              className="btn hb-rec-apply-btn"
              onClick={() => onApplyMix(rec.items)}
            >
              Выбрать микс
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
