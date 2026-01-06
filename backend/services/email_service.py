"""Email service for sending transactional emails.

This module provides a unified interface for sending emails through various providers.
Supports:
- console: Logs emails to console (development)
- smtp: Standard SMTP delivery
- sendgrid: SendGrid API (requires sendgrid package)
"""

import re
import smtplib
from abc import ABC, abstractmethod
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
