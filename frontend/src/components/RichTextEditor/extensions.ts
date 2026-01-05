import StarterKit from '@tiptap/starter-kit';
import Link from '@tiptap/extension-link';
import Underline from '@tiptap/extension-underline';
import Placeholder from '@tiptap/extension-placeholder';
import CharacterCount from '@tiptap/extension-character-count';

export interface ExtensionsConfig {
  placeholder?: string;
  maxLength?: number;
  mode?: 'full' | 'simple';
}

/**
 * Get Tiptap extensions for full editor (ideas)
 */
export function getFullEditorExtensions(config: ExtensionsConfig = {}) {
  const { placeholder = '', maxLength = 0 } = config;

  return [
    StarterKit.configure({
      // Customize starter kit
      heading: {
        levels: [2, 3],
      },
      // Disable features we don't want
      horizontalRule: false,
    }),
    Underline,
    Link.configure({
      openOnClick: false, // Don't open links while editing
      HTMLAttributes: {
        target: '_blank',
        rel: 'noopener noreferrer',
        class: 'text-primary-600 underline hover:text-primary-700',
      },
    }),
    Placeholder.configure({
      placeholder,
      emptyEditorClass: 'is-editor-empty',
    }),
    ...(maxLength > 0 ? [CharacterCount.configure({ limit: maxLength })] : [CharacterCount]),
  ];
}

/**
 * Get Tiptap extensions for simple editor (comments)
 */
export function getSimpleEditorExtensions(config: ExtensionsConfig = {}) {
  const { placeholder = '', maxLength = 0 } = config;

  return [
    StarterKit.configure({
      // Disable most features for simple editor
      heading: false,
      blockquote: false,
      codeBlock: false,
      horizontalRule: false,
      bulletList: false,
      orderedList: false,
      listItem: false,
    }),
    Link.configure({
      openOnClick: false,
      HTMLAttributes: {
        target: '_blank',
        rel: 'noopener noreferrer',
        class: 'text-primary-600 underline hover:text-primary-700',
      },
    }),
    Placeholder.configure({
      placeholder,
      emptyEditorClass: 'is-editor-empty',
    }),
    ...(maxLength > 0 ? [CharacterCount.configure({ limit: maxLength })] : [CharacterCount]),
  ];
}
