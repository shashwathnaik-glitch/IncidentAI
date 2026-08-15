import React from 'react';

/**
 * Reusable Table Component for incident history, users, metrics, etc.
 */
export const Table = ({
  columns = [],
  data = [],
  keyExtractor,
  emptyMessage = 'No data available',
  className = ''
}) => {
  return (
    <div className={`overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-xl ${className}`}>
      <table className="w-full text-left text-xs text-slate-300">
        <thead className="bg-slate-950/80 text-slate-400 uppercase font-semibold text-[10px] tracking-wider border-b border-slate-800">
          <tr>
            {columns.map((col, idx) => (
              <th
                key={col.key || idx}
                className={`p-3.5 ${col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left'} ${col.headerClassName || ''}`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/60">
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="p-8 text-center text-slate-500 text-xs">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, rowIdx) => {
              const key = keyExtractor ? keyExtractor(row, rowIdx) : row.id || rowIdx;
              return (
                <tr key={key} className="hover:bg-slate-950/40 transition-colors">
                  {columns.map((col, colIdx) => (
                    <td
                      key={col.key || colIdx}
                      className={`p-3.5 ${col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left'} ${col.cellClassName || ''}`}
                    >
                      {col.render ? col.render(row, rowIdx) : row[col.accessor]}
                    </td>
                  ))}
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
};
