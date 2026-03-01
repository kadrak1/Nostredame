import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../../api/client';

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface TobaccoData {
  id: number;
  venue_id: number;
  name: string;
  brand: string;
  strength: number;
  flavor_profile: string[] | null;
  in_stock: boolean;
  weight_available_grams: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface TobaccoFormData {
  name: string;
  brand: string;
  strength: number;
  flavor_profile: string;
  in_stock: boolean;
  weight_available_grams: string;
}

const EMPTY_FORM: TobaccoFormData = {
  name: '',
  brand: '',
  strength: 3,
  flavor_profile: '',
  in_stock: true,
  weight_available_grams: '',
};

const STRENGTH_LABELS = ['', 'Легкий', 'Легко-средний', 'Средний', 'Средне-крепкий', 'Крепкий'];

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export default function Tobaccos() {
  const qc = useQueryClient();

  /* --- filters --- */
  const [filterStrength, setFilterStrength] = useState<string>('');
  const [filterBrand, setFilterBrand] = useState('');
  const [filterStock, setFilterStock] = useState<string>('');

  /* --- modal state --- */
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<TobaccoFormData>(EMPTY_FORM);
  const [formError, setFormError] = useState('');

  /* --- delete confirmation --- */
  const [deleteId, setDeleteId] = useState<number | null>(null);

  /* --- data --- */
  const { data: tobaccos, isLoading, isError } = useQuery({
    queryKey: ['tobaccos'],
    queryFn: () => api.get<TobaccoData[]>('/tobaccos').then((r) => r.data),
  });

  /* --- mutations --- */
  const createMut = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      api.post<TobaccoData>('/tobaccos', payload).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tobaccos'] }),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, ...data }: Record<string, unknown> & { id: number }) =>
      api.put<TobaccoData>(`/tobaccos/${id}`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tobaccos'] }),
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => api.delete(`/tobaccos/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tobaccos'] }),
  });

  const toggleStockMut = useMutation({
    mutationFn: ({ id, in_stock }: { id: number; in_stock: boolean }) =>
      api.put<TobaccoData>(`/tobaccos/${id}`, { in_stock }).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tobaccos'] }),
  });

  /* --- helpers --- */
  const openCreate = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setFormError('');
    setModalOpen(true);
  };

  const openEdit = (t: TobaccoData) => {
    setEditingId(t.id);
    setForm({
      name: t.name,
      brand: t.brand,
      strength: t.strength,
      flavor_profile: t.flavor_profile?.join(', ') ?? '',
      in_stock: t.in_stock,
      weight_available_grams: t.weight_available_grams?.toString() ?? '',
    });
    setFormError('');
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    if (!form.name.trim() || !form.brand.trim()) {
      setFormError('Название и бренд обязательны');
      return;
    }

    const payload: Record<string, unknown> = {
      name: form.name.trim(),
      brand: form.brand.trim(),
      strength: form.strength,
      flavor_profile: form.flavor_profile.trim()
        ? form.flavor_profile.split(',').map((s) => s.trim()).filter(Boolean)
        : null,
      in_stock: form.in_stock,
      weight_available_grams: form.weight_available_grams
        ? parseInt(form.weight_available_grams, 10)
        : null,
    };

    try {
      if (editingId) {
        await updateMut.mutateAsync({ id: editingId, ...payload });
      } else {
        await createMut.mutateAsync(payload);
      }
      setModalOpen(false);
    } catch {
      setFormError('Ошибка сохранения');
    }
  };

  const handleDelete = async () => {
    if (deleteId === null) return;
    await deleteMut.mutateAsync(deleteId);
    setDeleteId(null);
  };

  /* --- filtered list --- */
  const filtered = (tobaccos ?? []).filter((t) => {
    if (filterStrength && t.strength !== Number(filterStrength)) return false;
    if (filterBrand && !t.brand.toLowerCase().includes(filterBrand.toLowerCase())) return false;
    if (filterStock === 'yes' && !t.in_stock) return false;
    if (filterStock === 'no' && t.in_stock) return false;
    return true;
  });

  /* --- render --- */
  return (
    <div className="admin-page">
      <div className="tc-header">
        <h1>Каталог табаков</h1>
        <button className="btn btn-primary" onClick={openCreate}>+ Добавить</button>
      </div>

      {/* Filters */}
      <div className="tc-filters">
        <div className="tc-filter-item">
          <label>Крепость
            <select value={filterStrength} onChange={(e) => setFilterStrength(e.target.value)}>
              <option value="">Все</option>
              {[1, 2, 3, 4, 5].map((v) => (
                <option key={v} value={v}>{v} — {STRENGTH_LABELS[v]}</option>
              ))}
            </select>
          </label>
        </div>
        <div className="tc-filter-item">
          <label>Бренд
            <input type="text" placeholder="Поиск по бренду" value={filterBrand}
              onChange={(e) => setFilterBrand(e.target.value)} />
          </label>
        </div>
        <div className="tc-filter-item">
          <label>Наличие
            <select value={filterStock} onChange={(e) => setFilterStock(e.target.value)}>
              <option value="">Все</option>
              <option value="yes">В наличии</option>
              <option value="no">Нет в наличии</option>
            </select>
          </label>
        </div>
      </div>

      {/* Table */}
      {isLoading && <p className="info-muted">Загрузка...</p>}
      {isError && <p className="error">Не удалось загрузить табаки</p>}

      {tobaccos && (
        <div className="tc-table-wrap">
          <table className="tc-table">
            <thead>
              <tr>
                <th>Название</th>
                <th>Бренд</th>
                <th>Крепость</th>
                <th>Вкусы</th>
                <th>Наличие</th>
                <th>Вес (г)</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr><td colSpan={7} className="tc-empty">Табаков не найдено</td></tr>
              )}
              {filtered.map((t) => (
                <tr key={t.id}>
                  <td>{t.name}</td>
                  <td>{t.brand}</td>
                  <td>
                    <span className="tc-strength" data-level={t.strength}>
                      {t.strength}/5
                    </span>
                  </td>
                  <td className="tc-flavors">
                    {t.flavor_profile?.map((f, i) => (
                      <span key={i} className="tc-tag">{f}</span>
                    )) ?? <span className="info-muted">—</span>}
                  </td>
                  <td>
                    <button
                      className={`tc-stock-toggle ${t.in_stock ? 'in-stock' : 'out-of-stock'}`}
                      onClick={() => toggleStockMut.mutate({ id: t.id, in_stock: !t.in_stock })}
                    >
                      {t.in_stock ? 'В наличии' : 'Нет'}
                    </button>
                  </td>
                  <td>{t.weight_available_grams ?? '—'}</td>
                  <td className="tc-actions">
                    <button className="tc-btn-edit" onClick={() => openEdit(t)}>Ред.</button>
                    <button className="tc-btn-del" onClick={() => setDeleteId(t.id)}>Удалить</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="info-muted tc-count">Показано: {filtered.length} из {tobaccos.length}</p>
        </div>
      )}

      {/* Create/Edit Modal */}
      {modalOpen && (
        <div className="tc-modal-overlay" onClick={() => setModalOpen(false)}>
          <div className="tc-modal" onClick={(e) => e.stopPropagation()}>
            <h2>{editingId ? 'Редактировать табак' : 'Добавить табак'}</h2>

            {formError && <p className="error">{formError}</p>}

            <label>Название
              <input type="text" value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </label>

            <label>Бренд
              <input type="text" value={form.brand}
                onChange={(e) => setForm({ ...form, brand: e.target.value })} />
            </label>

            <label>Крепость (1-5)
              <select value={form.strength}
                onChange={(e) => setForm({ ...form, strength: Number(e.target.value) })}>
                {[1, 2, 3, 4, 5].map((v) => (
                  <option key={v} value={v}>{v} — {STRENGTH_LABELS[v]}</option>
                ))}
              </select>
            </label>

            <label>Вкусовой профиль (через запятую)
              <input type="text" placeholder="фруктовый, мятный, ягодный"
                value={form.flavor_profile}
                onChange={(e) => setForm({ ...form, flavor_profile: e.target.value })} />
            </label>

            <label>Вес (граммы, опционально)
              <input type="number" min="0" value={form.weight_available_grams}
                onChange={(e) => setForm({ ...form, weight_available_grams: e.target.value })} />
            </label>

            <label className="tc-checkbox-label">
              <input type="checkbox" checked={form.in_stock}
                onChange={(e) => setForm({ ...form, in_stock: e.target.checked })} />
              В наличии
            </label>

            <div className="tc-modal-actions">
              <button className="btn btn-primary" onClick={handleSubmit}
                disabled={createMut.isPending || updateMut.isPending}>
                {createMut.isPending || updateMut.isPending ? 'Сохранение...' : 'Сохранить'}
              </button>
              <button className="btn fp-btn-secondary" onClick={() => setModalOpen(false)}>Отмена</button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {deleteId !== null && (
        <div className="tc-modal-overlay" onClick={() => setDeleteId(null)}>
          <div className="tc-modal tc-modal-sm" onClick={(e) => e.stopPropagation()}>
            <h2>Удалить табак?</h2>
            <p className="info-muted">Табак будет скрыт из каталога. Это действие можно отменить.</p>
            <div className="tc-modal-actions">
              <button className="btn fp-btn-danger" onClick={handleDelete}
                disabled={deleteMut.isPending}>
                {deleteMut.isPending ? 'Удаление...' : 'Удалить'}
              </button>
              <button className="btn fp-btn-secondary" onClick={() => setDeleteId(null)}>Отмена</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
