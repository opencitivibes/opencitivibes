"""Email service for sending transactional emails.

This module provides a unified interface for sending emails through various providers.
Supports:
- console: Logs emails to console (development)
- smtp: Standard SMTP delivery
- sendgrid: SendGrid API (requires sendgrid package)

Security features (addressing audit findings):
- Finding #7 (MEDIUM): Retry logic with exponential backoff
- Finding #12 (LOW): Template variable escaping and sanitization
"""

import html
import re
import smtplib
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from loguru import logger

from models.config import settings


class EmailProvider(ABC):
    """Abstract base class for email providers."""

    @abstractmethod
    def send(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> bool:
        """Send an email."""
        pass


class SMTPProvider(EmailProvider):
    """SMTP email provider."""

    def __init__(self) -> None:
        """Initialize SMTP provider with settings."""
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL
        self.from_name = settings.SMTP_FROM_NAME
        self.use_tls = settings.SMTP_USE_TLS
        self.use_ssl = settings.SMTP_USE_SSL

    def send(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> bool:
        """Send email via SMTP.

        Supports both:
        - Implicit SSL (port 465): use SMTP_USE_SSL=true
        - STARTTLS (port 587): use SMTP_USE_TLS=true
        """
        try:
            logger.info(
                f"SMTP: Connecting to {self.host}:{self.port} "
                f"(SSL={self.use_ssl}, TLS={self.use_tls}, user={self.user})"
            )

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email

            msg.attach(MIMEText(text_body, "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            if self.use_ssl:
                # Implicit SSL (port 465) - connection is encrypted from start
                server = smtplib.SMTP_SSL(self.host, self.port)
            elif self.use_tls:
                # STARTTLS (port 587) - upgrade to TLS after connection
                server = smtplib.SMTP(self.host, self.port)
                server.starttls()
            else:
                # Plain SMTP (not recommended)
                server = smtplib.SMTP(self.host, self.port)

            # Enable debug output to capture SMTP conversation
            server.set_debuglevel(1)

            if self.user and self.password:
                logger.debug("SMTP: Authenticating...")
                server.login(self.user, self.password)
                logger.debug("SMTP: Authentication successful")

            logger.info(f"SMTP: Sending email from {self.from_email} to {to_email}")
            result = server.sendmail(self.from_email, to_email, msg.as_string())
            logger.info(f"SMTP: sendmail() returned: {result}")

            server.quit()

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"SMTP: Recipients refused - {e.recipients}")
            return False
        except smtplib.SMTPSenderRefused as e:
            logger.error(f"SMTP: Sender refused - {e.smtp_code}: {e.smtp_error}")
            return False
        except smtplib.SMTPDataError as e:
            logger.error(f"SMTP: Data error - {e.smtp_code}: {e.smtp_error}")
            return False
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP: Authentication failed - {e.smtp_code}: {e.smtp_error}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False


class ConsoleProvider(EmailProvider):
    """Console email provider for development/testing."""

    def send(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> bool:
        """Log email to console."""
        clean_html = re.sub(r"<[^>]+>", "", html_body)[:500]
        logger.info(
            f"\n{'=' * 60}\n"
            f"EMAIL (Console Provider - Development Mode)\n"
            f"{'=' * 60}\n"
            f"To: {to_email}\n"
            f"Subject: {subject}\n"
            f"{'-' * 60}\n"
            f"PLAIN TEXT:\n{text_body}\n"
            f"{'-' * 60}\n"
            f"HTML (preview):\n{clean_html}\n"
            f"{'=' * 60}\n"
        )
        return True


class SendGridProvider(EmailProvider):
    """SendGrid email provider (requires sendgrid package)."""

    def __init__(self) -> None:
        """Initialize SendGrid provider."""
        self.api_key = settings.SENDGRID_API_KEY
        self.from_email = settings.SMTP_FROM_EMAIL
        self.from_name = settings.SMTP_FROM_NAME

    def send(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> bool:
        """Send email via SendGrid API."""
        try:
            from sendgrid import SendGridAPIClient  # type: ignore[import-not-found]
            from sendgrid.helpers.mail import Content, Email, Mail, To  # type: ignore[import-not-found]

            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject=subject,
            )
            message.content = [
                Content("text/plain", text_body),
                Content("text/html", html_body),
            ]

            sg = SendGridAPIClient(self.api_key)
            response = sg.send(message)

            if response.status_code in (200, 202):
                logger.info(f"Email sent to {to_email} via SendGrid")
                return True
            else:
                logger.error(f"SendGrid returned status {response.status_code}")
                return False

        except ImportError:
            logger.error("SendGrid package not installed. Run: pip install sendgrid")
            return False
        except Exception as e:
            logger.error(f"Failed to send email via SendGrid: {e}")
            return False


def get_email_provider() -> EmailProvider:
    """Get the configured email provider."""
    provider_name = settings.EMAIL_PROVIDER.lower()

    if provider_name == "smtp":
        return SMTPProvider()
    elif provider_name == "sendgrid":
        return SendGridProvider()
    elif provider_name == "console":
        return ConsoleProvider()
    else:
        logger.warning(f"Unknown email provider '{provider_name}', using console")
        return ConsoleProvider()


class EmailService:
    """High-level email service with template support."""

    TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "emails"

    @classmethod
    def _load_template(cls, template_name: str, language: str) -> tuple[str, str]:
        """Load HTML and text templates with fallback to English."""
        if language not in ("en", "fr"):
            language = "en"

        html_path = cls.TEMPLATES_DIR / f"{template_name}_{language}.html"
        text_path = cls.TEMPLATES_DIR / f"{template_name}_{language}.txt"

        # Fallback to English
        if not html_path.exists():
            html_path = cls.TEMPLATES_DIR / f"{template_name}_en.html"
        if not text_path.exists():
            text_path = cls.TEMPLATES_DIR / f"{template_name}_en.txt"

        html = html_path.read_text(encoding="utf-8") if html_path.exists() else ""
        text = text_path.read_text(encoding="utf-8") if text_path.exists() else ""

        return html, text

    @classmethod
    def _render_template(cls, template: str, **kwargs: str | int) -> str:
        """Simple template rendering with {variable} substitution."""
        result = template
        for key, value in kwargs.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result

    @classmethod
    def _get_instance_name(cls) -> str:
        """Get instance name from platform config."""
        try:
            from services.config_service import get_config

            config = get_config()
            return config.instance.name.get("en", "OpenCitiVibes")
        except Exception:
            return "OpenCitiVibes"

    @classmethod
    def send_login_code(
        cls,
        to_email: str,
        code: str,
        display_name: str,
        language: str = "en",
        expires_minutes: int = 10,
    ) -> bool:
        """Send login code email using template or inline fallback."""
        html_template, text_template = cls._load_template("login_code", language)

        # Format code with spaces for readability (12 34 56)
        formatted_code = " ".join([code[i : i + 2] for i in range(0, len(code), 2)])
        app_name = cls._get_instance_name()

        context: dict[str, str | int] = {
            "display_name": display_name,
            "code": code,
            "formatted_code": formatted_code,
            "expires_minutes": expires_minutes,
            "app_name": app_name,
            "year": str(datetime.now().year),
        }

        # Use templates if available, otherwise fallback to inline
        if html_template and text_template:
            html_body = cls._render_template(html_template, **context)
            text_body = cls._render_template(text_template, **context)
        else:
            text_body, html_body = cls._build_inline_email(
                code, display_name, language, expires_minutes
            )

        subject = cls._get_subject(language, app_name)
        provider = get_email_provider()
        return provider.send(to_email, subject, html_body, text_body)

    @classmethod
    def _get_subject(cls, language: str, app_name: str) -> str:
        """Get email subject based on language."""
        subjects = {
            "en": f"Your {app_name} login code",
            "fr": f"Votre code de connexion {app_name}",
        }
        return subjects.get(language, subjects["en"])

    @staticmethod
    def _build_inline_email(
        code: str, display_name: str, language: str, expires_minutes: int
    ) -> tuple[str, str]:
        """Build inline email as fallback when templates not found."""
        if language == "fr":
            return EmailService._build_french_inline(
                code, display_name, expires_minutes
            )
        return EmailService._build_english_inline(code, display_name, expires_minutes)

    @staticmethod
    def _build_french_inline(
        code: str, display_name: str, expires_minutes: int
    ) -> tuple[str, str]:
        """Build French inline email (text, html)."""
        text = f"""Bonjour {display_name},

Votre code de connexion est : {code}

Ce code expire dans {expires_minutes} minutes.

Si vous n'avez pas demande ce code, ignorez cet email.

Cordialement,
L'equipe"""
        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
<h2 style="color: #333;">Votre code de connexion</h2>
<p>Bonjour {display_name},</p>
<div style="background: #f5f5f5; padding: 20px; text-align: center; margin: 20px 0; border-radius: 8px;">
<span style="font-size: 32px; letter-spacing: 8px; font-weight: bold; color: #333;">{code}</span>
</div>
<p>Ce code expire dans <strong>{expires_minutes} minutes</strong>.</p>
<p style="color: #666; font-size: 14px;">Si vous n'avez pas demande ce code, ignorez cet email.</p>
</body></html>"""
        return text, html

    @staticmethod
    def _build_english_inline(
        code: str, display_name: str, expires_minutes: int
    ) -> tuple[str, str]:
        """Build English inline email (text, html)."""
        text = f"""Hello {display_name},

Your login code is: {code}

This code expires in {expires_minutes} minutes.

If you didn't request this code, ignore this email.

Best regards,
The Team"""
        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
<h2 style="color: #333;">Your login code</h2>
<p>Hello {display_name},</p>
<div style="background: #f5f5f5; padding: 20px; text-align: center; margin: 20px 0; border-radius: 8px;">
<span style="font-size: 32px; letter-spacing: 8px; font-weight: bold; color: #333;">{code}</span>
</div>
<p>This code expires in <strong>{expires_minutes} minutes</strong>.</p>
<p style="color: #666; font-size: 14px;">If you didn't request this code, ignore this email.</p>
</body></html>"""
        return text, html

    # =========================================================================
    # Device Trust Email (Law 25 - User Awareness)
    # =========================================================================

    @classmethod
    def send_device_trusted_email(
        cls,
        to_email: str,
        device_name: str,
        trusted_at: "datetime",
        expires_at: "datetime",
        display_name: str,
        language: str = "fr",
    ) -> bool:
        """
        Send email notification when a device is trusted.

        Law 25 Compliance: Users must be informed when a device is trusted
        so they can take action if it wasn't them.

        Args:
            to_email: User's email address
            device_name: Name of the trusted device (e.g., "Chrome on Windows 10")
            trusted_at: When the device was trusted
            expires_at: When the trust expires
            display_name: User's display name
            language: User's preferred language (en/fr)

        Returns:
            True if email sent successfully, False otherwise
        """
        app_name = cls._get_instance_name()

        # Format dates for display
        trusted_date = trusted_at.strftime("%Y-%m-%d %H:%M UTC")
        expires_date = expires_at.strftime("%Y-%m-%d %H:%M UTC")

        if language == "fr":
            subject = f"Nouvel appareil de confiance ajouté - {app_name}"
            text_body, html_body = cls._build_device_trusted_french(
                display_name, device_name, trusted_date, expires_date, app_name
            )
        else:
            subject = f"New trusted device added - {app_name}"
            text_body, html_body = cls._build_device_trusted_english(
                display_name, device_name, trusted_date, expires_date, app_name
            )

        provider = get_email_provider()
        return provider.send(to_email, subject, html_body, text_body)

    @staticmethod
    def _build_device_trusted_french(
        display_name: str,
        device_name: str,
        trusted_date: str,
        expires_date: str,
        app_name: str,
    ) -> tuple[str, str]:
        """Build French device trusted email."""
        text = f"""Bonjour {display_name},

Un nouvel appareil a été ajouté à votre liste d'appareils de confiance pour la vérification en deux étapes.

Appareil: {device_name}
Date d'ajout: {trusted_date}
Expire le: {expires_date}

Si ce n'était pas vous, veuillez révoquer immédiatement cet appareil depuis vos paramètres de sécurité.

Pour gérer vos appareils de confiance, connectez-vous à votre compte et accédez à Paramètres > Sécurité > Appareils de confiance.

Cordialement,
L'équipe {app_name}"""

        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
<h2 style="color: #333;">Nouvel appareil de confiance</h2>
<p>Bonjour {display_name},</p>
<p>Un nouvel appareil a été ajouté à votre liste d'appareils de confiance pour la vérification en deux étapes.</p>
<div style="background: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 8px;">
<p><strong>Appareil:</strong> {device_name}</p>
<p><strong>Date d'ajout:</strong> {trusted_date}</p>
<p><strong>Expire le:</strong> {expires_date}</p>
</div>
<div style="background: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 8px; margin: 20px 0;">
<p style="margin: 0; color: #856404;">
<strong>⚠️ Si ce n'était pas vous</strong>, veuillez révoquer immédiatement cet appareil depuis vos paramètres de sécurité.
</p>
</div>
<p style="color: #666; font-size: 14px;">
Pour gérer vos appareils de confiance, connectez-vous à votre compte et accédez à<br>
<strong>Paramètres > Sécurité > Appareils de confiance</strong>
</p>
<p style="color: #666; font-size: 14px;">Cordialement,<br>L'équipe {app_name}</p>
</body></html>"""
        return text, html

    @staticmethod
    def _build_device_trusted_english(
        display_name: str,
        device_name: str,
        trusted_date: str,
        expires_date: str,
        app_name: str,
    ) -> tuple[str, str]:
        """Build English device trusted email."""
        text = f"""Hello {display_name},

A new device has been added to your trusted devices for two-factor authentication.

Device: {device_name}
Added on: {trusted_date}
Expires on: {expires_date}

If this wasn't you, please revoke this device immediately from your security settings.

To manage your trusted devices, log in to your account and go to Settings > Security > Trusted Devices.

Best regards,
The {app_name} Team"""

        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
<h2 style="color: #333;">New Trusted Device</h2>
<p>Hello {display_name},</p>
<p>A new device has been added to your trusted devices for two-factor authentication.</p>
<div style="background: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 8px;">
<p><strong>Device:</strong> {device_name}</p>
<p><strong>Added on:</strong> {trusted_date}</p>
<p><strong>Expires on:</strong> {expires_date}</p>
</div>
<div style="background: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 8px; margin: 20px 0;">
<p style="margin: 0; color: #856404;">
<strong>⚠️ If this wasn't you</strong>, please revoke this device immediately from your security settings.
</p>
</div>
<p style="color: #666; font-size: 14px;">
To manage your trusted devices, log in to your account and go to<br>
<strong>Settings > Security > Trusted Devices</strong>
</p>
<p style="color: #666; font-size: 14px;">Best regards,<br>The {app_name} Team</p>
</body></html>"""
        return text, html

    # =========================================================================
    # Password Reset Emails (Security Audit Phase 1)
    # =========================================================================

    @staticmethod
    def _sanitize_display_name(name: str) -> str:
        """
        Sanitize display name for safe use in emails (Finding #12).

        Removes potentially dangerous characters and limits length.

        Args:
            name: Raw display name from user input

        Returns:
            Sanitized display name safe for email templates
        """
        if not name:
            return "User"
        # Remove HTML/script tags and limit to reasonable length
        sanitized = re.sub(r"<[^>]+>", "", name)
        sanitized = sanitized.strip()[:100]
        return sanitized if sanitized else "User"

    @staticmethod
    def _escape_template_vars(text: str) -> str:
        """
        Escape HTML special characters in template variables (Finding #12).

        Args:
            text: Raw text that might contain user input

        Returns:
            HTML-escaped text safe for template insertion
        """
        return html.escape(str(text))

    @classmethod
    def _send_with_retry(
        cls,
        send_func: Callable[[], bool],
        max_attempts: int = 3,
        base_delay: float = 1.0,
    ) -> bool:
        """
        Send email with exponential backoff retry (Finding #7).

        Args:
            send_func: Function that sends the email and returns success status
            max_attempts: Maximum number of send attempts
            base_delay: Base delay in seconds (doubles each retry)

        Returns:
            True if email sent successfully, False after all attempts fail
        """
        for attempt in range(max_attempts):
            try:
                if send_func():
                    return True
            except Exception as e:
                logger.warning(f"Email send attempt {attempt + 1} failed: {e}")

            if attempt < max_attempts - 1:
                delay = base_delay * (2**attempt)
                logger.info(f"Retrying email in {delay}s...")
                time.sleep(delay)

        logger.error(f"Email send failed after {max_attempts} attempts")
        return False

    @classmethod
    def send_password_reset_code(
        cls,
        to_email: str,
        code: str,
        display_name: str,
        language: str = "en",
        expires_minutes: int = 30,
    ) -> bool:
        """
        Send password reset code email with retry logic.

        Args:
            to_email: User's email address
            code: The 6-digit reset code
            display_name: User's display name
            language: User's preferred language (en/fr)
            expires_minutes: Minutes until code expires

        Returns:
            True if email sent successfully
        """
        html_template, text_template = cls._load_template("password_reset", language)

        # Sanitize user input (Finding #12)
        safe_display_name = cls._sanitize_display_name(display_name)

        # Format code with spaces for readability (12 34 56)
        formatted_code = " ".join([code[i : i + 2] for i in range(0, len(code), 2)])
        app_name = cls._get_instance_name()

        context: dict[str, str | int] = {
            "display_name": safe_display_name,
            "code": code,
            "formatted_code": formatted_code,
            "expires_minutes": expires_minutes,
            "app_name": app_name,
            "year": str(datetime.now().year),
        }

        # Use templates if available, otherwise fallback to inline
        if html_template and text_template:
            html_body = cls._render_template(html_template, **context)
            text_body = cls._render_template(text_template, **context)
        else:
            text_body, html_body = cls._build_password_reset_inline(
                code, safe_display_name, language, expires_minutes, app_name
            )

        subject = cls._get_password_reset_subject(language, app_name)
        provider = get_email_provider()

        # Use retry logic (Finding #7)
        return cls._send_with_retry(
            lambda: provider.send(to_email, subject, html_body, text_body)
        )

    @classmethod
    def _get_password_reset_subject(cls, language: str, app_name: str) -> str:
        """Get password reset email subject based on language."""
        subjects = {
            "en": f"Password reset code - {app_name}",
            "fr": f"Code de reinitialisation - {app_name}",
        }
        return subjects.get(language, subjects["en"])

    @staticmethod
    def _build_password_reset_inline(
        code: str,
        display_name: str,
        language: str,
        expires_minutes: int,
        app_name: str,
    ) -> tuple[str, str]:
        """Build inline password reset email as fallback when templates not found."""
        if language == "fr":
            text = f"""Bonjour {display_name},

Votre code de reinitialisation de mot de passe est : {code}

Ce code expire dans {expires_minutes} minutes.

Si vous n'avez pas demande cette reinitialisation, ignorez ce courriel.

Cordialement,
L'equipe {app_name}"""
            html_content = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
<h2 style="color: #333;">Reinitialisation du mot de passe</h2>
<p>Bonjour {display_name},</p>
<div style="background: #f5f5f5; padding: 20px; text-align: center; margin: 20px 0; border-radius: 8px;">
<span style="font-size: 32px; letter-spacing: 8px; font-weight: bold; color: #dc2626;">{code}</span>
</div>
<p>Ce code expire dans <strong>{expires_minutes} minutes</strong>.</p>
<p style="color: #666; font-size: 14px;">Si vous n'avez pas demande cette reinitialisation, ignorez ce courriel.</p>
</body></html>"""
        else:
            text = f"""Hello {display_name},

Your password reset code is: {code}

This code expires in {expires_minutes} minutes.

If you did not request this reset, ignore this email.

Best regards,
The {app_name} Team"""
            html_content = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
<h2 style="color: #333;">Password Reset</h2>
<p>Hello {display_name},</p>
<div style="background: #f5f5f5; padding: 20px; text-align: center; margin: 20px 0; border-radius: 8px;">
<span style="font-size: 32px; letter-spacing: 8px; font-weight: bold; color: #dc2626;">{code}</span>
</div>
<p>This code expires in <strong>{expires_minutes} minutes</strong>.</p>
<p style="color: #666; font-size: 14px;">If you did not request this reset, ignore this email.</p>
</body></html>"""
        return text, html_content

    @classmethod
    def send_password_changed_notification(
        cls,
        to_email: str,
        display_name: str,
        changed_at: datetime,
        language: str = "en",
    ) -> bool:
        """
        Send password changed confirmation email.

        Security notification sent after successful password reset
        so user can take action if it wasn't them.

        Args:
            to_email: User's email address
            display_name: User's display name
            changed_at: When the password was changed
            language: User's preferred language (en/fr)

        Returns:
            True if email sent successfully
        """
        html_template, text_template = cls._load_template("password_changed", language)

        # Sanitize user input (Finding #12)
        safe_display_name = cls._sanitize_display_name(display_name)

        # Format timestamp for display
        changed_at_str = changed_at.strftime("%Y-%m-%d %H:%M UTC")
        app_name = cls._get_instance_name()

        context: dict[str, str | int] = {
            "display_name": safe_display_name,
            "changed_at": changed_at_str,
            "app_name": app_name,
            "year": str(datetime.now().year),
        }

        # Use templates if available, otherwise fallback to inline
        if html_template and text_template:
            html_body = cls._render_template(html_template, **context)
            text_body = cls._render_template(text_template, **context)
        else:
            text_body, html_body = cls._build_password_changed_inline(
                safe_display_name, changed_at_str, language, app_name
            )

        subject = cls._get_password_changed_subject(language, app_name)
        provider = get_email_provider()

        # Use retry logic (Finding #7)
        return cls._send_with_retry(
            lambda: provider.send(to_email, subject, html_body, text_body)
        )

    @classmethod
    def _get_password_changed_subject(cls, language: str, app_name: str) -> str:
        """Get password changed email subject based on language."""
        subjects = {
            "en": f"Password changed successfully - {app_name}",
            "fr": f"Mot de passe modifie avec succes - {app_name}",
        }
        return subjects.get(language, subjects["en"])

    @staticmethod
    def _build_password_changed_inline(
        display_name: str,
        changed_at: str,
        language: str,
        app_name: str,
    ) -> tuple[str, str]:
        """Build inline password changed email as fallback when templates not found."""
        if language == "fr":
            text = f"""Bonjour {display_name},

Le mot de passe de votre compte {app_name} a ete modifie avec succes.

Modifie le : {changed_at}

Si ce n'etait pas vous, contactez-nous immediatement.

Cordialement,
L'equipe {app_name}"""
            html_content = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
<h2 style="color: #10b981;">Mot de passe modifie</h2>
<p>Bonjour {display_name},</p>
<p>Le mot de passe de votre compte {app_name} a ete modifie avec succes.</p>
<div style="background: #ecfdf5; padding: 20px; margin: 20px 0; border-radius: 8px; border: 1px solid #10b981;">
<p><strong>Modifie le :</strong> {changed_at}</p>
</div>
<div style="background: #fef2f2; border-left: 4px solid #dc2626; padding: 15px; margin: 20px 0;">
<strong>Ce n'etait pas vous?</strong> Contactez-nous immediatement.
</div>
</body></html>"""
        else:
            text = f"""Hello {display_name},

Your {app_name} account password has been changed successfully.

Changed on: {changed_at}

If this wasn't you, please contact us immediately.

Best regards,
The {app_name} Team"""
            html_content = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
<h2 style="color: #10b981;">Password Changed</h2>
<p>Hello {display_name},</p>
<p>Your {app_name} account password has been changed successfully.</p>
<div style="background: #ecfdf5; padding: 20px; margin: 20px 0; border-radius: 8px; border: 1px solid #10b981;">
<p><strong>Changed on:</strong> {changed_at}</p>
</div>
<div style="background: #fef2f2; border-left: 4px solid #dc2626; padding: 15px; margin: 20px 0;">
<strong>Didn't make this change?</strong> Please contact us immediately.
</div>
</body></html>"""
        return text, html_content

    # =========================================================================
    # Parental Consent Emails (Law 25 Minors)
    # =========================================================================

    @classmethod
    def send_parental_consent_request(
        cls,
        to_email: str,
        child_username: str,
        child_email: str,
        child_age: int,
        consent_url: str,
        expires_at: datetime,
        language: str = "fr",
    ) -> bool:
        """
        Send parental consent request email.

        Law 25 Compliance: This email contains all required information
        about data collection and parent rights.

        Args:
            to_email: Parent's email address
            child_username: Child's username
            child_email: Child's email address
            child_age: Child's age at registration
            consent_url: URL for parent to grant/deny consent
            expires_at: When the consent request expires
            language: Preferred language (en/fr)

        Returns:
            True if email sent successfully
        """
        app_name = cls._get_instance_name()

        # Sanitize inputs
        safe_username = cls._sanitize_display_name(child_username)
        safe_email = cls._escape_template_vars(child_email)
        expires_str = expires_at.strftime("%Y-%m-%d %H:%M UTC")

        if language == "fr":
            subject = f"Demande de consentement parental - {app_name}"
            text_body, html_body = cls._build_consent_request_french(
                safe_username, safe_email, child_age, consent_url, expires_str, app_name
            )
        else:
            subject = f"Parental consent request - {app_name}"
            text_body, html_body = cls._build_consent_request_english(
                safe_username, safe_email, child_age, consent_url, expires_str, app_name
            )

        provider = get_email_provider()
        return cls._send_with_retry(
            lambda: provider.send(to_email, subject, html_body, text_body)
        )

    @staticmethod
    def _build_consent_request_french(
        child_username: str,
        child_email: str,
        child_age: int,
        consent_url: str,
        expires_str: str,
        app_name: str,
    ) -> tuple[str, str]:
        """Build French parental consent request email."""
        text = f"""Bonjour,

Un enfant de {child_age} ans souhaite créer un compte sur {app_name}.

INFORMATIONS DU COMPTE:
- Nom d'utilisateur: {child_username}
- Courriel: {child_email}
- Âge: {child_age} ans

DONNÉES COLLECTÉES:
- Adresse courriel, nom d'utilisateur
- Idées, commentaires et votes soumis
- Horodatages d'activité
- Adresses IP (sécurité seulement)

FINALITÉS:
- Participation civique et communautaire
- Modération et sécurité de la plateforme

CONSERVATION:
Les données sont conservées pendant la durée de vie du compte + 30 jours après suppression.

VOS DROITS (Loi 25):
- Accéder aux données de l'enfant (via le compte ou export)
- Rectifier les informations inexactes
- Supprimer le compte à tout moment
- Retirer votre consentement (entraîne la suppression du compte)

VOTRE DÉCISION:
Pour autoriser ou refuser ce compte, veuillez visiter:
{consent_url}

Cette demande expire le {expires_str}.

Si vous n'avez pas demandé cette création de compte, vous pouvez ignorer ce courriel.

Cordialement,
L'équipe {app_name}"""

        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; line-height: 1.6;">
<h2 style="color: #333;">Demande de consentement parental</h2>
<p>Bonjour,</p>
<p>Un enfant de <strong>{child_age} ans</strong> souhaite créer un compte sur <strong>{app_name}</strong>.</p>

<div style="background: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 8px;">
<h3 style="margin-top: 0; color: #555;">Informations du compte</h3>
<p><strong>Nom d'utilisateur:</strong> {child_username}</p>
<p><strong>Courriel:</strong> {child_email}</p>
<p><strong>Âge:</strong> {child_age} ans</p>
</div>

<div style="background: #fff3cd; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #ffc107;">
<h3 style="margin-top: 0; color: #856404;">Données collectées</h3>
<ul style="margin-bottom: 0;">
<li>Adresse courriel et nom d'utilisateur</li>
<li>Idées, commentaires et votes soumis</li>
<li>Horodatages d'activité</li>
<li>Adresses IP (pour la sécurité uniquement)</li>
</ul>
</div>

<div style="background: #e8f4fd; padding: 20px; margin: 20px 0; border-radius: 8px;">
<h3 style="margin-top: 0; color: #0066cc;">Vos droits (Loi 25)</h3>
<ul style="margin-bottom: 0;">
<li>Accéder aux données de l'enfant</li>
<li>Rectifier les informations inexactes</li>
<li>Supprimer le compte à tout moment</li>
<li>Retirer votre consentement</li>
</ul>
</div>

<div style="text-align: center; margin: 30px 0;">
<a href="{consent_url}" style="display: inline-block; background: #10b981; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold;">Prendre ma décision</a>
</div>

<p style="color: #666; font-size: 14px; text-align: center;">
Cette demande expire le <strong>{expires_str}</strong>
</p>

<hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
<p style="color: #999; font-size: 12px;">
Si vous n'avez pas demandé cette création de compte, vous pouvez ignorer ce courriel.<br>
Cordialement, L'équipe {app_name}
</p>
</body></html>"""
        return text, html

    @staticmethod
    def _build_consent_request_english(
        child_username: str,
        child_email: str,
        child_age: int,
        consent_url: str,
        expires_str: str,
        app_name: str,
    ) -> tuple[str, str]:
        """Build English parental consent request email."""
        text = f"""Hello,

A {child_age}-year-old child wishes to create an account on {app_name}.

ACCOUNT INFORMATION:
- Username: {child_username}
- Email: {child_email}
- Age: {child_age} years old

DATA COLLECTED:
- Email address, username
- Ideas, comments, and votes submitted
- Activity timestamps
- IP addresses (for security only)

PURPOSES:
- Civic engagement and community participation
- Moderation and platform safety

RETENTION:
Data is retained for the lifetime of the account + 30 days after deletion.

YOUR RIGHTS (Law 25):
- Access your child's data (via account or export)
- Rectify inaccurate information
- Delete the account at any time
- Withdraw your consent (results in account deletion)

YOUR DECISION:
To authorize or refuse this account, please visit:
{consent_url}

This request expires on {expires_str}.

If you did not request this account creation, you can ignore this email.

Best regards,
The {app_name} Team"""

        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; line-height: 1.6;">
<h2 style="color: #333;">Parental Consent Request</h2>
<p>Hello,</p>
<p>A <strong>{child_age}-year-old child</strong> wishes to create an account on <strong>{app_name}</strong>.</p>

<div style="background: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 8px;">
<h3 style="margin-top: 0; color: #555;">Account Information</h3>
<p><strong>Username:</strong> {child_username}</p>
<p><strong>Email:</strong> {child_email}</p>
<p><strong>Age:</strong> {child_age} years old</p>
</div>

<div style="background: #fff3cd; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #ffc107;">
<h3 style="margin-top: 0; color: #856404;">Data Collected</h3>
<ul style="margin-bottom: 0;">
<li>Email address and username</li>
<li>Ideas, comments, and votes submitted</li>
<li>Activity timestamps</li>
<li>IP addresses (for security only)</li>
</ul>
</div>

<div style="background: #e8f4fd; padding: 20px; margin: 20px 0; border-radius: 8px;">
<h3 style="margin-top: 0; color: #0066cc;">Your Rights (Law 25)</h3>
<ul style="margin-bottom: 0;">
<li>Access your child's data</li>
<li>Rectify inaccurate information</li>
<li>Delete the account at any time</li>
<li>Withdraw your consent</li>
</ul>
</div>

<div style="text-align: center; margin: 30px 0;">
<a href="{consent_url}" style="display: inline-block; background: #10b981; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold;">Make My Decision</a>
</div>

<p style="color: #666; font-size: 14px; text-align: center;">
This request expires on <strong>{expires_str}</strong>
</p>

<hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
<p style="color: #999; font-size: 12px;">
If you did not request this account creation, you can ignore this email.<br>
Best regards, The {app_name} Team
</p>
</body></html>"""
        return text, html

    @classmethod
    def send_consent_granted_notification(
        cls,
        to_email: str,
        child_username: str,
        language: str = "fr",
    ) -> bool:
        """
        Send confirmation email when consent is granted.

        Args:
            to_email: Parent's email address
            child_username: Child's username
            language: Preferred language (en/fr)

        Returns:
            True if email sent successfully
        """
        app_name = cls._get_instance_name()
        safe_username = cls._sanitize_display_name(child_username)

        if language == "fr":
            subject = f"Consentement accordé - {app_name}"
            text_body, html_body = cls._build_consent_granted_french(
                safe_username, app_name
            )
        else:
            subject = f"Consent granted - {app_name}"
            text_body, html_body = cls._build_consent_granted_english(
                safe_username, app_name
            )

        provider = get_email_provider()
        return cls._send_with_retry(
            lambda: provider.send(to_email, subject, html_body, text_body)
        )

    @staticmethod
    def _build_consent_granted_french(
        child_username: str,
        app_name: str,
    ) -> tuple[str, str]:
        """Build French consent granted email."""
        text = f"""Bonjour,

Vous avez accordé votre consentement parental pour le compte de {child_username} sur {app_name}.

Le compte est maintenant actif et l'enfant peut utiliser la plateforme.

RAPPEL DE VOS DROITS:
- Vous pouvez accéder aux données du compte à tout moment
- Vous pouvez demander la suppression du compte
- Vous pouvez retirer votre consentement (cela supprimera le compte)

Si vous avez des questions, n'hésitez pas à nous contacter.

Cordialement,
L'équipe {app_name}"""

        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
<h2 style="color: #10b981;">Consentement accordé</h2>
<p>Bonjour,</p>
<p>Vous avez accordé votre consentement parental pour le compte de <strong>{child_username}</strong> sur <strong>{app_name}</strong>.</p>

<div style="background: #ecfdf5; padding: 20px; margin: 20px 0; border-radius: 8px; border: 1px solid #10b981;">
<p style="margin: 0; color: #059669; font-weight: bold;">
Le compte est maintenant actif.
</p>
</div>

<div style="background: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 8px;">
<h3 style="margin-top: 0; color: #555;">Rappel de vos droits</h3>
<ul>
<li>Accéder aux données du compte à tout moment</li>
<li>Demander la suppression du compte</li>
<li>Retirer votre consentement</li>
</ul>
</div>

<p style="color: #666; font-size: 14px;">
Cordialement,<br>L'équipe {app_name}
</p>
</body></html>"""
        return text, html

    @staticmethod
    def _build_consent_granted_english(
        child_username: str,
        app_name: str,
    ) -> tuple[str, str]:
        """Build English consent granted email."""
        text = f"""Hello,

You have granted parental consent for the account of {child_username} on {app_name}.

The account is now active and the child can use the platform.

REMINDER OF YOUR RIGHTS:
- You can access the account data at any time
- You can request account deletion
- You can withdraw your consent (this will delete the account)

If you have any questions, please contact us.

Best regards,
The {app_name} Team"""

        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
<h2 style="color: #10b981;">Consent Granted</h2>
<p>Hello,</p>
<p>You have granted parental consent for the account of <strong>{child_username}</strong> on <strong>{app_name}</strong>.</p>

<div style="background: #ecfdf5; padding: 20px; margin: 20px 0; border-radius: 8px; border: 1px solid #10b981;">
<p style="margin: 0; color: #059669; font-weight: bold;">
The account is now active.
</p>
</div>

<div style="background: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 8px;">
<h3 style="margin-top: 0; color: #555;">Reminder of Your Rights</h3>
<ul>
<li>Access the account data at any time</li>
<li>Request account deletion</li>
<li>Withdraw your consent</li>
</ul>
</div>

<p style="color: #666; font-size: 14px;">
Best regards,<br>The {app_name} Team
</p>
</body></html>"""
        return text, html

    @classmethod
    def send_consent_denied_notification(
        cls,
        to_email: str,
        child_username: str,
        grace_period_days: int = 30,
        language: str = "fr",
    ) -> bool:
        """
        Send notification when consent is denied.

        Args:
            to_email: Parent's email address
            child_username: Child's username
            grace_period_days: Days before account deletion
            language: Preferred language (en/fr)

        Returns:
            True if email sent successfully
        """
        app_name = cls._get_instance_name()
        safe_username = cls._sanitize_display_name(child_username)

        if language == "fr":
            subject = f"Consentement refusé - {app_name}"
            text_body, html_body = cls._build_consent_denied_french(
                safe_username, grace_period_days, app_name
            )
        else:
            subject = f"Consent denied - {app_name}"
            text_body, html_body = cls._build_consent_denied_english(
                safe_username, grace_period_days, app_name
            )

        provider = get_email_provider()
        return cls._send_with_retry(
            lambda: provider.send(to_email, subject, html_body, text_body)
        )

    @staticmethod
    def _build_consent_denied_french(
        child_username: str,
        grace_period_days: int,
        app_name: str,
    ) -> tuple[str, str]:
        """Build French consent denied email."""
        text = f"""Bonjour,

Vous avez refusé le consentement parental pour le compte de {child_username} sur {app_name}.

Le compte restera inactif et sera supprimé dans {grace_period_days} jours.

Si vous changez d'avis, vous pouvez nous contacter avant cette date.

Cordialement,
L'équipe {app_name}"""

        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
<h2 style="color: #dc2626;">Consentement refusé</h2>
<p>Bonjour,</p>
<p>Vous avez refusé le consentement parental pour le compte de <strong>{child_username}</strong> sur <strong>{app_name}</strong>.</p>

<div style="background: #fef2f2; padding: 20px; margin: 20px 0; border-radius: 8px; border: 1px solid #dc2626;">
<p style="margin: 0; color: #991b1b;">
Le compte restera inactif et sera <strong>supprimé dans {grace_period_days} jours</strong>.
</p>
</div>

<p>Si vous changez d'avis, vous pouvez nous contacter avant cette date.</p>

<p style="color: #666; font-size: 14px;">
Cordialement,<br>L'équipe {app_name}
</p>
</body></html>"""
        return text, html

    @staticmethod
    def _build_consent_denied_english(
        child_username: str,
        grace_period_days: int,
        app_name: str,
    ) -> tuple[str, str]:
        """Build English consent denied email."""
        text = f"""Hello,

You have denied parental consent for the account of {child_username} on {app_name}.

The account will remain inactive and will be deleted in {grace_period_days} days.

If you change your mind, you can contact us before that date.

Best regards,
The {app_name} Team"""

        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
<h2 style="color: #dc2626;">Consent Denied</h2>
<p>Hello,</p>
<p>You have denied parental consent for the account of <strong>{child_username}</strong> on <strong>{app_name}</strong>.</p>

<div style="background: #fef2f2; padding: 20px; margin: 20px 0; border-radius: 8px; border: 1px solid #dc2626;">
<p style="margin: 0; color: #991b1b;">
The account will remain inactive and will be <strong>deleted in {grace_period_days} days</strong>.
</p>
</div>

<p>If you change your mind, you can contact us before that date.</p>

<p style="color: #666; font-size: 14px;">
Best regards,<br>The {app_name} Team
</p>
</body></html>"""
        return text, html
