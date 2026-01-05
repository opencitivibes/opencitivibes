'use client';

import { useState, useEffect } from 'react';
import { X, Plus } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Button } from '@/components/Button';
import api from '@/lib/api';

interface Tag {
  id: number;
  name: string;
  display_name: string;
}

interface TagInputProps {
  selectedTags: string[];
  onTagsChange: (tags: string[]) => void;
  maxTags?: number;
  placeholder?: string;
}

export default function TagInput({
  selectedTags,
  onTagsChange,
  maxTags = 10,
  placeholder,
}: TagInputProps) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [suggestions, setSuggestions] = useState<Tag[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const displayPlaceholder = placeholder || t('ideas.addTags');

  // Search for tag suggestions
  useEffect(() => {
    const searchTags = async () => {
      if (searchQuery.length < 1) {
        setSuggestions([]);
        return;
      }

      setIsSearching(true);
      try {
        const response = await api.get(
          `/tags/search?q=${encodeURIComponent(searchQuery)}&limit=10`
        );
        // Filter out already selected tags
        const filtered = response.data.filter(
          (tag: Tag) => !selectedTags.includes(tag.display_name)
        );
        setSuggestions(filtered);
      } catch (error) {
        console.error('Error searching tags:', error);
        setSuggestions([]);
      } finally {
        setIsSearching(false);
      }
    };

    const debounce = setTimeout(searchTags, 300);
    return () => clearTimeout(debounce);
  }, [searchQuery, selectedTags]);

  const addTag = (tagName: string) => {
    if (selectedTags.length >= maxTags) {
      return;
    }

    const trimmedTag = tagName.trim();
    if (trimmedTag && !selectedTags.includes(trimmedTag)) {
      onTagsChange([...selectedTags, trimmedTag]);
      setSearchQuery('');
      setSuggestions([]);
    }
  };

  const removeTag = (tagToRemove: string) => {
    onTagsChange(selectedTags.filter((tag) => tag !== tagToRemove));
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && searchQuery.trim()) {
      e.preventDefault();
      addTag(searchQuery);
      setOpen(false);
    }
  };

  return (
    <div className="space-y-2">
      {/* Selected Tags Display */}
      {selectedTags.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {selectedTags.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center gap-1 px-3 py-1 text-sm bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 rounded-full"
            >
              {tag}
              <button
                type="button"
                onClick={() => removeTag(tag)}
                className="hover:text-primary-900 dark:hover:text-primary-200 focus:outline-none"
                aria-label={t('tags.removeTag', { tag })}
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Tag Input with Autocomplete */}
      {selectedTags.length < maxTags && (
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger asChild>
            <Button
              type="button"
              variant="secondary"
              className="w-full justify-start text-left font-normal"
            >
              <Plus className="mr-2 h-4 w-4" />
              {displayPlaceholder}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-full p-0" align="start">
            <Command shouldFilter={false}>
              <CommandInput
                placeholder={t('tags.searchPlaceholder')}
                value={searchQuery}
                onValueChange={setSearchQuery}
                onKeyDown={handleKeyDown}
              />
              <CommandList>
                {isSearching ? (
                  <CommandEmpty>{t('tags.searching')}</CommandEmpty>
                ) : searchQuery.length === 0 ? (
                  <CommandEmpty>{t('tags.startTyping')}</CommandEmpty>
                ) : suggestions.length === 0 ? (
                  <CommandGroup>
                    <CommandItem
                      onSelect={() => {
                        addTag(searchQuery);
                        setOpen(false);
                      }}
                    >
                      <Plus className="mr-2 h-4 w-4" />
                      {t('tags.createTag', { tag: searchQuery })}
                    </CommandItem>
                  </CommandGroup>
                ) : (
                  <>
                    <CommandGroup heading={t('tags.existingTags')}>
                      {suggestions.map((tag) => (
                        <CommandItem
                          key={tag.id}
                          onSelect={() => {
                            addTag(tag.display_name);
                            setOpen(false);
                          }}
                        >
                          {tag.display_name}
                        </CommandItem>
                      ))}
                    </CommandGroup>
                    {searchQuery.trim() &&
                      !suggestions.find(
                        (t) => t.display_name.toLowerCase() === searchQuery.toLowerCase()
                      ) && (
                        <CommandGroup>
                          <CommandItem
                            onSelect={() => {
                              addTag(searchQuery);
                              setOpen(false);
                            }}
                          >
                            <Plus className="mr-2 h-4 w-4" />
                            {t('tags.createTag', { tag: searchQuery })}
                          </CommandItem>
                        </CommandGroup>
                      )}
                  </>
                )}
              </CommandList>
            </Command>
          </PopoverContent>
        </Popover>
      )}

      {/* Helper Text */}
      <p className="text-sm text-gray-500 dark:text-gray-400">
        {t('tags.tagLimit', { current: selectedTags.length, max: maxTags })}{' '}
        {selectedTags.length < maxTags && `(${t('tags.pressEnter')})`}
      </p>
    </div>
  );
}
