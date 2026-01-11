'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/store/authStore';
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command';
import { HomeIcon, FileTextIcon, PlusIcon, PersonIcon, GearIcon } from '@radix-ui/react-icons';

export function CommandPalette() {
  const [open, setOpen] = React.useState(false);
  const router = useRouter();
  const { t } = useTranslation();
  const { user } = useAuthStore();

  React.useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };

    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, []);

  const runCommand = React.useCallback((command: () => void) => {
    setOpen(false);
    command();
  }, []);

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput
        placeholder={t('commandPalette.searchPlaceholder', 'Type a command or search...')}
      />
      <CommandList>
        <CommandEmpty>{t('commandPalette.noResults', 'No results found.')}</CommandEmpty>

        <CommandGroup heading={t('commandPalette.navigation', 'Navigation')}>
          <CommandItem onSelect={() => runCommand(() => router.push('/'))}>
            <HomeIcon className="mr-2 h-4 w-4" />
            {t('nav.home')}
          </CommandItem>
          {user && (
            <>
              <CommandItem onSelect={() => runCommand(() => router.push('/my-ideas'))}>
                <FileTextIcon className="mr-2 h-4 w-4" />
                {t('nav.myIdeas')}
              </CommandItem>
              <CommandItem onSelect={() => runCommand(() => router.push('/submit'))}>
                <PlusIcon className="mr-2 h-4 w-4" />
                {t('nav.submitIdea')}
              </CommandItem>
              <CommandItem onSelect={() => runCommand(() => router.push('/profile'))}>
                <PersonIcon className="mr-2 h-4 w-4" />
                {t('profile.title')}
              </CommandItem>
            </>
          )}
        </CommandGroup>

        {user?.is_global_admin && (
          <>
            <CommandSeparator />
            <CommandGroup heading={t('commandPalette.admin', 'Administration')}>
              <CommandItem onSelect={() => runCommand(() => router.push('/admin'))}>
                <GearIcon className="mr-2 h-4 w-4" />
                {t('nav.moderation')}
              </CommandItem>
              <CommandItem onSelect={() => runCommand(() => router.push('/admin/categories'))}>
                {t('nav.categories')}
              </CommandItem>
              <CommandItem onSelect={() => runCommand(() => router.push('/admin/users'))}>
                {t('nav.users')}
              </CommandItem>
            </CommandGroup>
          </>
        )}

        {!user && (
          <>
            <CommandSeparator />
            <CommandGroup heading={t('commandPalette.account', 'Account')}>
              <CommandItem onSelect={() => runCommand(() => router.push('/signin'))}>
                {t('nav.signIn')}
              </CommandItem>
              <CommandItem onSelect={() => runCommand(() => router.push('/signup'))}>
                {t('nav.signUp')}
              </CommandItem>
            </CommandGroup>
          </>
        )}
      </CommandList>
    </CommandDialog>
  );
}
