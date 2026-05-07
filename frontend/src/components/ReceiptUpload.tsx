'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { uploadReceipt, getTaskStatus } from '@/lib/api';
import { TaskStatus } from '@/types';

const processingStages = [
  { key: 'uploading', label: 'Uploading receipt...' },
  { key: 'processing', label: 'Extracting text with OCR...' },
  { key: 'analyzing', label: 'Analyzing with AI...' },
  { key: 'categorizing', label: 'Categorizing expense...' },
  { key: 'completed', label: 'Done!' },
];

interface ReceiptUploadProps {
  onUploadComplete?: () => void;
}

export default function ReceiptUpload({ onUploadComplete }: ReceiptUploadProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [currentStage, setCurrentStage] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);

  // abortRef prevents setState calls on an unmounted component.
  // The cleanup in useEffect sets it to true when the component unmounts,
  // and each poll() checks it before updating state or scheduling the next tick.
  const abortRef = useRef(false);

  useEffect(() => {
    return () => {
      abortRef.current = true;
    };
  }, []);

  // Polls GET /api/receipts/status/{taskId} every 2 seconds until the Celery
  // task reaches a terminal state (completed | failed) or the 60-attempt limit.
  const pollTaskStatus = useCallback(async (taskId: string) => {
    abortRef.current = false;
    const maxAttempts = 60; // 60 × 2s = 2-minute timeout
    let attempts = 0;

    const poll = async () => {
      if (abortRef.current) return;

      if (attempts >= maxAttempts) {
        setError('Processing timed out. Please try again.');
        setIsUploading(false);
        return;
      }

      try {
        const status = await getTaskStatus(taskId);
        if (abortRef.current) return;

        setTaskStatus(status);

        if (status.status === 'processing') {
          setCurrentStage(2); // advance UI to "Extracting text with OCR..."
        }

        if (status.status === 'completed') {
          setCurrentStage(4); // show "Done!" briefly before resetting
          setTimeout(() => {
            if (abortRef.current) return;
            setIsUploading(false);
            setCurrentStage(0);
            setTaskStatus(null);
            onUploadComplete?.(); // trigger parent to refresh expense list
          }, 1500);
          return;
        }

        if (status.status === 'failed') {
          setError(status.error || 'Processing failed. Please try again.');
          setIsUploading(false);
          return;
        }

        attempts++;
        if (!abortRef.current) setTimeout(poll, 2000);
      } catch {
        // Network hiccup — back off slightly and retry
        attempts++;
        if (!abortRef.current) setTimeout(poll, 3000);
      }
    };

    poll();
  }, [onUploadComplete]);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;

    setIsUploading(true);
    setError(null);
    setCurrentStage(0);

    try {
      setCurrentStage(0);
      const { task_id } = await uploadReceipt(file);
      setCurrentStage(1);
      pollTaskStatus(task_id);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Upload failed. Please try again.';
      setError(message);
      setIsUploading(false);
    }
  }, [pollTaskStatus]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
    },
    maxFiles: 1,
    disabled: isUploading,
  });

  const handleRetry = () => {
    setError(null);
    setIsUploading(false);
    setCurrentStage(0);
    setTaskStatus(null);
  };

  return (
    <div className="glass-card p-6">
      <h2 className="text-lg font-semibold text-white mb-4">Upload Receipt</h2>

      {error ? (
        <div className="text-center py-8">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-500/10 flex items-center justify-center">
            <svg className="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <p className="text-red-400 mb-4">{error}</p>
          <button
            onClick={handleRetry}
            className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
          >
            Try Again
          </button>
        </div>
      ) : isUploading ? (
        <div className="py-8 space-y-4">
          {processingStages.map((stage, index) => (
            <div key={stage.key} className="flex items-center gap-3">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 transition-all duration-300 ${
                  index < currentStage
                    ? 'bg-green-500/20 text-green-400'
                    : index === currentStage
                    ? 'bg-blue-500/20 text-blue-400 animate-pulse-slow'
                    : 'bg-slate-800 text-slate-600'
                }`}
              >
                {index < currentStage ? (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <span className="text-xs font-medium">{index + 1}</span>
                )}
              </div>
              <span
                className={`text-sm ${
                  index < currentStage
                    ? 'text-green-400'
                    : index === currentStage
                    ? 'text-blue-400'
                    : 'text-slate-600'
                }`}
              >
                {stage.label}
              </span>
            </div>
          ))}
          {taskStatus?.progress !== undefined && (
            <div className="mt-4">
              <div className="w-full bg-slate-800 rounded-full h-2">
                <div
                  className="bg-blue-500 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${taskStatus.progress}%` }}
                />
              </div>
            </div>
          )}
        </div>
      ) : (
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200 ${
            isDragActive
              ? 'border-blue-500 bg-blue-500/5'
              : 'border-slate-700 hover:border-slate-600 hover:bg-slate-800/30'
          }`}
        >
          <input {...getInputProps()} />
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-800 flex items-center justify-center">
            <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          {isDragActive ? (
            <p className="text-blue-400 font-medium">Drop your receipt here</p>
          ) : (
            <>
              <p className="text-slate-300 font-medium mb-1">
                Drag & drop a receipt image
              </p>
              <p className="text-slate-500 text-sm">or click to browse (JPG, PNG)</p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
