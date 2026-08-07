import { useState } from 'react';

export default function Table({
  columns,
  data = [],
  loading = false,
  emptyMessage = 'Aucune donnée disponible',
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
              <svg
                className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
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

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                {columns.map((col) => (
                  <th
                    key={col.key}
                    className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-600"
                    style={{ width: col.width }}
                  >
                    {col.header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={columns.length} className="px-4 py-12 text-center">
                    <div className="inline-flex items-center gap-2 text-sm text-slate-500">
                      <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary-200 border-t-primary-600" />
                      Chargement...
                    </div>
                  </td>
                </tr>
              ) : data.length === 0 ? (
                <tr>
                  <td colSpan={columns.length} className="px-4 py-12 text-center text-sm text-slate-500">
                    {emptyMessage}
                  </td>
                </tr>
              ) : (
                data.map((row) => (
                  <tr
                    key={row[keyField]}
                    onClick={() => onRowClick?.(row)}
                    className={`transition-colors ${onRowClick ? 'cursor-pointer hover:bg-slate-50' : ''}`}
                  >
                    {columns.map((col) => (
                      <td key={col.key} className="whitespace-nowrap px-4 py-3 text-sm text-slate-700">
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
          <div className="flex flex-col items-center justify-between gap-3 border-t border-slate-200 px-4 py-3 sm:flex-row">
            <p className="text-sm text-slate-600">
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
              <span className="text-sm text-slate-600">
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
