'use client';

import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { StickyNote, Plus, Edit, Trash2, Loader2, Save, X } from 'lucide-react';
import { adminModerationAPI } from '@/lib/api';
import { useToast } from '@/hooks/useToast';
import { useLocalizedField } from '@/hooks/useLocalizedField';
import { Button } from '@/components/Button';
import { Textarea } from '@/components/Textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatDistanceToNow } from 'date-fns';
import type { AdminNote } from '@/types/moderation';

interface AdminNotesPanelProps {
  userId: number;
}

export function AdminNotesPanel({ userId }: AdminNotesPanelProps) {
  const { t } = useTranslation();
  const { success, error: toastError } = useToast();
  const { getDisplayName } = useLocalizedField();

  const [notes, setNotes] = useState<AdminNote[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isAdding, setIsAdding] = useState(false);
  const [newNoteContent, setNewNoteContent] = useState('');
  const [editingNoteId, setEditingNoteId] = useState<number | null>(null);
  const [editContent, setEditContent] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const loadNotes = useCallback(async () => {
    try {
      const data = await adminModerationAPI.getUserNotes(userId);
      setNotes(data);
    } catch (err) {
      console.error('Failed to load notes:', err);
      toastError(t('toast.error'), { isRaw: true });
    } finally {
      setIsLoading(false);
    }
  }, [userId, t, toastError]);

  useEffect(() => {
    loadNotes();
  }, [loadNotes]);

  const handleAddNote = async () => {
    if (!newNoteContent.trim()) return;

    setIsSaving(true);
    try {
      const note = await adminModerationAPI.addUserNote(userId, newNoteContent);
      setNotes([note, ...notes]);
      setNewNoteContent('');
      setIsAdding(false);
      success(t('adminModeration.notes.noteAdded'), { isRaw: true });
    } catch (err) {
      console.error('Failed to add note:', err);
      toastError(t('toast.error'), { isRaw: true });
    } finally {
      setIsSaving(false);
    }
  };

  const handleUpdateNote = async (noteId: number) => {
    if (!editContent.trim()) return;

    setIsSaving(true);
    try {
      const updated = await adminModerationAPI.updateNote(noteId, editContent);
      setNotes(notes.map((n) => (n.id === noteId ? updated : n)));
      setEditingNoteId(null);
      setEditContent('');
      success(t('adminModeration.notes.noteUpdated'), { isRaw: true });
    } catch (err) {
      console.error('Failed to update note:', err);
      toastError(t('toast.error'), { isRaw: true });
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteNote = async (noteId: number) => {
    if (!confirm(t('adminModeration.notes.deleteConfirm'))) return;

    try {
      await adminModerationAPI.deleteNote(noteId);
      setNotes(notes.filter((n) => n.id !== noteId));
      success(t('adminModeration.notes.noteDeleted'), { isRaw: true });
    } catch (err) {
      console.error('Failed to delete note:', err);
      toastError(t('toast.error'), { isRaw: true });
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <StickyNote className="h-5 w-5" />
          {t('adminModeration.notes.title')}
        </CardTitle>
        <Button variant="secondary" size="sm" onClick={() => setIsAdding(true)} disabled={isAdding}>
          <Plus className="h-4 w-4 mr-1" />
          {t('adminModeration.notes.add')}
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {isAdding && (
          <div className="space-y-2 border-b border-gray-200 pb-4">
            <Textarea
              value={newNoteContent}
              onChange={(e) => setNewNoteContent(e.target.value)}
              placeholder={t('adminModeration.notes.placeholder')}
              rows={3}
            />
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={handleAddNote}
                disabled={isSaving || !newNoteContent.trim()}
              >
                {isSaving && <Loader2 className="h-4 w-4 animate-spin mr-1" />}
                <Save className="h-4 w-4 mr-1" />
                {t('common.save')}
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setIsAdding(false);
                  setNewNoteContent('');
                }}
              >
                <X className="h-4 w-4 mr-1" />
                {t('common.cancel')}
              </Button>
            </div>
          </div>
        )}

        {isLoading ? (
          <div className="text-center py-4">
            <Loader2 className="h-6 w-6 animate-spin mx-auto text-gray-400" />
          </div>
        ) : notes.length === 0 ? (
          <p className="text-gray-500 text-center py-4">{t('adminModeration.notes.empty')}</p>
        ) : (
          notes.map((note) => (
            <div key={note.id} className="border-b border-gray-100 pb-4 last:border-0">
              {editingNoteId === note.id ? (
                <div className="space-y-2">
                  <Textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    rows={3}
                  />
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      onClick={() => handleUpdateNote(note.id)}
                      disabled={isSaving || !editContent.trim()}
                    >
                      {isSaving && <Loader2 className="h-4 w-4 animate-spin mr-1" />}
                      <Save className="h-4 w-4 mr-1" />
                      {t('common.save')}
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        setEditingNoteId(null);
                        setEditContent('');
                      }}
                    >
                      <X className="h-4 w-4 mr-1" />
                      {t('common.cancel')}
                    </Button>
                  </div>
                </div>
              ) : (
                <>
                  <p className="text-sm text-gray-800 whitespace-pre-wrap">{note.content}</p>
                  <div className="flex justify-between items-center mt-2">
                    <p className="text-xs text-gray-500">
                      {getDisplayName(note.author_display_name)} -{' '}
                      {formatDistanceToNow(new Date(note.created_at), {
                        addSuffix: true,
                      })}
                    </p>
                    <div className="flex gap-1">
                      <Button
                        variant="secondary"
                        size="sm"
                        className="h-7 w-7 p-0"
                        onClick={() => {
                          setEditingNoteId(note.id);
                          setEditContent(note.content);
                        }}
                      >
                        <Edit className="h-3 w-3" />
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        className="h-7 w-7 p-0 text-error-600 hover:text-error-700"
                        onClick={() => handleDeleteNote(note.id)}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                </>
              )}
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
