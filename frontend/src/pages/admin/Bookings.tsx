import { useState, useMemo, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import api from '../../api/client';

/* ------------------------------------------------------------------ */
/*  Types                                                               */
/* ------------------------------------------------------------------ */

type BookingStatus = 'pending' | 'confirmed' | 'completed' | 'cancelled';

interface BookingAdmin {
  id: number;
  venue_id: number;
  table_id: number;
  guest_id: number | null;
  date: string;          // "2026-03-01"
  time_from: string;     // "18:00:00"
  time_to: string;       // "21:00:00"
  guest_count: number;
  guest_name: string;
  guest_phone_masked: string;
  status: BookingStatus;
  notes: string;
  created_at: string;
  updated_at: string;
}

/* ------------------------------------------------------------------ */
/*  Constants                                                           */
/* ------------------------------------------------------------------ */

const STATUS_LABEL: Record<BookingStatus, string> = {
  pending:   'Ожидает',
  confirmed: 'Подтверждена',
  completed: 'Завершена',
  cancelled: 'Отменена',
};

const STATUS_CLASS: Record<BookingStatus, string> = {
  pending:   'ab-status ab-status-pending',
  confirmed: 'ab-status ab-status-confirmed',
  completed: 'ab-status ab-status-completed',
  cancelled: 'ab-status ab-status-cancelled',
};

const ALL_STATUSES: BookingStatus[] = ['pending', 'confirmed', 'completed', 'cancelled'];

/** Возвращает сегодняшнюю дату в локальном часовом поясе (YYYY-MM-DD).
 *  toISOString() даёт UTC, что в UTC+3 до 3:00 ночи даст вчерашний день. */
function todayISO() {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function formatTime(t: string) {
  // "18:00:00" → "18:00"  (слайс безопасен — API всегда возвращает HH:MM:SS)
  return t.slice(0, 5);
}

function formatDate(d: string) {
  // Берём только первые 10 символов на случай если API вернёт datetime
  return new Date(d.slice(0, 10) + 'T00:00:00').toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'short',
  });
}

/* ------------------------------------------------------------------ */
/*  Component                                                           */
/* ------------------------------------------------------------------ */

export default function AdminBookings() {
  const qc = useQueryClient();

  /* --- server-side filters (sent to API) --- */
  const [filterDate, setFilterDate] = useState('');
  const [filterStatus, setFilterStatus] = useState<BookingStatus | ''>('');

  /* --- client-side name filter --- */
  const [filterName, setFilterName] = useState('');

  /* --- pending action confirmation --- */
  const [confirmAction, setConfirmAction] = useState<{
    id: number;
    action: 'confirm' | 'complete' | 'reject';
    name: string;
  } | null>(null);

  /* --- action error (shown to user after failed mutation) --- */
  const [actionError, setActionError] = useState<string | null>(null);

  /* --- data --- */
  // Параметры передаются через queryKey, чтобы queryFn всегда синхронизирован с ключом
  const { data: bookings, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin-bookings', { date: filterDate, status: filterStatus }] as const,
    queryFn: ({ queryKey }) => {
      const [, filters] = queryKey;
      const params: Record<string, string> = {};
      if (filters.date)   params['date']   = filters.date;
      if (filters.status) params['status'] = filters.status;
      return api
        .get<BookingAdmin[]>('/admin/bookings', { params })
        .then((r) => r.data);
    },
    staleTime: 15_000,
  });

  /* --- mutations --- */
  const mutOpts = {
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-bookings'] }),
  };

  const confirmMut = useMutation({
    mutationFn: (id: number) =>
      api.put<BookingAdmin>(`/admin/bookings/${id}/confirm`).then((r) => r.data),
    ...mutOpts,
  });

  const completeMut = useMutation({
    mutationFn: (id: number) =>
      api.put<BookingAdmin>(`/admin/bookings/${id}/complete`).then((r) => r.data),
    ...mutOpts,
  });

  const rejectMut = useMutation({
    mutationFn: (id: number) =>
      api.put<BookingAdmin>(`/admin/bookings/${id}/reject`).then((r) => r.data),
    ...mutOpts,
  });

  const isActionPending =
    confirmMut.isPending || completeMut.isPending || rejectMut.isPending;

  /* --- client-side name filter --- */
  const filtered = useMemo(
    () =>
      (bookings ?? []).filter((b) => {
        if (!filterName) return true;
        return b.guest_name.toLowerCase().includes(filterName.toLowerCase());
      }),
    [bookings, filterName],
  );

  /* --- stats (over all loaded bookings, not filtered by name) --- */
  const stats = useMemo(() => {
    const all = bookings ?? [];
    return {
      pending:   all.filter((b) => b.status === 'pending').length,
      confirmed: all.filter((b) => b.status === 'confirmed').length,
      total:     all.length,
    };
  }, [bookings]);

  /* --- Escape закрывает модал --- */
  const closeModal = useCallback(() => setConfirmAction(null), []);
  useEffect(() => {
    if (!confirmAction) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') closeModal(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [confirmAction, closeModal]);

  /* --- action handler ---
   * setConfirmAction(null) вызывается в finally, чтобы при ошибке
   * контекст (id, action, name) оставался доступен для показа сообщения. */
  const handleAction = async () => {
    if (!confirmAction) return;
    const { id, action } = confirmAction;
    setActionError(null);
    try {
      if (action === 'confirm')  await confirmMut.mutateAsync(id);
      if (action === 'complete') await completeMut.mutateAsync(id);
      if (action === 'reject')   await rejectMut.mutateAsync(id);
      setConfirmAction(null);
    } catch (err: unknown) {
      const detail =
        axios.isAxiosError(err)
          ? (err.response?.data?.detail as string | undefined) ?? 'Ошибка сервера'
          : 'Неизвестная ошибка';
      setActionError(detail);
      setConfirmAction(null);
    }
  };

  /* --- render --- */
  return (
    <div className="admin-page">

      {/* Header */}
      <div className="ab-header">
        <h1>Бронирования</h1>
        <div className="ab-header-actions">
          <button className="btn fp-btn-secondary" onClick={() => setFilterDate(todayISO())}>
            Сегодня
          </button>
          <button
            className="btn fp-btn-secondary"
            aria-label="Обновить список бронирований"
            onClick={() => refetch()}
            disabled={isLoading || isActionPending}
          >
            ↻ Обновить
          </button>
        </div>
      </div>

      {/* Stats row */}
      <div className="ab-stats">
        <div className="ab-stat ab-stat-pending">
          <span className="ab-stat-num">{stats.pending}</span>
          <span className="ab-stat-label">Ожидают</span>
        </div>
        <div className="ab-stat ab-stat-confirmed">
          <span className="ab-stat-num">{stats.confirmed}</span>
          <span className="ab-stat-label">Подтверждены</span>
        </div>
        <div className="ab-stat ab-stat-total">
          <span className="ab-stat-num">{stats.total}</span>
          <span className="ab-stat-label">Всего загружено</span>
        </div>
      </div>

      {/* Filters */}
      <div className="tc-filters">
        <div className="tc-filter-item ab-filter-date">
          <label>
            Дата
            <input
              type="date"
              value={filterDate}
              onChange={(e) => setFilterDate(e.target.value)}
            />
          </label>
          {filterDate && (
            <button
              className="ab-clear-btn"
              onClick={() => setFilterDate('')}
              title="Сбросить дату"
            >
              ×
            </button>
          )}
        </div>

        <div className="tc-filter-item">
          <label>
            Статус
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value as BookingStatus | '')}
            >
              <option value="">Все статусы</option>
              {ALL_STATUSES.map((s) => (
                <option key={s} value={s}>{STATUS_LABEL[s]}</option>
              ))}
            </select>
          </label>
        </div>

        <div className="tc-filter-item">
          <label>
            Гость
            <input
              type="text"
              placeholder="Поиск по имени"
              value={filterName}
              onChange={(e) => setFilterName(e.target.value)}
            />
          </label>
        </div>
      </div>

      {/* Loading / error */}
      {isLoading && <p className="info-muted">Загрузка бронирований...</p>}
      {isError && (
        <p className="error">Не удалось загрузить бронирования. Проверьте авторизацию.</p>
      )}
      {actionError && (
        <p className="error ab-action-error">
          Ошибка действия: {actionError}
          <button className="ab-clear-btn" onClick={() => setActionError(null)} title="Закрыть">
            {' '}×
          </button>
        </p>
      )}
      {isActionPending && <p className="info-muted ab-action-spinner">Выполняется действие...</p>}

      {/* Table */}
      {bookings && (
        <div className="tc-table-wrap">
          <table className="tc-table ab-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Гость</th>
                <th>Телефон</th>
                <th>Стол</th>
                <th>Дата</th>
                <th>Время</th>
                <th>Гостей</th>
                <th>Статус</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={9} className="tc-empty">
                    Бронирований не найдено
                  </td>
                </tr>
              )}
              {filtered.map((b) => (
                <tr key={b.id} className={b.status === 'pending' ? 'ab-row-pending' : ''}>
                  <td className="ab-id">#{b.id}</td>
                  <td>
                    <span className="ab-guest-name">{b.guest_name}</span>
                    {b.notes && (
                      <span className="ab-notes-icon" title={b.notes} aria-label="Есть примечание">
                        {' '}💬
                      </span>
                    )}
                  </td>
                  <td className="ab-phone">{b.guest_phone_masked}</td>
                  <td className="ab-table-num">#{b.table_id}</td>
                  <td>{formatDate(b.date)}</td>
                  <td className="ab-time">
                    {formatTime(b.time_from)}–{formatTime(b.time_to)}
                  </td>
                  <td className="ab-guests">{b.guest_count}</td>
                  <td>
                    <span className={STATUS_CLASS[b.status]}>
                      {STATUS_LABEL[b.status]}
                    </span>
                  </td>
                  <td className="ab-actions">
                    {b.status === 'pending' && (
                      <>
                        <button
                          className="ab-btn ab-btn-confirm"
                          disabled={isActionPending}
                          onClick={() =>
                            setConfirmAction({ id: b.id, action: 'confirm', name: b.guest_name })
                          }
                        >
                          Подтвердить
                        </button>
                        <button
                          className="ab-btn ab-btn-reject"
                          disabled={isActionPending}
                          onClick={() =>
                            setConfirmAction({ id: b.id, action: 'reject', name: b.guest_name })
                          }
                        >
                          Отклонить
                        </button>
                      </>
                    )}
                    {b.status === 'confirmed' && (
                      <>
                        <button
                          className="ab-btn ab-btn-complete"
                          disabled={isActionPending}
                          onClick={() =>
                            setConfirmAction({ id: b.id, action: 'complete', name: b.guest_name })
                          }
                        >
                          Завершить
                        </button>
                        <button
                          className="ab-btn ab-btn-reject"
                          disabled={isActionPending}
                          onClick={() =>
                            setConfirmAction({ id: b.id, action: 'reject', name: b.guest_name })
                          }
                        >
                          Отклонить
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="info-muted tc-count">
            Показано: {filtered.length} из {bookings.length}
          </p>
        </div>
      )}

      {/* Action confirmation modal */}
      {confirmAction && (
        <div
          className="tc-modal-overlay"
          onClick={closeModal}
          aria-hidden="true"
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="ab-modal-title"
            className="tc-modal tc-modal-sm"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 id="ab-modal-title">
              {confirmAction.action === 'confirm' && 'Подтвердить бронирование?'}
              {confirmAction.action === 'complete' && 'Завершить бронирование?'}
              {confirmAction.action === 'reject'   && 'Отклонить бронирование?'}
            </h2>
            <p className="info-muted">
              Гость: <strong>{confirmAction.name}</strong> (#{confirmAction.id})
            </p>
            <div className="tc-modal-actions">
              <button
                className={`btn ${
                  confirmAction.action === 'reject' ? 'fp-btn-danger' : 'btn-primary'
                }`}
                onClick={handleAction}
                disabled={isActionPending}
                autoFocus
              >
                {confirmAction.action === 'confirm' && 'Подтвердить'}
                {confirmAction.action === 'complete' && 'Завершить'}
                {confirmAction.action === 'reject'   && 'Отклонить'}
              </button>
              <button
                className="btn fp-btn-secondary"
                onClick={closeModal}
              >
                Отмена
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
