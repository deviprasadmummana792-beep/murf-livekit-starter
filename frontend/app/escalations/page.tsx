'use client';

import { useState, useEffect } from 'react';
import { 
  ArrowLeft, 
  Search, 
  ShieldAlert, 
  Clock, 
  CheckCircle2, 
  AlertTriangle,
  User, 
  FileText, 
  Globe, 
  Mail, 
  Phone,
  RefreshCw 
} from 'lucide-react';
import Link from 'next/link';

interface Escalation {
  reference_id: string;
  user_name: string;
  issue_summary: string;
  what_agent_checked: string;
  urgency: string;
  language: string;
  preferred_follow_up_method: string;
  status: string;
  created_at: string;
}

export default function EscalationsDashboard() {
  const [escalations, setEscalations] = useState<Escalation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedEscalation, setSelectedEscalation] = useState<Escalation | null>(null);

  const fetchEscalations = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch('/api/escalations');
      if (!res.ok) {
        throw new Error(`Failed to fetch: ${res.statusText}`);
      }
      const data = await res.json();
      setEscalations(Array.isArray(data) ? data : []);
    } catch (err: any) {
      setError(err.message || 'Unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEscalations();
  }, []);

  const handleStatusChange = async (refId: string, newStatus: string) => {
    try {
      const res = await fetch('/api/escalations', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reference_id: refId, status: newStatus }),
      });

      if (!res.ok) {
        throw new Error('Failed to update status');
      }

      // Update local state
      setEscalations(prev =>
        prev.map(item =>
          item.reference_id === refId ? { ...item, status: newStatus } : item
        )
      );

      if (selectedEscalation?.reference_id === refId) {
        setSelectedEscalation(prev => prev ? { ...prev, status: newStatus } : null);
      }
    } catch (err: any) {
      alert(`Error updating status: ${err.message}`);
    }
  };

  // KPI calculations
  const totalCount = escalations.length;
  const openCount = escalations.filter(e => e.status === 'open').length;
  const inProgressCount = escalations.filter(e => e.status === 'in_progress').length;
  const resolvedCount = escalations.filter(e => e.status === 'resolved').length;

  // Filter & search logic
  const filteredEscalations = escalations.filter(e => {
    const matchesStatus = statusFilter === 'all' || e.status === statusFilter;
    const matchesSearch = 
      e.reference_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.user_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.issue_summary.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  return (
    <div className="min-h-screen bg-[#0d0f14] text-gray-100 p-6 font-sans">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* Header */}
        <div className="flex justify-between items-center pb-4 border-b border-gray-800">
          <div className="flex items-center space-x-4">
            <Link 
              href="/" 
              className="p-2 bg-gray-900 rounded-lg hover:bg-gray-800 transition-colors text-gray-400 hover:text-white"
            >
              <ArrowLeft size={20} />
            </Link>
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">
                FinVoice Human Escalation Center
              </h1>
              <p className="text-sm text-gray-400 mt-1">
                Monitor and resolve customer support tickets escalated by the voice agent.
              </p>
            </div>
          </div>
          <button 
            onClick={fetchEscalations} 
            className="flex items-center space-x-2 px-4 py-2 bg-gray-900 hover:bg-gray-800 text-sm font-medium rounded-lg border border-gray-800 transition-colors"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-[#141820] border border-gray-800/80 rounded-xl p-5 shadow-lg">
            <p className="text-sm text-gray-400">Total Tickets</p>
            <p className="text-3xl font-semibold text-white mt-2">{totalCount}</p>
          </div>
          <div className="bg-[#141820] border border-gray-800/80 rounded-xl p-5 shadow-lg border-l-4 border-l-red-500">
            <p className="text-sm text-gray-400">Open</p>
            <p className="text-3xl font-semibold text-white mt-2">{openCount}</p>
          </div>
          <div className="bg-[#141820] border border-gray-800/80 rounded-xl p-5 shadow-lg border-l-4 border-l-amber-500">
            <p className="text-sm text-gray-400">In Progress</p>
            <p className="text-3xl font-semibold text-white mt-2">{inProgressCount}</p>
          </div>
          <div className="bg-[#141820] border border-gray-800/80 rounded-xl p-5 shadow-lg border-l-4 border-l-emerald-500">
            <p className="text-sm text-gray-400">Resolved</p>
            <p className="text-3xl font-semibold text-white mt-2">{resolvedCount}</p>
          </div>
        </div>

        {/* Search & Filter Controls */}
        <div className="flex flex-col sm:flex-row justify-between items-center gap-4 bg-[#141820] p-4 rounded-xl border border-gray-800/80">
          <div className="relative w-full sm:w-80">
            <Search className="absolute left-3 top-2.5 text-gray-500" size={18} />
            <input
              type="text"
              placeholder="Search ref ID, user, or issue..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-gray-950 border border-gray-850 rounded-lg text-sm focus:outline-none focus:border-indigo-500 text-gray-100 placeholder-gray-500"
            />
          </div>
          <div className="flex gap-2 w-full sm:w-auto overflow-x-auto">
            {['all', 'open', 'in_progress', 'resolved'].map(status => (
              <button
                key={status}
                onClick={() => setStatusFilter(status)}
                className={`px-4 py-2 rounded-lg text-xs font-semibold uppercase tracking-wider transition-colors ${
                  statusFilter === status 
                    ? 'bg-indigo-600 text-white' 
                    : 'bg-gray-950 text-gray-400 hover:text-white hover:bg-gray-900 border border-gray-850'
                }`}
              >
                {status.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>

        {/* Dashboard Layout: Table + Detail view */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Tickets Table */}
          <div className={`bg-[#141820] border border-gray-800/80 rounded-xl overflow-hidden shadow-lg lg:col-span-${selectedEscalation ? '2' : '3'}`}>
            {loading ? (
              <div className="flex flex-col items-center justify-center p-20 space-y-4 text-gray-400">
                <RefreshCw className="animate-spin text-indigo-500" size={32} />
                <p>Loading escalations...</p>
              </div>
            ) : error ? (
              <div className="p-20 text-center text-red-400">
                <AlertTriangle className="mx-auto text-red-500 mb-4" size={40} />
                <p className="font-medium">Failed to load data</p>
                <p className="text-sm mt-1 text-gray-500">{error}</p>
              </div>
            ) : filteredEscalations.length === 0 ? (
              <div className="p-20 text-center text-gray-500">
                <Clock className="mx-auto mb-4" size={40} />
                <p className="font-medium">No escalation requests found</p>
                <p className="text-sm mt-1">No requests match your current search or filter.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-gray-800 bg-gray-900/60 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                      <th className="py-4 px-5">Ref ID</th>
                      <th className="py-4 px-5">User</th>
                      <th className="py-4 px-5">Issue</th>
                      <th className="py-4 px-5">Urgency</th>
                      <th className="py-4 px-5">Follow-up</th>
                      <th className="py-4 px-5">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-850">
                    {filteredEscalations.map((item) => (
                      <tr 
                        key={item.reference_id}
                        onClick={() => setSelectedEscalation(item)}
                        className={`hover:bg-gray-800/40 cursor-pointer transition-colors ${
                          selectedEscalation?.reference_id === item.reference_id ? 'bg-indigo-900/10 border-l-2 border-l-indigo-500' : ''
                        }`}
                      >
                        <td className="py-4 px-5 font-mono text-sm text-indigo-400 font-bold">{item.reference_id}</td>
                        <td className="py-4 px-5 font-medium">{item.user_name}</td>
                        <td className="py-4 px-5 max-w-xs truncate text-gray-300 text-sm">{item.issue_summary}</td>
                        <td className="py-4 px-5">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                            item.urgency === 'high' ? 'bg-red-500/10 text-red-400 border border-red-550/20' :
                            item.urgency === 'low' ? 'bg-blue-500/10 text-blue-400 border border-blue-550/20' :
                            'bg-gray-500/10 text-gray-400 border border-gray-550/20'
                          }`}>
                            {item.urgency}
                          </span>
                        </td>
                        <td className="py-4 px-5 text-sm text-gray-400 capitalize">{item.preferred_follow_up_method}</td>
                        <td className="py-4 px-5">
                          <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${
                            item.status === 'resolved' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                            item.status === 'in_progress' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                            'bg-red-500/10 text-red-400 border border-red-500/20'
                          }`}>
                            {item.status.replace('_', ' ')}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Ticket Inspection Panel */}
          {selectedEscalation && (
            <div className="bg-[#141820] border border-gray-800/80 rounded-xl p-6 shadow-lg space-y-6 flex flex-col justify-between">
              <div>
                <div className="flex justify-between items-start">
                  <div>
                    <span className="font-mono text-sm text-indigo-400 font-bold">{selectedEscalation.reference_id}</span>
                    <h2 className="text-xl font-semibold text-white mt-1">Inspection Panel</h2>
                  </div>
                  <button 
                    onClick={() => setSelectedEscalation(null)}
                    className="text-gray-500 hover:text-gray-300 text-sm font-medium"
                  >
                    Close
                  </button>
                </div>

                <div className="space-y-4 mt-6">
                  
                  {/* Status update controller */}
                  <div className="bg-gray-950 p-4 rounded-lg border border-gray-850">
                    <label className="text-xs text-gray-450 block font-semibold uppercase tracking-wider mb-2">Change Ticket Status</label>
                    <div className="grid grid-cols-3 gap-2">
                      {['open', 'in_progress', 'resolved'].map(st => (
                        <button
                          key={st}
                          onClick={() => handleStatusChange(selectedEscalation.reference_id, st)}
                          className={`py-2 px-1 text-center rounded text-xs font-semibold transition-colors ${
                            selectedEscalation.status === st
                              ? st === 'resolved' ? 'bg-emerald-600 text-white' :
                                st === 'in_progress' ? 'bg-amber-600 text-white' :
                                'bg-red-600 text-white'
                              : 'bg-gray-900 text-gray-400 hover:bg-gray-800 hover:text-white'
                          }`}
                        >
                          {st.replace('_', ' ')}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* General ticket properties */}
                  <div className="space-y-3">
                    <div className="flex items-start space-x-3 text-sm">
                      <User className="text-gray-500 mt-0.5" size={16} />
                      <div>
                        <p className="text-gray-400 text-xs">Customer Name</p>
                        <p className="text-gray-200 mt-0.5">{selectedEscalation.user_name}</p>
                      </div>
                    </div>

                    <div className="flex items-start space-x-3 text-sm">
                      <Globe className="text-gray-500 mt-0.5" size={16} />
                      <div>
                        <p className="text-gray-400 text-xs">Preferred Language</p>
                        <p className="text-gray-200 mt-0.5">{selectedEscalation.language}</p>
                      </div>
                    </div>

                    <div className="flex items-start space-x-3 text-sm">
                      {selectedEscalation.preferred_follow_up_method === 'email' ? (
                        <Mail className="text-gray-500 mt-0.5" size={16} />
                      ) : (
                        <Phone className="text-gray-500 mt-0.5" size={16} />
                      )}
                      <div>
                        <p className="text-gray-400 text-xs">Follow-up Preference</p>
                        <p className="text-gray-200 mt-0.5 capitalize">{selectedEscalation.preferred_follow_up_method}</p>
                      </div>
                    </div>

                    <div className="flex items-start space-x-3 text-sm">
                      <Clock className="text-gray-500 mt-0.5" size={16} />
                      <div>
                        <p className="text-gray-400 text-xs">Created At</p>
                        <p className="text-gray-200 mt-0.5 font-mono">
                          {new Date(selectedEscalation.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Text sections */}
                  <div className="border-t border-gray-850 pt-4 space-y-3">
                    <div>
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 flex items-center gap-1.5 mb-1">
                        <FileText size={12} />
                        Issue Summary
                      </h4>
                      <p className="text-gray-205 bg-gray-950 p-3 rounded-lg border border-gray-850 text-sm whitespace-pre-wrap leading-relaxed">
                        {selectedEscalation.issue_summary || 'No summary available.'}
                      </p>
                    </div>

                    <div>
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 flex items-center gap-1.5 mb-1">
                        <ShieldAlert size={12} />
                        What Agent Verified
                      </h4>
                      <p className="text-gray-205 bg-gray-950 p-3 rounded-lg border border-gray-850 text-sm whitespace-pre-wrap leading-relaxed">
                        {selectedEscalation.what_agent_checked || 'No verification details.'}
                      </p>
                    </div>
                  </div>

                </div>
              </div>

              <div className="pt-4 border-t border-gray-850 text-center">
                <p className="text-xs text-gray-550">
                  Select another ticket to inspect its details.
                </p>
              </div>
            </div>
          )}

        </div>

      </div>
    </div>
  );
}
