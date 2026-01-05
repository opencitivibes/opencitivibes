/**
 * Moderation system types for content flagging and user penalties.
 */

// Enums matching backend
export type FlagReason =
  | 'spam'
  | 'hate_speech'
  | 'harassment'
  | 'off_topic'
  | 'misinformation'
  | 'other';

export type FlagStatus = 'pending' | 'dismissed' | 'actioned';

export type ContentType = 'comment' | 'idea';

export type PenaltyType =
  | 'warning'
  | 'temp_ban_24h'
  | 'temp_ban_7d'
  | 'temp_ban_30d'
  | 'permanent_ban';

export type PenaltyStatus = 'active' | 'expired' | 'appealed' | 'revoked';

export type AppealStatus = 'pending' | 'approved' | 'rejected';

// Flag interfaces
export interface FlagCreate {
  content_type: ContentType;
  content_id: number;
  reason: FlagReason;
  details?: string;
}

export interface FlagResponse {
  id: number;
  content_type: ContentType;
  content_id: number;
  reporter_id: number;
  reason: FlagReason;
  details?: string;
  status: FlagStatus;
  created_at: string;
}

export interface FlagCheckResponse {
  flagged: boolean;
}

// Penalty interfaces
export interface PenaltyResponse {
  id: number;
  user_id: number;
  penalty_type: PenaltyType;
  reason: string;
  status: PenaltyStatus;
  issued_by: number;
  issued_at: string;
  expires_at?: string;
}

export interface UserBanInfo {
  is_banned: boolean;
  penalty?: PenaltyResponse;
  expires_at?: string;
  can_appeal: boolean;
}

// Appeal interfaces
export interface AppealCreate {
  penalty_id: number;
  reason: string;
}

export interface AppealResponse {
  id: number;
  penalty_id: number;
  user_id: number;
  reason: string;
  status: AppealStatus;
  created_at: string;
  reviewed_at?: string;
  review_notes?: string;
}

// ============================================================================
// Admin Moderation Types
// ============================================================================

export interface FlagWithReporter {
  id: number;
  content_type: ContentType;
  content_id: number;
  reporter_id: number;
  reporter_username: string;
  reporter_display_name: string;
  reason: FlagReason;
  details?: string;
  status: FlagStatus;
  created_at: string;
}

export interface ModerationQueueItem {
  content_type: ContentType;
  content_id: number;
  content_text: string;
  content_author_id: number;
  content_author_username: string;
  content_created_at: string;
  flag_count: number;
  is_hidden: boolean;
  flags: FlagWithReporter[];
  author_trust_score: number;
  author_total_flags: number;
  idea_id?: number; // For comments: links to parent idea
}

export interface ModerationQueueResponse {
  items: ModerationQueueItem[];
  total: number;
  pending_count: number;
}

export interface FlaggedUserSummary {
  user_id: number;
  username: string;
  display_name: string;
  trust_score: number;
  total_flags_received: number;
  valid_flags_received: number;
  pending_flags_count: number;
  has_active_penalty: boolean;
  active_penalty_type?: PenaltyType;
}

export interface ModerationStats {
  total_flags: number;
  pending_flags: number;
  resolved_today: number;
  flags_by_reason: Record<string, number>;
  flags_by_day: Array<{ date: string; count: number }>;
  top_flagged_users: FlaggedUserSummary[];
  active_penalties: number;
  pending_appeals: number;
}

export interface AdminNote {
  id: number;
  user_id: number;
  content: string;
  created_by: number;
  created_at: string;
  updated_at?: string;
  author_username: string;
  author_display_name: string;
}

export interface KeywordEntry {
  id: number;
  keyword: string;
  is_regex: boolean;
  auto_flag_reason: FlagReason;
  is_active: boolean;
  match_count: number;
  created_at: string;
}

export interface PendingComment {
  id: number;
  idea_id: number;
  content: string;
  created_at: string;
  author_username: string;
  author_display_name: string;
}

// Localized label type supporting all languages
export type LocalizedLabel = { en: string; fr: string; es: string };

// Label mappings for UI display
export const FLAG_REASON_LABELS: Record<FlagReason, LocalizedLabel> = {
  spam: { en: 'Spam/Advertising', fr: 'Spam/Publicité', es: 'Spam/Publicidad' },
  hate_speech: {
    en: 'Hate Speech/Discrimination',
    fr: 'Discours haineux/Discrimination',
    es: 'Discurso de odio/Discriminación',
  },
  harassment: {
    en: 'Harassment/Personal Attacks',
    fr: 'Harcèlement/Attaques personnelles',
    es: 'Acoso/Ataques personales',
  },
  off_topic: {
    en: 'Off-topic/Not Constructive',
    fr: 'Hors sujet/Non constructif',
    es: 'Fuera de tema/No constructivo',
  },
  misinformation: { en: 'Misinformation', fr: 'Désinformation', es: 'Desinformación' },
  other: { en: 'Other', fr: 'Autre', es: 'Otro' },
};

export const PENALTY_TYPE_LABELS: Record<PenaltyType, LocalizedLabel> = {
  warning: { en: 'Warning', fr: 'Avertissement', es: 'Advertencia' },
  temp_ban_24h: {
    en: '24-hour Ban',
    fr: 'Suspension de 24 heures',
    es: 'Suspensión de 24 horas',
  },
  temp_ban_7d: { en: '7-day Ban', fr: 'Suspension de 7 jours', es: 'Suspensión de 7 días' },
  temp_ban_30d: { en: '30-day Ban', fr: 'Suspension de 30 jours', es: 'Suspensión de 30 días' },
  permanent_ban: { en: 'Permanent Ban', fr: 'Bannissement permanent', es: 'Suspensión permanente' },
};

/**
 * Get a localized label from a label object.
 * Falls back to English if the requested locale is not available.
 */
export function getLocalizedLabel(labels: LocalizedLabel, locale: string): string {
  return labels[locale as keyof LocalizedLabel] || labels.en;
}
