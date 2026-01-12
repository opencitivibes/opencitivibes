/**
 * Age calculation utility for Law 25 minors protection
 * Quebec Law 25 requires parental consent for users under 14
 */

/**
 * Calculate age in years from a date of birth
 * Handles edge cases like leap years and time zones
 *
 * @param dob - Date of birth
 * @returns Age in complete years
 */
export function calculateAge(dob: Date): number {
  const today = new Date();

  // Normalize both dates to midnight UTC to avoid timezone issues
  const birthDate = new Date(Date.UTC(dob.getFullYear(), dob.getMonth(), dob.getDate()));
  const currentDate = new Date(Date.UTC(today.getFullYear(), today.getMonth(), today.getDate()));

  let age = currentDate.getUTCFullYear() - birthDate.getUTCFullYear();

  // Check if birthday hasn't occurred yet this year
  const monthDiff = currentDate.getUTCMonth() - birthDate.getUTCMonth();
  if (monthDiff < 0 || (monthDiff === 0 && currentDate.getUTCDate() < birthDate.getUTCDate())) {
    age--;
  }

  return age;
}

/**
 * Check if a user is a minor under Quebec Law 25 (under 14)
 *
 * @param dob - Date of birth
 * @returns true if user is under 14
 */
export function isMinorRequiringConsent(dob: Date): boolean {
  const age = calculateAge(dob);
  return age < 14;
}

/**
 * Get the minimum valid date of birth (100 years ago)
 * Used for form validation
 *
 * @returns Date 100 years ago from today
 */
export function getMinDateOfBirth(): Date {
  const today = new Date();
  return new Date(today.getFullYear() - 100, today.getMonth(), today.getDate());
}

/**
 * Get the maximum valid date of birth (today)
 * No future dates allowed
 *
 * @returns Today's date
 */
export function getMaxDateOfBirth(): Date {
  return new Date();
}

/**
 * Format a Date to ISO date string (YYYY-MM-DD) for HTML date input
 *
 * @param date - Date to format
 * @returns ISO date string
 */
export function formatDateForInput(date: Date): string {
  const isoString = date.toISOString();
  const datePart = isoString.split('T')[0];
  return datePart ?? isoString.substring(0, 10);
}

/**
 * Parse an ISO date string to Date object
 * Returns null if invalid
 *
 * @param dateString - ISO date string (YYYY-MM-DD)
 * @returns Date object or null if invalid
 */
export function parseDateString(dateString: string): Date | null {
  if (!dateString || !/^\d{4}-\d{2}-\d{2}$/.test(dateString)) {
    return null;
  }

  const date = new Date(dateString + 'T00:00:00');

  // Check if the date is valid
  if (isNaN(date.getTime())) {
    return null;
  }

  return date;
}
