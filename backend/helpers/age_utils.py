"""
Age calculation utilities for Law 25 compliance.

Provides accurate age calculation for parental consent requirements.
"""

from datetime import date, datetime, timezone


def calculate_age(date_of_birth: date | datetime) -> int:
    """
    Calculate age from date of birth.

    Handles edge cases:
    - Leap years (Feb 29 birthdays)
    - Timezone-aware datetimes

    Args:
        date_of_birth: Birth date (date or datetime object)

    Returns:
        Age in complete years

    Example:
        >>> from datetime import date
        >>> calculate_age(date(2010, 6, 15))  # If today is 2024-06-14
        13
        >>> calculate_age(date(2010, 6, 15))  # If today is 2024-06-15
        14
    """
    if isinstance(date_of_birth, datetime):
        # Convert datetime to date in UTC
        if date_of_birth.tzinfo is not None:
            date_of_birth = date_of_birth.astimezone(timezone.utc).date()
        else:
            date_of_birth = date_of_birth.date()

    today = date.today()

    # Calculate raw year difference
    age = today.year - date_of_birth.year

    # Check if birthday hasn't occurred yet this year
    birthday_this_year = date_of_birth.replace(year=today.year)

    # Handle Feb 29 birthdays in non-leap years
    try:
        birthday_this_year = date_of_birth.replace(year=today.year)
    except ValueError:
        # Feb 29 in a non-leap year - use Feb 28
        birthday_this_year = date(today.year, 2, 28)

    if today < birthday_this_year:
        age -= 1

    return age


def is_minor(date_of_birth: date | datetime, age_of_majority: int = 14) -> bool:
    """
    Check if a person is considered a minor.

    For Law 25 Quebec compliance, the age threshold for requiring
    parental consent is 14 years old.

    Args:
        date_of_birth: Birth date
        age_of_majority: Age threshold (default: 14 for Quebec Law 25)

    Returns:
        True if person is under the age threshold
    """
    return calculate_age(date_of_birth) < age_of_majority


def requires_parental_consent(date_of_birth: date | datetime) -> bool:
    """
    Check if user requires parental consent.

    Law 25 (Quebec): Children under 14 require parental consent
    for collection of personal information.

    Args:
        date_of_birth: User's birth date

    Returns:
        True if parental consent is required
    """
    return is_minor(date_of_birth, age_of_majority=14)
