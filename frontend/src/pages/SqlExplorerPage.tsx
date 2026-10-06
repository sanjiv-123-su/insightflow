import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { datasetService } from '../services/datasetService';
import { sqlService } from '../services/sqlService';
import { getErrorMessage } from '../services/api';
import type { Dataset, SqlQueryResponse, SavedQuery } from '../types';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorAlert } from '../components/common/ErrorAlert';
import {
  Play,
  Save,
  Trash2,
  Bookmark,
  Database,
  Terminal,
  ShieldCheck,
  Clock,
  Download,
  Search,
  ArrowLeft,
  FileSearch,
  CheckCircle,
} from 'lucide-react';

const QUICK_TEMPLATES = [
  {
    name: 'Preview All Rows',
    query: 'SELECT * FROM dataset LIMIT 25;',
  },
  {
    name: 'Summary Count & Aggregation',
    query: 'SELECT COUNT(*) AS total_rows FROM dataset;',
  },
  {
    name: 'Order By First Columns',
    query: 'SELECT * FROM dataset ORDER BY 1 DESC LIMIT 50;',
  },
];

export const SqlExplorerPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [loadingDataset, setLoadingDataset] = useState(true);
  const [datasetError, setDatasetError] = useState<string | null>(null);

  // Query editor state
  const [query, setQuery] = useState('SELECT * FROM dataset LIMIT 50;');
  const [limit, setLimit] = useState<number>(500);
  const [isExecuting, setIsExecuting] = useState(false);
  const [queryResult, setQueryResult] = useState<SqlQueryResponse | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);

  // Saved queries state
  const [savedQueries, setSavedQueries] = useState<SavedQuery[]>([]);
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [saveQueryName, setSaveQueryName] = useState('');
  const [savingQuery, setSavingQuery] = useState(false);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);

  // Results search filter
  const [filterText, setFilterText] = useState('');

  // Load dataset and saved queries
  const loadInitialData = useCallback(async () => {
    if (!id) return;
    setLoadingDataset(true);
    setDatasetError(null);
    try {
      const [dsData, savedData] = await Promise.all([
        datasetService.getDatasetById(id),
        sqlService.getSavedQueries(id).catch(() => []),
      ]);
      setDataset(dsData);
      setSavedQueries(savedData);
    } catch (err) {
      setDatasetError(getErrorMessage(err));
    } finally {
      setLoadingDataset(false);
    }
  }, [id]);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // Execute SQL Query
  const handleExecuteQuery = async (customQuery?: string) => {
    if (!id) return;
    const queryToRun = (customQuery || query).trim();
    if (!queryToRun) {
      setQueryError('Please enter a SQL query to execute.');
      return;
    }

    setIsExecuting(true);
    setQueryError(null);
    try {
      const res = await sqlService.executeQuery(id, queryToRun, limit);
      setQueryResult(res);
    } catch (err) {
      setQueryError(getErrorMessage(err));
    } finally {
      setIsExecuting(false);
    }
  };

  // Keyboard shortcut Ctrl/Cmd + Enter to run query
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleExecuteQuery();
    }
  };

  // Handle Save Query
  const handleSaveQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !saveQueryName.trim() || !query.trim()) return;

    setSavingQuery(true);
    try {
      const saved = await sqlService.saveQuery(id, {
        name: saveQueryName.trim(),
        query: query.trim(),
      });
      setSavedQueries([saved, ...savedQueries]);
      setSaveModalOpen(false);
      setSaveQueryName('');
      setSaveSuccessMsg('Query saved successfully!');
      setTimeout(() => setSaveSuccessMsg(null), 3500);
    } catch (err) {
      setQueryError(getErrorMessage(err));
    } finally {
      setSavingQuery(false);
    }
  };

  // Handle Delete Saved Query
  const handleDeleteSavedQuery = async (queryId: string) => {
    if (!id) return;
    try {
      await sqlService.deleteSavedQuery(id, queryId);
      setSavedQueries(savedQueries.filter((q) => q.id !== queryId));
    } catch (err) {
      setQueryError(getErrorMessage(err));
    }
  };

  // Export Results as CSV
  const handleExportCsv = () => {
    if (!queryResult || queryResult.rows.length === 0) return;
    const cols = queryResult.columns;
    const csvRows = [cols.join(',')];

    for (const row of queryResult.rows) {
      const values = cols.map((col) => {
        const val = row[col];
        if (val === null || val === undefined) return '';
        const escaped = String(val).replace(/"/g, '""');
        return `"${escaped}"`;
      });
      csvRows.push(values.join(','));
    }

    const blob = new Blob([csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `query_results_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (loadingDataset) {
    return (
      <div className="flex justify-center items-center py-24">
        <LoadingSpinner size="lg" message="Loading SQL Explorer..." />
      </div>
    );
  }

  if (datasetError || !dataset) {
    return (
      <div className="space-y-4">
        <ErrorAlert
          title="Failed to Load Dataset"
          message={datasetError || 'Dataset not found.'}
        />
        <Link
          to="/datasets"
          className="inline-flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-700"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Datasets
        </Link>
      </div>
    );
  }

  // Filter rows based on search input
  const filteredRows = queryResult?.rows.filter((row) => {
    if (!filterText.trim()) return true;
    const searchLower = filterText.toLowerCase();
    return Object.values(row).some((val) =>
      String(val ?? '').toLowerCase().includes(searchLower)
    );
  }) || [];

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Top Breadcrumb & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Link to="/datasets" className="hover:text-slate-900 transition-colors">
              Datasets
            </Link>
            <span>/</span>
            <Link to={`/datasets/${dataset.id}`} className="hover:text-slate-900 transition-colors">
              {dataset.name}
            </Link>
            <span>/</span>
            <span className="text-slate-900 font-medium">SQL Explorer</span>
          </div>

          <div className="flex items-center gap-3 mt-1.5 flex-wrap">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
              <Terminal className="w-6 h-6 text-blue-600" />
              SQL Explorer
            </h1>

            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
              <ShieldCheck className="w-3.5 h-3.5" /> Read-Only Sandbox
            </span>

            <span className="text-xs text-slate-600 bg-slate-100 border border-slate-200 px-2.5 py-0.5 rounded-md font-mono">
              Table: <strong className="text-slate-900">dataset</strong> or <strong className="text-slate-900">data</strong>
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <Link
            to={`/datasets/${dataset.id}`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 hover:text-slate-900 text-xs font-semibold transition-colors shadow-sm"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Overview &amp; Analytics</span>
          </Link>
          <Link
            to={`/datasets/${dataset.id}/profile`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 hover:text-slate-900 text-xs font-semibold transition-colors shadow-sm"
          >
            <FileSearch className="w-3.5 h-3.5" />
            <span>Data Profile</span>
          </Link>
        </div>
      </div>

      {saveSuccessMsg && (
        <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs flex items-center gap-2">
          <CheckCircle className="w-4 h-4 shrink-0" />
          <span>{saveSuccessMsg}</span>
        </div>
      )}

      {/* Main Grid: Editor & Results (Left) + Saved Queries & Schema (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Column (Editor + Results Table) */}
        <div className="lg:col-span-3 space-y-6">
          {/* SQL Editor Panel */}
          <div className="glass-panel rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
            {/* Editor Header Bar */}
            <div className="flex items-center justify-between px-4 py-3 bg-slate-50 border-b border-slate-200 flex-wrap gap-2">
              <div className="flex items-center gap-2 text-xs text-slate-600">
                <Database className="w-4 h-4 text-blue-600" />
                <span className="font-semibold text-slate-800">Analytical Query</span>
                <span className="hidden sm:inline text-slate-400">&bull; Press Ctrl+Enter to execute</span>
              </div>

              {/* Quick Template Buttons */}
              <div className="flex items-center gap-1.5 flex-wrap">
                {QUICK_TEMPLATES.map((tmpl) => (
                  <button
                    key={tmpl.name}
                    onClick={() => {
                      setQuery(tmpl.query);
                      handleExecuteQuery(tmpl.query);
                    }}
                    className="text-xs px-2.5 py-1 rounded-lg bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 shadow-xs transition-colors cursor-pointer"
                    title={tmpl.query}
                  >
                    {tmpl.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Monospace Code Editor Area */}
            <div className="relative bg-slate-950 p-4">
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={5}
                placeholder="Enter SELECT query, e.g. SELECT * FROM dataset LIMIT 10;"
                className="w-full bg-transparent text-slate-200 font-mono text-sm leading-relaxed focus:outline-none resize-y selection:bg-blue-600/30 placeholder:text-slate-600"
                spellCheck={false}
              />
            </div>

            {/* Editor Action Controls */}
            <div className="flex items-center justify-between px-4 py-3 bg-slate-50 border-t border-slate-200 flex-wrap gap-3">
              <div className="flex items-center gap-3">
                <label className="text-xs text-slate-600 flex items-center gap-1.5 font-medium">
                  Row Limit:
                  <select
                    value={limit}
                    onChange={(e) => setLimit(Number(e.target.value))}
                    className="bg-white border border-slate-200 text-slate-800 text-xs rounded-lg px-2.5 py-1 focus:outline-none focus:border-blue-600 font-mono shadow-xs"
                  >
                    <option value={50}>50 rows</option>
                    <option value={100}>100 rows</option>
                    <option value={250}>250 rows</option>
                    <option value={500}>500 rows</option>
                    <option value={1000}>1,000 rows (max)</option>
                  </select>
                </label>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setSaveModalOpen(true)}
                  disabled={!query.trim() || isExecuting}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white hover:bg-slate-100 text-slate-700 text-xs font-semibold border border-slate-200 shadow-xs transition-colors disabled:opacity-50 cursor-pointer"
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>Save Query</span>
                </button>

                <button
                  onClick={() => handleExecuteQuery()}
                  disabled={isExecuting || !query.trim()}
                  className="inline-flex items-center gap-2 px-4 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm transition-all disabled:opacity-50 cursor-pointer"
                >
                  {isExecuting ? (
                    <LoadingSpinner size="sm" />
                  ) : (
                    <Play className="w-3.5 h-3.5 fill-current" />
                  )}
                  <span>{isExecuting ? 'Running...' : 'Run Query'}</span>
                </button>
              </div>
            </div>
          </div>

          {/* Safe Error Alert Banner */}
          {queryError && (
            <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-sm space-y-1.5 shadow-sm animate-in fade-in duration-200">
              <div className="font-semibold flex items-center gap-2 text-rose-900">
                <span className="w-2 h-2 rounded-full bg-rose-600 animate-pulse" />
                Query Execution Error
              </div>
              <p className="font-mono text-xs text-rose-800 break-words">{queryError}</p>
              <p className="text-xs text-rose-700/90">
                Ensure your query starts with <code className="text-slate-900 font-semibold font-mono">SELECT</code> and uses valid columns from <code className="text-slate-900 font-semibold font-mono">dataset</code>. Mutations and stacked statements are strictly prevented.
              </p>
            </div>
          )}

          {/* Query Results Section */}
          {queryResult && (
            <div className="glass-panel rounded-2xl border border-slate-200 overflow-hidden shadow-sm space-y-3 p-4">
              {/* Results Stats & Filter Bar */}
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-slate-200">
                <div className="flex items-center gap-3 text-xs flex-wrap">
                  <span className="font-semibold text-slate-900">
                    {queryResult.row_count.toLocaleString()} rows returned
                  </span>

                  <span className="inline-flex items-center gap-1 text-slate-500">
                    <Clock className="w-3.5 h-3.5 text-blue-600" />
                    {queryResult.execution_time_ms} ms
                  </span>

                  {queryResult.truncated && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
                      Capped at limit ({limit})
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <div className="relative">
                    <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      value={filterText}
                      onChange={(e) => setFilterText(e.target.value)}
                      placeholder="Filter results..."
                      className="pl-8 pr-3 py-1 rounded-xl bg-white border border-slate-200 text-xs text-slate-900 focus:outline-none focus:border-blue-600 placeholder:text-slate-400 shadow-xs"
                    />
                  </div>

                  <button
                    onClick={handleExportCsv}
                    className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-xs transition-colors cursor-pointer"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>CSV</span>
                  </button>
                </div>
              </div>

              {/* Table Container */}
              {queryResult.columns.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-500">
                  Query executed successfully, but returned no columns.
                </div>
              ) : filteredRows.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-500">
                  No records match your filter criteria.
                </div>
              ) : (
                <div className="overflow-x-auto max-h-[500px] rounded-xl border border-slate-200">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead className="bg-slate-50 text-slate-700 sticky top-0 backdrop-blur z-10 border-b border-slate-200">
                      <tr>
                        <th className="py-2.5 px-3 text-slate-500 font-mono text-[10px] w-12 text-center">
                          #
                        </th>
                        {queryResult.columns.map((col) => (
                          <th key={col} className="py-2.5 px-3 font-semibold text-slate-800 whitespace-nowrap">
                            <div className="flex items-center gap-1.5">
                              <span>{col}</span>
                              {queryResult.column_types[col] && (
                                <span className="text-[10px] text-slate-500 font-mono font-normal">
                                  ({queryResult.column_types[col]})
                                </span>
                              )}
                            </div>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-mono text-slate-800">
                      {filteredRows.map((row, idx) => (
                        <tr key={idx} className="hover:bg-slate-50/80 transition-colors">
                          <td className="py-2 px-3 text-slate-400 text-center text-[10px]">
                            {idx + 1}
                          </td>
                          {queryResult.columns.map((col) => {
                            const val = row[col];
                            return (
                              <td key={col} className="py-2 px-3 whitespace-nowrap">
                                {val === null ? (
                                  <span className="text-slate-400 italic">null</span>
                                ) : typeof val === 'boolean' ? (
                                  <span className={val ? 'text-emerald-700 font-semibold' : 'text-rose-700 font-semibold'}>
                                    {String(val)}
                                  </span>
                                ) : typeof val === 'number' ? (
                                  <span className="text-blue-700 font-semibold">
                                    {val.toLocaleString()}
                                  </span>
                                ) : (
                                  String(val)
                                )}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Column: Saved Queries & Quick Schema Reference */}
        <div className="space-y-6">
          {/* Saved Queries Card */}
          <div className="glass-panel rounded-2xl border border-slate-200 p-4 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                <Bookmark className="w-4 h-4 text-blue-600" />
                Saved Queries
              </h3>
              <span className="text-xs text-slate-500 font-mono">{savedQueries.length}</span>
            </div>

            {savedQueries.length === 0 ? (
              <p className="text-xs text-slate-500 py-3 text-center">
                No saved queries yet. Click &quot;Save Query&quot; above to store reusable analytical queries.
              </p>
            ) : (
              <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                {savedQueries.map((sq) => (
                  <div
                    key={sq.id}
                    className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 hover:border-slate-300 transition-all text-xs group"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-semibold text-slate-900 truncate">{sq.name}</span>
                      <button
                        onClick={() => handleDeleteSavedQuery(sq.id)}
                        className="text-slate-400 hover:text-rose-600 transition-colors opacity-0 group-hover:opacity-100 cursor-pointer"
                        title="Delete saved query"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    <p className="font-mono text-[11px] text-slate-500 truncate mt-1">
                      {sq.query}
                    </p>

                    <button
                      onClick={() => {
                        setQuery(sq.query);
                        handleExecuteQuery(sq.query);
                      }}
                      className="mt-2 text-[11px] font-semibold text-blue-600 hover:text-blue-700 inline-flex items-center gap-1 transition-colors cursor-pointer"
                    >
                      <Play className="w-3 h-3" /> Load &amp; Run
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Quick Security & Usage Reference */}
          <div className="glass-panel rounded-2xl border border-slate-200 p-4 space-y-3 text-xs text-slate-600">
            <h4 className="font-bold text-slate-900 flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              Security Architecture
            </h4>
            <ul className="space-y-1.5 list-disc pl-4 text-slate-600 leading-relaxed text-[11px]">
              <li>Queries run in an isolated in-memory analytical SQLite sandbox.</li>
              <li>Only <strong className="text-slate-900 font-semibold">SELECT</strong> queries and read-only analytical CTEs are allowed.</li>
              <li>Mutations (<code className="text-slate-900 font-semibold">DROP</code>, <code className="text-slate-900 font-semibold">DELETE</code>, <code className="text-slate-900 font-semibold">UPDATE</code>, <code className="text-slate-900 font-semibold">INSERT</code>) are rejected.</li>
              <li>Database credentials and Neon tables are completely inaccessible.</li>
              <li>Enforces strict 5.0-second execution timeout.</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Save Query Modal */}
      {saveModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 max-w-md w-full p-6 space-y-4 shadow-xl animate-in zoom-in-95 duration-150">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Bookmark className="w-5 h-5 text-blue-600" />
              Save Analytical Query
            </h3>

            <form onSubmit={handleSaveQuery} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Query Name
                </label>
                <input
                  type="text"
                  required
                  value={saveQueryName}
                  onChange={(e) => setSaveQueryName(e.target.value)}
                  placeholder="e.g. Monthly Top Products"
                  className="w-full px-3 py-2 rounded-xl bg-white border border-slate-200 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Query Preview
                </label>
                <textarea
                  readOnly
                  rows={3}
                  value={query}
                  className="w-full px-3 py-2 rounded-xl bg-slate-50 border border-slate-200 text-xs font-mono text-slate-600 focus:outline-none resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setSaveModalOpen(false)}
                  className="px-3.5 py-1.5 rounded-xl bg-white hover:bg-slate-100 border border-slate-200 text-slate-700 text-xs font-semibold transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingQuery || !saveQueryName.trim()}
                  className="px-4 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm transition-all disabled:opacity-50 cursor-pointer"
                >
                  {savingQuery ? 'Saving...' : 'Save Query'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default SqlExplorerPage;
