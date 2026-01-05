'use client';

import { useId, useEffect } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import { useTranslation } from 'react-i18next';
import { getSimpleEditorExtensions } from './extensions';
import { Toolbar } from './Toolbar';
import type { SimpleRichTextEditorProps } from '@/types/editor';
import './styles.css';

export function SimpleRichTextEditor({
  value,
  onChange,
  placeholder,
  label,
  disabled = false,
  error = false,
  success = false,
  helperText,
  rows = 3,
  maxLength = 0,
  showCharacterCount = false,
  className = '',
  id,
}: SimpleRichTextEditorProps) {
  const { t } = useTranslation();
  const generatedId = useId();
  const editorId = id || generatedId;

  // Resolve placeholder
  const resolvedPlaceholder = placeholder?.startsWith('editor.')
    ? t(placeholder)
    : placeholder || t('editor.placeholderComment');

  // Calculate min height based on rows (approximate)
  const minHeight = rows * 28; // ~28px per row

  const editor = useEditor({
    extensions: getSimpleEditorExtensions({
      placeholder: resolvedPlaceholder,
      maxLength,
    }),
    content: value,
    editable: !disabled,
    immediatelyRender: false, // Prevent SSR hydration mismatch
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML());
    },
    editorProps: {
      attributes: {
        id: editorId,
        'aria-label': label || t('editor.placeholderComment'),
        role: 'textbox',
        'aria-multiline': 'true',
        style: `min-height: ${minHeight}px`,
      },
    },
  });

  // Update content when value prop changes externally
  useEffect(() => {
    if (editor && value !== editor.getHTML()) {
      editor.commands.setContent(value, { emitUpdate: false });
    }
  }, [value, editor]);

  // Update editable state when disabled changes
  useEffect(() => {
    if (editor) {
      editor.setEditable(!disabled);
    }
  }, [disabled, editor]);

  const characterCount = editor?.storage.characterCount?.characters() || 0;

  return (
    <div className={`w-full ${className}`}>
      {label && (
        <label htmlFor={editorId} className="block text-sm font-medium text-gray-700 mb-2">
          {label}
        </label>
      )}

      <div
        className={`
          rich-text-editor
          ${error ? 'error' : ''}
          ${success ? 'success' : ''}
          ${disabled ? 'disabled' : ''}
        `}
      >
        <Toolbar editor={editor} mode="simple" />
        <EditorContent editor={editor} />
      </div>

      {/* Helper text and character count */}
      {(helperText || showCharacterCount) && (
        <div className="mt-1.5 flex justify-between items-center">
          {helperText && (
            <p
              className={`text-sm ${
                error ? 'text-error-600' : success ? 'text-success-600' : 'text-gray-500'
              }`}
            >
              {helperText}
            </p>
          )}
          {showCharacterCount && (
            <p
              className={`text-sm ml-auto ${
                maxLength > 0 && characterCount > maxLength * 0.9
                  ? 'text-error-600'
                  : 'text-gray-500'
              }`}
            >
              {maxLength > 0 ? `${characterCount} / ${maxLength}` : characterCount}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
