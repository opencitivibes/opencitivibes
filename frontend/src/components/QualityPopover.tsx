'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { useTranslation } from 'react-i18next';
import { X, Check } from 'lucide-react';
import { QualityChips } from './QualityChips';
import { voteAPI } from '@/lib/api';
import type { QualityType } from '@/types';

interface QualityPopoverProps {
  ideaId: number;
  isOpen: boolean;
  onClose: () => void;
  initialQualities?: QualityType[];
  anchorRef: React.RefObject<HTMLElement | null>;
}

export function QualityPopover({
  ideaId,
  isOpen,
  onClose,
  initialQualities = [],
  anchorRef,
}: QualityPopoverProps) {
  const { t } = useTranslation();
  const [selected, setSelected] = useState<QualityType[]>(initialQualities);
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saved' | 'error'>('idle');
  const [isMobile, setIsMobile] = useState(false);
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const autoCloseTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const saveStatusTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Detect mobile viewport
  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 640);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Calculate position based on anchor element
  useEffect(() => {
    if (!isOpen) {
      setPosition(null);
      return;
    }

    if (isMobile) {
      return; // Mobile uses fixed bottom sheet, no positioning needed
    }

    let rafId: number;

    const updatePosition = () => {
      if (!anchorRef.current) return;

      const rect = anchorRef.current.getBoundingClientRect();

      // Calculate position relative to viewport (for fixed positioning)
      const top = rect.bottom + 8; // 8px gap below button
      const left = rect.left;

      // Ensure popover doesn't go off-screen to the right
      const popoverWidth = 280; // min-width from CSS
      const maxLeft = window.innerWidth - popoverWidth - 16; // 16px margin
      const adjustedLeft = Math.max(8, Math.min(left, maxLeft)); // Also ensure min 8px from left

      // Ensure popover doesn't go off-screen at bottom
      const popoverHeight = 200; // approximate height
      const maxTop = window.innerHeight - popoverHeight - 16;
      const adjustedTop = Math.min(top, maxTop);

      setPosition((prev) => {
        // Only update if position changed (avoid unnecessary rerenders)
        if (prev?.top === adjustedTop && prev?.left === adjustedLeft) {
          return prev;
        }
        return { top: adjustedTop, left: adjustedLeft };
      });
    };

    // Continuously update position while popover is open
    // This handles cases where the anchor moves (e.g., list reorder)
    const animate = () => {
      updatePosition();
      rafId = requestAnimationFrame(animate);
    };

    rafId = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(rafId);
    };
  }, [isOpen, anchorRef, isMobile]);

  // Memoize onClose to prevent infinite loops
  const handleClose = useCallback(() => {
    // Return focus to trigger element
    if (anchorRef.current) {
      anchorRef.current.focus();
    }
    onClose();
  }, [onClose, anchorRef]);

  // Reset timer function
  const resetTimer = useCallback(() => {
    if (autoCloseTimer.current) clearTimeout(autoCloseTimer.current);
    autoCloseTimer.current = setTimeout(() => {
      handleClose();
    }, 5000);
  }, [handleClose]);

  // Auto-close after 5 seconds of inactivity
  useEffect(() => {
    if (isOpen) {
      autoCloseTimer.current = setTimeout(() => {
        handleClose();
      }, 5000);
      // Focus the close button when popover opens
      setTimeout(() => closeButtonRef.current?.focus(), 100);
    }
    return () => {
      if (autoCloseTimer.current) clearTimeout(autoCloseTimer.current);
    };
  }, [isOpen, handleClose]);

  // Sync initial qualities when prop changes
  useEffect(() => {
    setSelected(initialQualities);
  }, [initialQualities]);

  // Save qualities when selection changes
  const handleChange = async (qualities: QualityType[]) => {
    setSelected(qualities);
    resetTimer();
    setSaveStatus('idle');

    setIsSaving(true);
    try {
      await voteAPI.updateQualities(ideaId, qualities);
      setSaveStatus('saved');
      // Clear saved status after 2 seconds
      if (saveStatusTimer.current) clearTimeout(saveStatusTimer.current);
      saveStatusTimer.current = setTimeout(() => setSaveStatus('idle'), 2000);
    } catch (err) {
      console.error('Failed to save qualities:', err);
      setSaveStatus('error');
    } finally {
      setIsSaving(false);
    }
  };

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        popoverRef.current &&
        !popoverRef.current.contains(e.target as Node) &&
        anchorRef.current &&
        !anchorRef.current.contains(e.target as Node)
      ) {
        handleClose();
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen, handleClose, anchorRef]);

  // Handle keyboard navigation and escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        handleClose();
      }

      // Focus trap: Tab and Shift+Tab
      if (e.key === 'Tab' && popoverRef.current) {
        const focusableElements = popoverRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (e.shiftKey && document.activeElement === firstElement) {
          e.preventDefault();
          lastElement?.focus();
        } else if (!e.shiftKey && document.activeElement === lastElement) {
          e.preventDefault();
          firstElement?.focus();
        }
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      // Prevent body scroll on mobile when bottom sheet is open
      if (isMobile) {
        document.body.style.overflow = 'hidden';
      }
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [isOpen, handleClose, isMobile]);

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      if (saveStatusTimer.current) clearTimeout(saveStatusTimer.current);
    };
  }, []);

  if (!isOpen) return null;

  // Mobile bottom sheet (uses portal with fixed positioning)
  if (isMobile) {
    return createPortal(
      <>
        {/* Backdrop */}
        <div
          className="fixed inset-0 bg-black/50 z-[9998] motion-safe:animate-in motion-safe:fade-in"
          onClick={handleClose}
          aria-hidden="true"
        />
        {/* Bottom sheet */}
        <div
          ref={popoverRef}
          role="dialog"
          aria-modal="true"
          aria-label={t('qualities.title')}
          className="fixed inset-x-0 bottom-0 z-[9999] p-4 pt-6 bg-white dark:bg-gray-800
            rounded-t-2xl shadow-2xl motion-safe:animate-in motion-safe:slide-in-from-bottom
            motion-safe:duration-200"
          style={{ paddingBottom: 'max(1rem, env(safe-area-inset-bottom))' }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Drag handle for visual affordance */}
          <div className="absolute top-2 left-1/2 -translate-x-1/2 w-10 h-1 bg-gray-300 dark:bg-gray-600 rounded-full" />

          <div className="flex items-center justify-between mb-4">
            <h4 className="text-base font-medium text-gray-700 dark:text-gray-300">
              {t('qualities.title')}
            </h4>
            <button
              ref={closeButtonRef}
              onClick={handleClose}
              className="p-2 -mr-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700
                text-gray-400 hover:text-gray-600 dark:hover:text-gray-300
                transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label={t('common.close')}
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <QualityChips selected={selected} onChange={handleChange} disabled={isSaving} />

          <div className="mt-4 flex items-center justify-between">
            <p className="text-sm text-gray-500 dark:text-gray-400">{t('qualities.hint')}</p>
            {/* Live region for screen readers */}
            <div aria-live="polite" aria-atomic="true" className="flex items-center gap-1">
              {saveStatus === 'saved' && (
                <span className="text-sm text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                  <Check className="w-4 h-4" />
                  {t('qualities.saved')}
                </span>
              )}
              {saveStatus === 'error' && (
                <span className="text-sm text-red-500">{t('toast.qualitiesSaveFailed')}</span>
              )}
              {isSaving && <span className="text-sm text-gray-500">{t('qualities.saving')}</span>}
            </div>
          </div>
        </div>
      </>,
      document.body
    );
  }

  // Desktop popover (uses portal with fixed positioning)
  // Don't render until position is calculated
  if (!position) return null;

  return createPortal(
    <div
      ref={popoverRef}
      role="dialog"
      aria-modal="true"
      aria-label={t('qualities.title')}
      className="fixed z-[9999] p-4 bg-white dark:bg-gray-800 rounded-xl shadow-lg
        border border-gray-200 dark:border-gray-700
        min-w-[280px] max-w-sm motion-safe:animate-in motion-safe:fade-in
        motion-safe:slide-in-from-top-2 motion-safe:duration-200"
      style={{ top: position.top, left: position.left }}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
          {t('qualities.title')}
        </h4>
        <button
          ref={closeButtonRef}
          onClick={handleClose}
          className="p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700
            text-gray-400 hover:text-gray-600 dark:hover:text-gray-300
            transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
          aria-label={t('common.close')}
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <QualityChips selected={selected} onChange={handleChange} disabled={isSaving} />

      <div className="mt-3 flex items-center justify-between">
        <p className="text-xs text-gray-500 dark:text-gray-400">{t('qualities.hint')}</p>
        {/* Live region for screen readers */}
        <div aria-live="polite" aria-atomic="true" className="flex items-center gap-1">
          {saveStatus === 'saved' && (
            <span className="text-xs text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
              <Check className="w-3 h-3" />
              {t('qualities.saved')}
            </span>
          )}
          {saveStatus === 'error' && (
            <span className="text-xs text-red-500">{t('toast.qualitiesSaveFailed')}</span>
          )}
          {isSaving && <span className="text-xs text-gray-500">{t('qualities.saving')}</span>}
        </div>
      </div>
    </div>,
    document.body
  );
}
