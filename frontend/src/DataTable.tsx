import React, { useMemo } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getPaginationRowModel,
  flexRender,
  createColumnHelper,
  SortingState,
  PaginationState,
} from '@tanstack/react-table';

interface DataTableProps {
  data: any[];
  title?: string;
}

const DataTable: React.FC<DataTableProps> = ({ data, title }) => {
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const [pagination, setPagination] = React.useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  });

  // Generate columns dynamically based on data structure
  const columns = useMemo(() => {
    if (!data || data.length === 0) return [];

    const columnHelper = createColumnHelper<any>();
    const firstRow = data[0];
    const keys = Object.keys(firstRow);

    return keys.map(key => {
      return columnHelper.accessor(key, {
        header: () => {
          // Format header text
          const header = key
            .replace(/([a-z])([A-Z])/g, '$1 $2')
            .replace(/_/g, ' ')
            .trim();
          return header.charAt(0).toUpperCase() + header.slice(1);
        },
        cell: (info) => {
          const value = info.getValue();
          
          // Handle null/undefined
          if (value === null || value === undefined) {
            return <span style={{ color: '#999' }}>N/A</span>;
          }

          // Handle URLs (including datasheet links)
          if (typeof value === 'string' && (value.startsWith('http://') || value.startsWith('https://'))) {
            const isDatasheet = key.toLowerCase().includes('datasheet') || value.toLowerCase().includes('datasheet');
            return (
              <a 
                href={value} 
                target="_blank" 
                rel="noopener noreferrer"
                style={{ color: '#0066cc', textDecoration: 'none' }}
              >
                {isDatasheet ? '📄 Datasheet' : '🔗 Link'}
              </a>
            );
          }

          // Handle long strings
          if (typeof value === 'string' && value.length > 100) {
            return (
              <span title={value}>
                {value.substring(0, 100)}...
              </span>
            );
          }

          // Handle arrays
          if (Array.isArray(value)) {
            return <span>{value.join(', ')}</span>;
          }

          // Handle objects
          if (typeof value === 'object') {
            return <span>{JSON.stringify(value)}</span>;
          }

          return <span>{String(value)}</span>;
        },
      });
    });
  }, [data]);

  const table = useReactTable({
    data,
    columns,
    state: {
      sorting,
      pagination,
    },
    onSortingChange: setSorting,
    onPaginationChange: setPagination,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  });

  if (!data || data.length === 0) {
    return <div>No data available</div>;
  }

  return (
    <div style={{ padding: '10px', backgroundColor: '#f8f9fa', borderRadius: '8px', marginTop: '10px' }}>
      {title && (
        <h4 style={{ margin: '0 0 10px 0', color: '#333', fontSize: '16px', fontWeight: 600 }}>
          {title}
        </h4>
      )}
      
      <div style={{ overflowX: 'auto', backgroundColor: 'white', borderRadius: '4px', border: '1px solid #ddd' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            {table.getHeaderGroups().map(headerGroup => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map(header => (
                  <th
                    key={header.id}
                    onClick={header.column.getToggleSortingHandler()}
                    style={{
                      padding: '10px',
                      textAlign: 'left',
                      backgroundColor: '#f1f3f5',
                      borderBottom: '2px solid #dee2e6',
                      cursor: header.column.getCanSort() ? 'pointer' : 'default',
                      userSelect: 'none',
                      fontSize: '13px',
                      fontWeight: 600,
                      color: '#495057',
                    }}
                  >
                    {flexRender(header.column.columnDef.header, header.getContext())}
                    {header.column.getIsSorted() && (
                      <span style={{ marginLeft: '5px' }}>
                        {header.column.getIsSorted() === 'asc' ? '↑' : '↓'}
                      </span>
                    )}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map(row => (
              <tr key={row.id}>
                {row.getVisibleCells().map(cell => (
                  <td
                    key={cell.id}
                    style={{
                      padding: '10px',
                      borderBottom: '1px solid #dee2e6',
                      fontSize: '13px',
                      color: '#212529',
                    }}
                  >
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        marginTop: '10px',
        fontSize: '13px',
      }}>
        <div>
          Showing {table.getState().pagination.pageIndex * table.getState().pagination.pageSize + 1} to{' '}
          {Math.min(
            (table.getState().pagination.pageIndex + 1) * table.getState().pagination.pageSize,
            data.length
          )}{' '}
          of {data.length} entries
        </div>
        
        <div style={{ display: 'flex', gap: '5px', alignItems: 'center' }}>
          <button
            onClick={() => table.setPageIndex(0)}
            disabled={!table.getCanPreviousPage()}
            style={{
              padding: '5px 10px',
              border: '1px solid #dee2e6',
              backgroundColor: 'white',
              borderRadius: '4px',
              cursor: table.getCanPreviousPage() ? 'pointer' : 'not-allowed',
              opacity: table.getCanPreviousPage() ? 1 : 0.5,
            }}
          >
            {'<<'}
          </button>
          <button
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            style={{
              padding: '5px 10px',
              border: '1px solid #dee2e6',
              backgroundColor: 'white',
              borderRadius: '4px',
              cursor: table.getCanPreviousPage() ? 'pointer' : 'not-allowed',
              opacity: table.getCanPreviousPage() ? 1 : 0.5,
            }}
          >
            {'<'}
          </button>
          <span style={{ padding: '0 10px' }}>
            Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}
          </span>
          <button
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            style={{
              padding: '5px 10px',
              border: '1px solid #dee2e6',
              backgroundColor: 'white',
              borderRadius: '4px',
              cursor: table.getCanNextPage() ? 'pointer' : 'not-allowed',
              opacity: table.getCanNextPage() ? 1 : 0.5,
            }}
          >
            {'>'}
          </button>
          <button
            onClick={() => table.setPageIndex(table.getPageCount() - 1)}
            disabled={!table.getCanNextPage()}
            style={{
              padding: '5px 10px',
              border: '1px solid #dee2e6',
              backgroundColor: 'white',
              borderRadius: '4px',
              cursor: table.getCanNextPage() ? 'pointer' : 'not-allowed',
              opacity: table.getCanNextPage() ? 1 : 0.5,
            }}
          >
            {'>>'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default DataTable;