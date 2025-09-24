import React, { useMemo, useCallback } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  flexRender,
  createColumnHelper,
  SortingState,
  ColumnFiltersState,
  PaginationState,
  ColumnResizeMode,
} from '@tanstack/react-table';
import './TanStackDataTable.css';

interface TanStackDataTableProps {
  data: any;
  userQuery?: string;
  toolName?: string;
  title?: string;
  isPartDetailsSection?: boolean;
}

const TanStackDataTable: React.FC<TanStackDataTableProps> = ({
  data,
  userQuery,
  toolName,
  title,
  isPartDetailsSection = false,
}) => {
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([]);
  const [globalFilter, setGlobalFilter] = React.useState('');
  const [columnResizeMode] = React.useState<ColumnResizeMode>('onChange');
  const [showExportMenu, setShowExportMenu] = React.useState(false);

  // Close menus when clicking outside
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (!target.closest('.export-container')) {
        setShowExportMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const [pagination, setPagination] = React.useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  });

  // Generate title based on tool name and context
  const generateTableTitle = (toolName?: string, userQuery?: string, title?: string) => {
    if (title) return title;

    if (toolName) {
      switch (toolName.toLowerCase()) {
        case 'part_details':
          return 'Part Details';
        case 'market_availability':
          return 'Market Availability & Pricing';
        case 'part_search':
          return 'Part Search Results';
        case 'cross_references':
          return 'Cross References & Alternatives';
        case 'supply_chain_locations':
          return 'Supply Chain Locations';
        default:
          return toolName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      }
    }

    return 'Data Results';
  };

  // Extract and structure data
  const processedData = useMemo(() => {
    if (!data) return [];

    // If it's already an array of objects, return it
    if (Array.isArray(data)) {
      return data.filter((item: any) => item && typeof item === 'object');
    }

    // If it's a single object, check if it has arrays that should be the main table
    if (typeof data === 'object') {
      // Look for arrays in top-level properties
      const arrayProperties = Object.entries(data).filter(([key, value]) =>
        Array.isArray(value) && value.length > 0 && typeof value[0] === 'object'
      );

      if (arrayProperties.length > 0) {
        const [, arrayData] = arrayProperties[0];
        return arrayData as any[];
      }

      // If no arrays found, treat as a single record
      return [data];
    }

    return [];
  }, [data]);

  // Generate columns dynamically based on data structure
  const columns = useMemo(() => {
    if (!processedData.length) return [];

    const columnHelper = createColumnHelper<any>();
    const allKeys = new Set<string>();

    // Collect all unique keys from all objects
    processedData.forEach((item: any) => {
      Object.keys(item).forEach((key: string) => {
        // Filter out Part ID columns for part search results
        if (key.toLowerCase() !== 'partid' && key.toLowerCase() !== 'part id') {
          allKeys.add(key);
        }
      });
    });

    // Convert to array and create columns
    const columnList = Array.from(allKeys).map(key => {
      // Determine smart column width based on column name and data type
      const getColumnWidth = () => {
        const keyLower = key.toLowerCase();

        // For part details sections, use fixed widths for Field and Value columns
        if (isPartDetailsSection) {
          if (keyLower === 'field') {
            return 200; // Fixed width for Field column
          }
          if (keyLower === 'value') {
            return 400; // Fixed width for Value column
          }
        }

        // Very narrow columns for IDs, counts, quantities
        if (keyLower.includes('id') ||
            keyLower === 'qty' ||
            keyLower === 'quantity' ||
            keyLower === 'count' ||
            keyLower === 'rank' ||
            keyLower === 'score') {
          return 80;
        }

        // Narrow columns for numeric values, prices, percentages
        if (keyLower.includes('price') ||
            keyLower.includes('cost') ||
            keyLower.includes('percent') ||
            keyLower.includes('rating') ||
            keyLower.includes('stock') ||
            keyLower === 'lead time' ||
            keyLower === 'leadtime' ||
            keyLower === 'moq') {
          return 100;
        }

        // Medium columns for dates, status, short text
        if (keyLower.includes('date') ||
            keyLower.includes('status') ||
            keyLower.includes('state') ||
            keyLower.includes('type') ||
            keyLower.includes('category') ||
            keyLower === 'supplier') {
          return 150;
        }

        // Wider for manufacturer and part number
        if (keyLower === 'manufacturer' ||
            keyLower === 'part number' ||
            keyLower === 'partnumber' ||
            keyLower === 'mpn') {
          return 200;
        }

        // Wide columns for descriptions, long text
        if (keyLower.includes('description') ||
            keyLower.includes('address') ||
            keyLower.includes('comment') ||
            keyLower.includes('note')) {
          return 300;
        }

        // Narrow columns for URLs and datasheet links
        if (keyLower.includes('datasheet') ||
            keyLower.includes('url') ||
            keyLower.includes('link') ||
            keyLower.includes('path')) {
          return 100;
        }

        // Check actual data for smart sizing
        const sampleValues = processedData.slice(0, 10).map((row: any) => {
          const val = row[key];
          if (val === null || val === undefined) return 0;
          if (typeof val === 'number') return String(val).length;
          if (typeof val === 'string') return val.length;
          if (Array.isArray(val)) return 20;
          return 10;
        });

        const avgLength = sampleValues.reduce((a, b) => a + b, 0) / sampleValues.length;

        // Based on average content length
        if (avgLength < 5) return 80;
        if (avgLength < 10) return 120;
        if (avgLength < 20) return 150;
        if (avgLength < 40) return 200;
        return 250;
      };

      // Handle special 'View in Tool' column
      if (key === '__view_in_tool__') {
        return columnHelper.accessor(
          (row) => row,
          {
            id: 'view_in_tool',
            header: () => 'View in Tool',
            cell: () => (
              <a
                href="https://login.z2data.com"
                target="_blank"
                rel="noopener noreferrer"
                className="view-tool-link"
                title="View in Z2Data Tool"
              >
                <img
                  src="https://app.z2data.com/assets/img/Part-Risk-Manager_Transparency.png"
                  alt="Z2Data"
                  className="z2data-icon"
                />
              </a>
            ),
            size: 80,
            enableSorting: false,
            enableResizing: false,
          }
        );
      }

      return columnHelper.accessor(key, {
        header: () => {
          // Fix letter spacing issues by properly handling camelCase and special cases
          let header = key
            .replace(/([a-z])([A-Z])/g, '$1 $2')  // camelCase -> camel Case
            .replace(/([A-Z])([A-Z][a-z])/g, '$1 $2')  // XMLHttpRequest -> XML Http Request
            .replace(/ID/g, 'ID')  // Keep ID together
            .replace(/MPN/g, 'MPN')  // Keep MPN together
            .replace(/URL/g, 'URL')  // Keep URL together
            .replace(/API/g, 'API')  // Keep API together
            .trim();

          // Capitalize first letter
          return header.charAt(0).toUpperCase() + header.slice(1);
        },
        cell: (info) => {
          const value = info.getValue();

          // Handle null/undefined
          if (value === null || value === undefined) {
            return <span className="null-value">N/A</span>;
          }

          // Handle arrays
          if (Array.isArray(value)) {
            if (value.length === 0) return <span className="empty-array">Empty</span>;

            // For arrays of primitives, show as comma-separated
            if (value.every(item => typeof item !== 'object' || item === null)) {
              return (
                <span className="array-value">
                  {value.filter((item: any) => item !== null && item !== undefined).join(', ')}
                </span>
              );
            }

            // For arrays of objects, show expandable details
            return (
              <details className="array-details">
                <summary className="array-summary">
                  {value.length} items
                </summary>
                <div className="array-content">
                  {value.map((item, index) => (
                    <div key={index} className="array-item">
                      {typeof item === 'object' && item !== null
                        ? Object.entries(item).map(([k, v]) => (
                            <div key={k} className="sub-item">
                              <strong>{k}:</strong> {String(v)}
                            </div>
                          ))
                        : String(item)
                      }
                    </div>
                  ))}
                </div>
              </details>
            );
          }

          // Handle objects
          if (typeof value === 'object') {
            return (
              <details className="object-details">
                <summary className="object-summary">
                  Object ({Object.keys(value).length} properties)
                </summary>
                <div className="object-content">
                  {Object.entries(value).map(([k, v]) => (
                    <div key={k} className="sub-item">
                      <strong>{k}:</strong> {String(v)}
                    </div>
                  ))}
                </div>
              </details>
            );
          }

          // Handle URLs with special formatting
          if (typeof value === 'string' && (value.startsWith('http://') || value.startsWith('https://'))) {
            const columnId = info.column.id.toLowerCase();

            const isDatasheet = columnId.includes('datasheet') ||
                              value.toLowerCase().includes('datasheet') ||
                              value.toLowerCase().includes('.pdf');

            // Handle datasheet URLs - show only PDF icon
            if (isDatasheet) {
              return (
                <a
                  href={value}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="document-link"
                  title="View Datasheet"
                >
                  <span className="document-icon">📄</span>
                </a>
              );
            }

            // Handle regular URLs
            return (
              <a href={value} target="_blank" rel="noopener noreferrer" className="url-link">
                {value.length > 40 ? `${value.substring(0, 40)}...` : value}
              </a>
            );
          }

          // Handle long strings
          if (typeof value === 'string' && value.length > 100) {
            return (
              <span className="cell-value" title={value}>
                {value.substring(0, 100)}...
              </span>
            );
          }

          // Handle boolean values
          if (typeof value === 'boolean') {
            return (
              <span className={`boolean-value ${value ? 'true' : 'false'}`}>
                {value ? 'Yes' : 'No'}
              </span>
            );
          }

          // Handle numeric values
          if (typeof value === 'number') {
            const numStr = value.toLocaleString();
            return <span className="numeric-value">{numStr}</span>;
          }

          // Handle regular string values
          const stringValue = String(value);
          return <span className="cell-value">{stringValue}</span>;
        },
        sortingFn: 'alphanumeric',
        filterFn: 'includesString',
        size: getColumnWidth(),
        minSize: 80,
        maxSize: 500,
        enableResizing: true,
      });
    });

    // Add 'View in Tool' column for part search results at the end
    if (toolName?.toLowerCase() === 'part_search') {
      columnList.push(
        columnHelper.accessor(
          (row) => row,
          {
            id: 'view_in_tool',
            header: () => 'View in Tool',
            cell: () => (
              <a
                href="https://login.z2data.com"
                target="_blank"
                rel="noopener noreferrer"
                className="view-tool-link"
                title="View in Z2Data Tool"
              >
                <img
                  src="https://app.z2data.com/assets/img/Part-Risk-Manager_Transparency.png"
                  alt="Z2Data"
                  className="z2data-icon"
                />
              </a>
            ),
            size: 80,
            enableSorting: false,
            enableResizing: false,
          }
        )
      );
    }

    return columnList;
  }, [processedData, toolName]);

  const table = useReactTable({
    data: processedData,
    columns,
    state: {
      sorting,
      columnFilters,
      globalFilter,
      pagination,
    },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    onPaginationChange: setPagination,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    columnResizeMode,
    enableColumnResizing: true,
    debugTable: false,
  });

  const tableTitle = generateTableTitle(toolName, userQuery, title);

  // Export functions
  const exportToCSV = useCallback(() => {
    const rows = table.getFilteredRowModel().rows;
    const headers = columns.map(col => {
      const header = col.header;
      return typeof header === 'function' ? col.id : header;
    });

    const csvContent = [
      headers.join(','),
      ...rows.map(row =>
        row.getVisibleCells().map(cell => {
          const value = cell.getValue();
          const stringValue = value === null || value === undefined ? '' : String(value);
          // Escape quotes and wrap in quotes if contains comma or newline
          if (stringValue.includes(',') || stringValue.includes('\n') || stringValue.includes('"')) {
            return `"${stringValue.replace(/"/g, '""')}"`;
          }
          return stringValue;
        }).join(',')
      )
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${tableTitle || 'data'}_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    setShowExportMenu(false);
  }, [table, columns, tableTitle]);

  const exportToExcel = useCallback(() => {
    // Create a simple HTML table for Excel
    const rows = table.getFilteredRowModel().rows;
    const headers = columns.map(col => {
      const header = col.header;
      return typeof header === 'function' ? col.id : header;
    });

    let html = '<table border="1"><thead><tr>';
    headers.forEach(header => {
      html += `<th>${header}</th>`;
    });
    html += '</tr></thead><tbody>';

    rows.forEach(row => {
      html += '<tr>';
      row.getVisibleCells().forEach(cell => {
        const value = cell.getValue();
        const displayValue = value === null || value === undefined ? '' : String(value);
        html += `<td>${displayValue}</td>`;
      });
      html += '</tr>';
    });
    html += '</tbody></table>';

    const blob = new Blob([html], { type: 'application/vnd.ms-excel' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${tableTitle || 'data'}_${new Date().toISOString().slice(0, 10)}.xls`;
    link.click();
    setShowExportMenu(false);
  }, [table, columns, tableTitle]);

  if (!processedData.length) {
    return (
      <div className="tanstack-table-container">
        <div className="table-header">
          <h4 className="table-title">{generateTableTitle(toolName, userQuery, title)}</h4>
        </div>
        <div className="no-data">
          No tabular data available to display.
        </div>
      </div>
    );
  }

  return (
    <div className="tanstack-table-container">
      {/* Header with title and controls */}
      {!isPartDetailsSection && (
        <>
          <div className="table-header">
            <h4 className="table-title">{tableTitle}</h4>
            <div className="table-stats">
              {`${table.getRowModel().rows.length} of ${processedData.length} rows`}
            </div>
          </div>

          <div className="table-controls">
            <div className="search-box">
              <input
                type="text"
                placeholder="Search all columns..."
                value={globalFilter}
                onChange={(e) => setGlobalFilter(e.target.value)}
                className="global-filter"
              />
            </div>
            <div className="export-container">
              <button
                className="export-button"
                onClick={() => setShowExportMenu(!showExportMenu)}
              >
                <span className="export-icon">⬇</span>
                Export
              </button>
              {showExportMenu && (
                <div className="export-dropdown">
                  <button className="export-option" onClick={exportToCSV}>
                    Export as CSV
                  </button>
                  <button className="export-option" onClick={exportToExcel}>
                    Export as XLS
                  </button>
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* No title shown for part details sections */}

      {/* Table */}
      <div className="table-wrapper">
        <table className={`tanstack-table ${isPartDetailsSection ? 'part-details-table' : ''}`}>
          <thead className={isPartDetailsSection ? 'hidden-header' : ''}>
            {table.getHeaderGroups().map(headerGroup => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map(header => (
                  <th
                    key={header.id}
                    className={`table-header-cell ${header.column.getCanSort() ? 'sortable' : ''}`}
                    style={{
                      width: header.getSize(),
                      position: 'relative',
                    }}
                  >
                    {header.isPlaceholder ? null : (
                      <>
                        <div className="header-content" onClick={header.column.getToggleSortingHandler()}>
                          <span>
                            {flexRender(header.column.columnDef.header, header.getContext())}
                          </span>
                          {header.column.getCanSort() && (
                            <span className="sort-indicator">
                              {{
                                asc: ' ↑',
                                desc: ' ↓',
                              }[header.column.getIsSorted() as string] ?? ''}
                            </span>
                          )}
                        </div>
                        <div
                          onMouseDown={header.getResizeHandler()}
                          onTouchStart={header.getResizeHandler()}
                          className={`column-resizer ${
                            header.column.getIsResizing() ? 'isResizing' : ''
                          }`}
                        />
                      </>
                    )}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map(row => (
              <tr key={row.id} className="table-row">
                {row.getVisibleCells().map(cell => (
                  <td
                    key={cell.id}
                    className="table-cell"
                    style={{
                      width: cell.column.getSize(),
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

      {/* Pagination Controls */}
      {!isPartDetailsSection && (
      <div className="table-pagination">
        <div className="page-size-selector">
          Show
          <select
            className="page-size-select"
            value={table.getState().pagination.pageSize}
            onChange={(e) => table.setPageSize(Number(e.target.value))}
          >
            <option value={5}>5</option>
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
          per page
        </div>
        <div className="pagination-controls">
          <button
            className="pagination-button"
            onClick={() => table.setPageIndex(0)}
            disabled={!table.getCanPreviousPage()}
          >
            {'<<'}
          </button>
          <button
            className="pagination-button"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
          >
            {'<'}
          </button>
          <span className="page-info">
            Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}
          </span>
          <button
            className="pagination-button"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
          >
            {'>'}
          </button>
          <button
            className="pagination-button"
            onClick={() => table.setPageIndex(table.getPageCount() - 1)}
            disabled={!table.getCanNextPage()}
          >
            {'>>'}
          </button>
        </div>
      </div>
      )}
    </div>
  );
};

export default TanStackDataTable;