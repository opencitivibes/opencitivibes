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
