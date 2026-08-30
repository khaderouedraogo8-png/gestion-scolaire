import { useState } from 'react';
import { Inbox, Search } from 'lucide-react';
import EmptyState from './EmptyState';

export default function Table({
  columns,
  data = [],
  loading = false,
  emptyMessage = "Aucune donnée pour l'instant",
  emptyIcon = Inbox,
  searchable = false,
  searchPlaceholder = 'Rechercher...',
  onSearch,
  filters = null,
  pagination = null,
  onRowClick,
  keyField = 'id',
}) {
  const [localSearch, setLocalSearch] = useState('');

  const handleSearchChange = (e) => {
    const value = e.target.value;
    setLocalSearch(value);
    onSearch?.(value);
  };

  return (
    <div className="space-y-4">
      {(searchable || filters) && (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          {searchable && (
            <div className="relative max-w-sm flex-1">
              <Search
                className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-texte-secondaire"
                strokeWidth={1.75}
              />
              <input
                type="search"
                value={localSearch}
                onChange={handleSearchChange}
                placeholder={searchPlaceholder}
                className="input pl-9"
              />
            </div>
          )}
          {filters && <div className="flex flex-wrap gap-2">{filters}</div>}
        </div>
      )}

      <div className="overflow-hidden rounded-card border border-bordure bg-blanc">
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="border-b border-bordure/60 bg-craie/40">
                {columns.map((col) => (
                  <th
                    key={col.key}
                    className={`px-4 py-3 text-left text-[11px] font-medium uppercase tracking-[0.03em] text-texte-secondaire ${
                      col.align === 'right' ? 'text-right' : ''
                    }`}
                    style={{ width: col.width }}
                  >
                    {col.header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={columns.length} className="px-4 py-12 text-center">
                    <div className="inline-flex items-center gap-2 text-sm text-texte-secondaire">
                      <div className="loading-ring h-5 w-5" />
                      Chargement...
                    </div>
                  </td>
                </tr>
              ) : data.length === 0 ? (
                <tr>
                  <td colSpan={columns.length} className="p-4">
                    <EmptyState icon={emptyIcon} message={emptyMessage} />
                  </td>
                </tr>
              ) : (
                data.map((row) => (
                  <tr
                    key={row[keyField]}
                    onClick={() => onRowClick?.(row)}
                    className={`border-b border-bordure/50 last:border-b-0 transition-colors ${
                      onRowClick ? 'cursor-pointer hover:bg-craie/60' : ''
                    }`}
                  >
                    {columns.map((col) => (
                      <td
                        key={col.key}
                        className={`whitespace-nowrap px-4 py-3 text-sm text-encre ${
                          col.align === 'right' ? 'text-right tabular-nums' : ''
                        }`}
                      >
                        {col.render ? col.render(row) : row[col.key]}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {pagination && (
          <div className="flex flex-col items-center justify-between gap-3 border-t border-bordure px-4 py-3 sm:flex-row">
            <p className="text-sm text-texte-secondaire">
              {pagination.total > 0
                ? `${(pagination.page - 1) * pagination.perPage + 1}–${Math.min(
                    pagination.page * pagination.perPage,
                    pagination.total
                  )} sur ${pagination.total}`
                : '0 résultat'}
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={pagination.page <= 1}
                onClick={() => pagination.onPageChange(pagination.page - 1)}
                className="btn-secondary px-3 py-1.5 text-xs"
              >
                Précédent
              </button>
              <span className="text-sm text-texte-secondaire">
                Page {pagination.page} / {pagination.totalPages || 1}
              </span>
              <button
                type="button"
                disabled={pagination.page >= (pagination.totalPages || 1)}
                onClick={() => pagination.onPageChange(pagination.page + 1)}
                className="btn-secondary px-3 py-1.5 text-xs"
              >
                Suivant
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
