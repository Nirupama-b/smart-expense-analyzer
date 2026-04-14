'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import Navbar from '@/components/Navbar';

export default function SettingsPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [profileLoading, setProfileLoading] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [profileMessage, setProfileMessage] = useState('');
  const [passwordMessage, setPasswordMessage] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState(false);

  useEffect(() => {
    const checkAuth = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        router.push('/login');
        return;
      }
      setEmail(session.user.email || '');
      setName(session.user.user_metadata?.name || '');
    };
    checkAuth();
  }, [router]);

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setProfileLoading(true);
    setProfileMessage('');

    try {
      const { error } = await supabase.auth.updateUser({
        data: { name },
      });

      if (error) {
        setProfileMessage(`Error: ${error.message}`);
      } else {
        setProfileMessage('Profile updated successfully.');
      }
    } catch {
      setProfileMessage('An unexpected error occurred.');
    } finally {
      setProfileLoading(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordLoading(true);
    setPasswordMessage('');
    setPasswordError('');

    if (newPassword !== confirmPassword) {
      setPasswordError('Passwords do not match.');
      setPasswordLoading(false);
      return;
    }

    if (newPassword.length < 6) {
      setPasswordError('Password must be at least 6 characters.');
      setPasswordLoading(false);
      return;
    }

    try {
      // Re-authenticate with current password
      const { error: signInError } = await supabase.auth.signInWithPassword({
        email,
        password: currentPassword,
      });

      if (signInError) {
        setPasswordError('Current password is incorrect.');
        setPasswordLoading(false);
        return;
      }

      const { error } = await supabase.auth.updateUser({
        password: newPassword,
      });

      if (error) {
        setPasswordError(error.message);
      } else {
        setPasswordMessage('Password changed successfully.');
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');
      }
    } catch {
      setPasswordError('An unexpected error occurred.');
    } finally {
      setPasswordLoading(false);
    }
  };

  const handleExportCSV = async () => {
    setExportLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const { data: { session } } = await supabase.auth.getSession();

      const response = await fetch(`${apiUrl}/api/expenses/export`, {
        headers: {
          Authorization: `Bearer ${session?.access_token}`,
        },
      });

      if (!response.ok) throw new Error('Export failed');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `expenses-${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Export failed:', err);
    } finally {
      setExportLoading(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (!deleteConfirm) {
      setDeleteConfirm(true);
      return;
    }

    try {
      await supabase.auth.signOut();
      router.push('/');
    } catch (err) {
      console.error('Failed to delete account:', err);
    }
  };

  return (
    <div className="flex min-h-screen">
      <Navbar />
      <main className="flex-1 ml-64 p-8">
        <div className="max-w-3xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-white">Settings</h1>
            <p className="text-slate-400 mt-1">Manage your account and preferences</p>
          </div>

          {/* Profile Info */}
          <div className="glass-card p-6 mb-6">
            <h2 className="text-lg font-semibold text-white mb-4">Profile Information</h2>
            <form onSubmit={handleUpdateProfile} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Email</label>
                <input
                  type="email"
                  value={email}
                  disabled
                  className="w-full px-4 py-2.5 bg-slate-800/30 border border-slate-700 rounded-lg text-slate-400 cursor-not-allowed"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Full Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-4 py-2.5 bg-slate-800/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
                />
              </div>
              {profileMessage && (
                <p className={`text-sm ${profileMessage.startsWith('Error') ? 'text-red-400' : 'text-green-400'}`}>
                  {profileMessage}
                </p>
              )}
              <button
                type="submit"
                disabled={profileLoading}
                className="px-6 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-500/50 text-white rounded-lg text-sm font-medium transition-colors"
              >
                {profileLoading ? 'Saving...' : 'Save Changes'}
              </button>
            </form>
          </div>

          {/* Change Password */}
          <div className="glass-card p-6 mb-6">
            <h2 className="text-lg font-semibold text-white mb-4">Change Password</h2>
            <form onSubmit={handleChangePassword} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Current Password</label>
                <input
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  required
                  className="w-full px-4 py-2.5 bg-slate-800/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
                  placeholder="Enter current password"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">New Password</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={6}
                  className="w-full px-4 py-2.5 bg-slate-800/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
                  placeholder="Min. 6 characters"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Confirm New Password</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  className="w-full px-4 py-2.5 bg-slate-800/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
                  placeholder="Confirm new password"
                />
              </div>
              {passwordError && <p className="text-sm text-red-400">{passwordError}</p>}
              {passwordMessage && <p className="text-sm text-green-400">{passwordMessage}</p>}
              <button
                type="submit"
                disabled={passwordLoading}
                className="px-6 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-500/50 text-white rounded-lg text-sm font-medium transition-colors"
              >
                {passwordLoading ? 'Changing...' : 'Change Password'}
              </button>
            </form>
          </div>

          {/* Export Data */}
          <div className="glass-card p-6 mb-6">
            <h2 className="text-lg font-semibold text-white mb-4">Export Data</h2>
            <p className="text-sm text-slate-400 mb-4">
              Download all your expense data as a CSV file for backup or analysis in other tools.
            </p>
            <button
              onClick={handleExportCSV}
              disabled={exportLoading}
              className="flex items-center gap-2 px-6 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm font-medium border border-slate-700 transition-colors disabled:opacity-50"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              {exportLoading ? 'Exporting...' : 'Export CSV'}
            </button>
          </div>

          {/* Danger Zone */}
          <div className="glass-card p-6 border-red-500/20">
            <h2 className="text-lg font-semibold text-red-400 mb-4">Danger Zone</h2>
            <p className="text-sm text-slate-400 mb-4">
              Once you delete your account, there is no going back. Please be certain.
            </p>
            <button
              onClick={handleDeleteAccount}
              className={`px-6 py-2 rounded-lg text-sm font-medium transition-colors ${
                deleteConfirm
                  ? 'bg-red-500 hover:bg-red-600 text-white'
                  : 'bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20'
              }`}
            >
              {deleteConfirm ? 'Click again to confirm deletion' : 'Delete Account'}
            </button>
            {deleteConfirm && (
              <button
                onClick={() => setDeleteConfirm(false)}
                className="ml-3 px-4 py-2 text-sm text-slate-400 hover:text-slate-300 transition-colors"
              >
                Cancel
              </button>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
