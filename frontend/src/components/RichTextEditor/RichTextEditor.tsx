'use client';

import { useId, useEffect } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import { useTranslation } from 'react-i18next';
import { getFullEditorExtensions } from './extensions';
import { Toolbar } from './Toolbar';
import type { RichTextEditorProps } from '@/types/editor';
import './styles.css';

export function RichTextEditor({
  value,
  onChange,
  placeholder,
  label,
  disabled = false,
  error = false,
  success = false,
  helperText,
  minHeight = 200,
  maxLength = 0,
  showCharacterCount = true,
  className = '',
  id,
}: RichTextEditorProps) {
  const { t } = useTranslation();
  const generatedId = useId();
  const editorId = id || generatedId;

  // Resolve placeholder (translation key or direct text)
  const resolvedPlaceholder = placeholder?.startsWith('editor.')
    ? t(placeholder)
    : placeholder || t('editor.placeholder');

  const editor = useEditor({
    extensions: getFullEditorExtensions({
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
        'aria-label': label || t('editor.placeholder'),
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
        <label
          htmlFor={editorId}
          className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2"
        >
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
        <Toolbar editor={editor} mode="full" />
        <EditorContent editor={editor} />
      </div>

      {/* Helper text and character count */}
      <div className="mt-1.5 flex justify-between items-center">
        {helperText && (
          <p
            className={`text-sm ${
              error
                ? 'text-error-600 dark:text-error-400'
                : success
                  ? 'text-success-600 dark:text-success-400'
                  : 'text-gray-500 dark:text-gray-400'
            }`}
          >
            {helperText}
          </p>
        )}
        {showCharacterCount && (
          <p
            className={`text-sm ml-auto ${
              maxLength > 0 && characterCount > maxLength * 0.9
                ? 'text-error-600 dark:text-error-400'
                : 'text-gray-500 dark:text-gray-400'
            }`}
          >
            {maxLength > 0
              ? t('editor.characterCount', { count: characterCount }) + ` / ${maxLength}`
              : t('editor.characterCount', { count: characterCount })}
          </p>
        )}
      </div>
    </div>
  );
}
