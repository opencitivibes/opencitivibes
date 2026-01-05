'use client';

import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/Button';
import { analyticsAPI } from '@/lib/api';
import { useToast } from '@/hooks/useToast';
import type { DateRange } from '@/types';
import { Download, FileSpreadsheet, ChevronDown } from 'lucide-react';

interface ExportButtonProps {
  dateRange?: DateRange;
}

type ExportType = 'overview' | 'ideas' | 'users' | 'categories';

export function ExportButton({ dateRange }: ExportButtonProps) {
  const { t } = useTranslation();
  const { success, error: showError } = useToast();
  const [isOpen, setIsOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [exportingType, setExportingType] = useState<ExportType | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleExport = async (dataType: ExportType) => {
    setIsExporting(true);
    setExportingType(dataType);
    setIsOpen(false);

    try {
      const params: {
        data_type: ExportType;
        start_date?: string;
        end_date?: string;
      } = { data_type: dataType };

      if (dateRange) {
        params.start_date = dateRange.startDate.toISOString().split('T')[0];
        params.end_date = dateRange.endDate.toISOString().split('T')[0];
      }

      const blob = await analyticsAPI.exportData(params);

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${dataType}_export_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      success('toast.exported');
    } catch (err) {
      console.error('Export failed:', err);
      showError(t('analytics.error'), { isRaw: true });
    } finally {
      setIsExporting(false);
      setExportingType(null);
    }
  };

  const exportOptions: { type: ExportType; labelKey: string }[] = [
    { type: 'overview', labelKey: 'analytics.overview' },
    { type: 'ideas', labelKey: 'analytics.totalIdeas' },
    { type: 'users', labelKey: 'analytics.totalUsers' },
    { type: 'categories', labelKey: 'analytics.categories' },
  ];

  return (
    <div className="relative" ref={dropdownRef}>
      <Button
        variant="secondary"
        size="sm"
        onClick={() => setIsOpen(!isOpen)}
        disabled={isExporting}
        loading={isExporting}
      >
        <Download className="h-4 w-4 mr-2" />
        {t('analytics.exportCSV')}
        <ChevronDown className="h-4 w-4 ml-2" />
      </Button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
          {exportOptions.map((option) => (
            <button
              key={option.type}
              onClick={() => handleExport(option.type)}
              disabled={isExporting}
              className="w-full flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <FileSpreadsheet className="h-4 w-4 mr-3 text-gray-400" />
              {t(option.labelKey)}
              {exportingType === option.type && (
                <svg
                  className="animate-spin ml-auto h-4 w-4 text-primary-500"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
