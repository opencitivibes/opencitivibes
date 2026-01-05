'use client';

import { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { Editor } from '@tiptap/react';
import { MenuButton, MenuDivider } from './MenuButton';

interface ToolbarProps {
  editor: Editor | null;
  mode?: 'full' | 'simple';
}

/**
 * Link input dialog for the toolbar
 */
function LinkDialog({
  isOpen,
  onClose,
  onSave,
  initialUrl,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSave: (url: string) => void;
  initialUrl: string;
}) {
  const { t } = useTranslation();
  const [url, setUrl] = useState(initialUrl);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (url.trim()) {
      // Add https:// if no protocol specified
      const finalUrl = url.match(/^https?:\/\//) ? url : `https://${url}`;
      onSave(finalUrl);
    }
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="absolute top-full left-0 mt-1 p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg z-50">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder={t('editor.linkUrl')}
          className="px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
          autoFocus
        />
        <button
          type="submit"
          className="px-3 py-1.5 bg-primary-500 text-white rounded text-sm hover:bg-primary-600 focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          {t('editor.linkSave')}
        </button>
        <button
          type="button"
          onClick={onClose}
          className="px-3 py-1.5 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded text-sm hover:bg-gray-200 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500"
        >
          {t('editor.linkCancel')}
        </button>
      </form>
    </div>
  );
}

export function Toolbar({ editor, mode = 'full' }: ToolbarProps) {
  const { t } = useTranslation();
  const [showLinkDialog, setShowLinkDialog] = useState(false);

  const setLink = useCallback(
    (url: string) => {
      if (!editor) return;

      if (url) {
        editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run();
      } else {
        editor.chain().focus().extendMarkRange('link').unsetLink().run();
      }
    },
    [editor]
  );

  const openLinkDialog = useCallback(() => {
    if (!editor) return;
    setShowLinkDialog(true);
  }, [editor]);

  if (!editor) return null;

  // Simple mode: only bold, italic, link
  if (mode === 'simple') {
    return (
      <div
        role="toolbar"
        aria-label={t('editor.toolbar', 'Text formatting toolbar')}
        className="flex items-center gap-0.5 p-2 border-b border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 rounded-t-lg relative"
      >
        <MenuButton
          onClick={() => editor.chain().focus().toggleBold().run()}
          isActive={editor.isActive('bold')}
          title={`${t('editor.bold')} (Ctrl+B)`}
        >
          <BoldIcon />
        </MenuButton>
        <MenuButton
          onClick={() => editor.chain().focus().toggleItalic().run()}
          isActive={editor.isActive('italic')}
          title={`${t('editor.italic')} (Ctrl+I)`}
        >
          <ItalicIcon />
        </MenuButton>
        <MenuDivider />
        <MenuButton
          onClick={openLinkDialog}
          isActive={editor.isActive('link')}
          title={`${t('editor.link')} (Ctrl+K)`}
        >
          <LinkIcon />
        </MenuButton>

        <LinkDialog
          isOpen={showLinkDialog}
          onClose={() => setShowLinkDialog(false)}
          onSave={setLink}
          initialUrl={editor.getAttributes('link').href || ''}
        />
      </div>
    );
  }

  // Full mode: all formatting options
  return (
    <div
      role="toolbar"
      aria-label={t('editor.toolbar', 'Text formatting toolbar')}
      className="flex flex-wrap items-center gap-0.5 p-2 border-b border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 rounded-t-lg relative"
    >
      {/* Text formatting */}
      <MenuButton
        onClick={() => editor.chain().focus().toggleBold().run()}
        isActive={editor.isActive('bold')}
        title={`${t('editor.bold')} (Ctrl+B)`}
      >
        <BoldIcon />
      </MenuButton>
      <MenuButton
        onClick={() => editor.chain().focus().toggleItalic().run()}
        isActive={editor.isActive('italic')}
        title={`${t('editor.italic')} (Ctrl+I)`}
      >
        <ItalicIcon />
      </MenuButton>
      <MenuButton
        onClick={() => editor.chain().focus().toggleUnderline().run()}
        isActive={editor.isActive('underline')}
        title={`${t('editor.underline')} (Ctrl+U)`}
      >
        <UnderlineIcon />
      </MenuButton>
      <MenuButton
        onClick={() => editor.chain().focus().toggleStrike().run()}
        isActive={editor.isActive('strike')}
        title={`${t('editor.strikethrough')} (Ctrl+Shift+X)`}
      >
        <StrikethroughIcon />
      </MenuButton>

      <MenuDivider />

      {/* Headings */}
      <MenuButton
        onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
        isActive={editor.isActive('heading', { level: 2 })}
        title={`${t('editor.heading2')} (Ctrl+Alt+2)`}
      >
        <span className="text-sm font-bold">H2</span>
      </MenuButton>
      <MenuButton
        onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
        isActive={editor.isActive('heading', { level: 3 })}
        title={`${t('editor.heading3')} (Ctrl+Alt+3)`}
      >
        <span className="text-sm font-bold">H3</span>
      </MenuButton>

      <MenuDivider />

      {/* Lists */}
      <MenuButton
        onClick={() => editor.chain().focus().toggleBulletList().run()}
        isActive={editor.isActive('bulletList')}
        title={`${t('editor.bulletList')} (Ctrl+Shift+8)`}
      >
        <BulletListIcon />
      </MenuButton>
      <MenuButton
        onClick={() => editor.chain().focus().toggleOrderedList().run()}
        isActive={editor.isActive('orderedList')}
        title={`${t('editor.numberedList')} (Ctrl+Shift+7)`}
      >
        <NumberedListIcon />
      </MenuButton>

      <MenuDivider />

      {/* Blocks */}
      <MenuButton
        onClick={() => editor.chain().focus().toggleBlockquote().run()}
        isActive={editor.isActive('blockquote')}
        title={`${t('editor.blockquote')} (Ctrl+Shift+B)`}
      >
        <QuoteIcon />
      </MenuButton>
      <MenuButton
        onClick={() => editor.chain().focus().toggleCodeBlock().run()}
        isActive={editor.isActive('codeBlock')}
        title={`${t('editor.codeBlock')} (Ctrl+Alt+C)`}
      >
        <CodeBlockIcon />
      </MenuButton>

      <MenuDivider />

      {/* Link */}
      <MenuButton
        onClick={openLinkDialog}
        isActive={editor.isActive('link')}
        title={`${t('editor.link')} (Ctrl+K)`}
      >
        <LinkIcon />
      </MenuButton>

      <MenuDivider />

      {/* History */}
      <MenuButton
        onClick={() => editor.chain().focus().undo().run()}
        disabled={!editor.can().undo()}
        title={`${t('editor.undo')} (Ctrl+Z)`}
      >
        <UndoIcon />
      </MenuButton>
      <MenuButton
        onClick={() => editor.chain().focus().redo().run()}
        disabled={!editor.can().redo()}
        title={`${t('editor.redo')} (Ctrl+Shift+Z)`}
      >
        <RedoIcon />
      </MenuButton>

      <LinkDialog
        isOpen={showLinkDialog}
        onClose={() => setShowLinkDialog(false)}
        onSave={setLink}
        initialUrl={editor.getAttributes('link').href || ''}
      />
    </div>
  );
}

// SVG Icons - responsive sizes for mobile
function BoldIcon() {
  return (
    <svg className="w-4 h-4 sm:w-5 sm:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M6 4h8a4 4 0 014 4 4 4 0 01-4 4H6z"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M6 12h9a4 4 0 014 4 4 4 0 01-4 4H6z"
      />
    </svg>
  );
}

function ItalicIcon() {
  return (
    <svg className="w-4 h-4 sm:w-5 sm:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M10 4h4m-2 0v16m-4 0h4"
        transform="skewX(-10)"
      />
    </svg>
  );
}

function UnderlineIcon() {
  return (
    <svg className="w-4 h-4 sm:w-5 sm:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M6 3v7a6 6 0 006 6 6 6 0 006-6V3"
      />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 21h16" />
    </svg>
  );
}

function StrikethroughIcon() {
  return (
    <svg className="w-4 h-4 sm:w-5 sm:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M17.5 12h-11M12 4c-2.21 0-4 1.79-4 4 0 1.06.41 2.02 1.09 2.74M12 20c2.21 0 4-1.79 4-4 0-1.06-.41-2.02-1.09-2.74"
      />
    </svg>
  );
}

function BulletListIcon() {
  return (
    <svg className="w-4 h-4 sm:w-5 sm:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M8 6h13M8 12h13M8 18h13"
      />
      <circle cx="4" cy="6" r="1.5" fill="currentColor" />
      <circle cx="4" cy="12" r="1.5" fill="currentColor" />
      <circle cx="4" cy="18" r="1.5" fill="currentColor" />
    </svg>
  );
}

function NumberedListIcon() {
  return (
    <svg className="w-4 h-4 sm:w-5 sm:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M8 6h13M8 12h13M8 18h13"
      />
      <text x="2" y="8" fontSize="8" fill="currentColor" fontWeight="bold">
        1
      </text>
      <text x="2" y="14" fontSize="8" fill="currentColor" fontWeight="bold">
        2
      </text>
      <text x="2" y="20" fontSize="8" fill="currentColor" fontWeight="bold">
        3
      </text>
    </svg>
  );
}

function QuoteIcon() {
  return (
    <svg className="w-4 h-4 sm:w-5 sm:h-5" fill="currentColor" viewBox="0 0 24 24">
      <path d="M6 17h3l2-4V7H5v6h3l-2 4zm8 0h3l2-4V7h-6v6h3l-2 4z" />
    </svg>
  );
}

function CodeBlockIcon() {
  return (
    <svg className="w-4 h-4 sm:w-5 sm:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"
      />
    </svg>
  );
}

function LinkIcon() {
  return (
    <svg className="w-4 h-4 sm:w-5 sm:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
      />
    </svg>
  );
}

function UndoIcon() {
  return (
    <svg className="w-4 h-4 sm:w-5 sm:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6"
      />
    </svg>
  );
}

function RedoIcon() {
  return (
    <svg className="w-4 h-4 sm:w-5 sm:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M21 10h-10a8 8 0 00-8 8v2M21 10l-6 6m6-6l-6-6"
      />
    </svg>
  );
}
