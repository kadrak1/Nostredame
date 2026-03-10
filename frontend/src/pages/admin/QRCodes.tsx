/**
 * QRCodes — страница QR-кодов столов (T-065).
 *
 * Маршрут: /admin/qr-codes
 *
 * Возможности:
 *  - Список активных столов
 *  - Скачать QR-код отдельного стола (PNG, /api/tables/{id}/qr)
 *  - Скачать все QR-коды (ZIP, /api/tables/qr-all)
 *  - Просмотр QR в модальном окне
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../../api/client';

/* ── Types ──────────────────────────────────────────────────────────── */

interface TableData {
  id: number;
  venue_id: number;
  number: number;
  capacity: number;
  shape: string;
  is_active: boolean;
}

/* ── Helpers ─────────────────────────────────────────────────────────── */

/** Скачать blob как файл через временный <a> */
function triggerBlobDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  // Revoke after a short delay so the browser has time to start the download
  setTimeout(() => URL.revokeObjectURL(url), 5_000);
}

/* ── Component ───────────────────────────────────────────────────────── */

export default function QRCodes() {
  const [previewTable, setPreviewTable] = useState<TableData | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<number | 'all' | null>(null);
  /** Флаг загрузки превью — защита от параллельных запросов и утечки blob URL */
  const [previewLoading, setPreviewLoading] = useState(false);

  /* --- data --- */
  const { data: tables, isLoading, isError } = useQuery({
    queryKey: ['tables'],
    queryFn: () => api.get<TableData[]>('/tables').then((r) => r.data),
  });

  const activeTables = (tables ?? [])
    .filter((t) => t.is_active)
    .sort((a, b) => a.number - b.number);

  /* --- actions --- */

  async function downloadQR(table: TableData): Promise<void> {
    if (downloadingId !== null) return;
    setDownloadingId(table.id);
    try {
      const response = await api.get<Blob>(`/tables/${table.id}/qr`, {
        params: { size: 300 },
        responseType: 'blob',
      });
      triggerBlobDownload(response.data, `table_${table.number}.png`);
    } catch {
      // Silently ignore — user sees no change, can retry
    } finally {
      setDownloadingId(null);
    }
  }

  async function downloadAll(): Promise<void> {
    if (downloadingId !== null) return;
    setDownloadingId('all');
    try {
      const response = await api.get<Blob>('/tables/qr-all', {
        responseType: 'blob',
      });
      triggerBlobDownload(response.data, 'qr-codes.zip');
    } catch {
      // Silently ignore
    } finally {
      setDownloadingId(null);
    }
  }

  async function openPreview(table: TableData): Promise<void> {
    // HIGH-3: guard against parallel requests — second click would leak the first blob URL
    if (previewLoading) return;
    setPreviewLoading(true);
    try {
      const response = await api.get(`/tables/${table.id}/qr`, {
        params: { size: 300 },
        responseType: 'blob',
      });
      const url = URL.createObjectURL(response.data as Blob);
      setPreviewUrl(url);
      setPreviewTable(table);
    } catch {
      // Ignore — preview simply won't open
    } finally {
      setPreviewLoading(false);
    }
  }

  function closePreview(): void {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setPreviewUrl(null);
    setPreviewTable(null);
  }

  /* --- render --- */
  return (
    <div className="admin-page">
      {/* Header */}
      <div className="tc-header">
        <h1>QR-коды столов</h1>
        <button
          className="btn btn-primary"
          onClick={() => void downloadAll()}
          disabled={downloadingId === 'all' || activeTables.length === 0}
        >
          {downloadingId === 'all' ? 'Скачивание…' : '⬇ Скачать все (ZIP)'}
        </button>
      </div>

      {/* States */}
      {isLoading && <p className="info-muted">Загрузка столов…</p>}
      {isError && <p className="error">Не удалось загрузить список столов</p>}

      {/* Table */}
      {tables && (
        <div className="tc-table-wrap">
          <table className="tc-table">
            <thead>
              <tr>
                <th>Стол</th>
                <th>Вместимость</th>
                <th>QR-ссылка</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {activeTables.length === 0 && (
                <tr>
                  <td colSpan={4} className="tc-empty">Активных столов нет</td>
                </tr>
              )}
              {activeTables.map((t) => (
                <tr key={t.id}>
                  <td>
                    <span className="qr-table-num">№{t.number}</span>
                  </td>
                  <td>{t.capacity} чел.</td>
                  <td>
                    <span className="qr-url-hint">/table/{t.id}</span>
                  </td>
                  <td className="tc-actions">
                    <button
                      className="tc-btn-edit"
                      onClick={() => void openPreview(t)}
                      disabled={previewLoading}
                      title="Открыть QR в модальном окне"
                    >
                      {previewLoading ? '…' : 'Просмотр'}
                    </button>
                    <button
                      className="btn btn-primary qr-btn-dl"
                      onClick={() => void downloadQR(t)}
                      disabled={downloadingId === t.id}
                      title={`Скачать QR для стола №${t.number}`}
                    >
                      {downloadingId === t.id ? '…' : '⬇ QR'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="info-muted tc-count">
            Активных столов: {activeTables.length}
          </p>
        </div>
      )}

      {/* Preview Modal */}
      {previewTable !== null && previewUrl !== null && (
        <div className="tc-modal-overlay" onClick={closePreview}>
          <div
            className="tc-modal qr-preview-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <h2>QR-код стола №{previewTable.number}</h2>
            <div className="qr-preview-img-wrap">
              <img
                src={previewUrl}
                alt={`QR-код стола №${previewTable.number}`}
                className="qr-preview-img"
              />
            </div>
            <p className="info-muted qr-preview-hint">
              Гость сканирует код → переходит на страницу заказа стола
            </p>
            <div className="tc-modal-actions">
              <button
                className="btn btn-primary"
                // HIGH-1: don't close without download; HIGH-2: disable during active download
                disabled={downloadingId !== null}
                onClick={() => {
                  if (downloadingId !== null) return;
                  void downloadQR(previewTable);
                  closePreview();
                }}
              >
                {downloadingId !== null ? '…' : '⬇ Скачать PNG'}
              </button>
              <button className="btn fp-btn-secondary" onClick={closePreview}>
                Закрыть
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
