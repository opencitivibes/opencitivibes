"""Contact form service for handling user inquiries.

This module handles contact form submissions and sends emails to administrators.
"""

import html
import os

from loguru import logger

from models.exceptions import EmailDeliveryException
from models.schemas import ContactFormRequest, ContactSubject
from services.config_service import get_config
from services.email_service import get_email_provider


class ContactService:
    """Service for handling contact form submissions."""

    # Subject labels for emails (bilingual)
    SUBJECT_LABELS = {
        ContactSubject.GENERAL: {"en": "General Question", "fr": "Question générale"},
        ContactSubject.ACCOUNT: {"en": "Account Issue", "fr": "Problème de compte"},
        ContactSubject.IDEA: {"en": "About an Idea", "fr": "À propos d'une idée"},
        ContactSubject.BUG: {"en": "Bug Report", "fr": "Signalement de bogue"},
        ContactSubject.FEEDBACK: {"en": "Feedback", "fr": "Commentaire"},
        ContactSubject.PRIVACY: {
            "en": "Privacy Request",
            "fr": "Demande de confidentialité",
        },
        ContactSubject.OTHER: {"en": "Other", "fr": "Autre"},
    }

    @classmethod
    def _get_admin_email(cls) -> str:
        """Get the admin contact email from ADMIN_EMAIL env var or platform config."""

        # Prefer ADMIN_EMAIL env var (set in .env for each deployment)
        admin_email = os.environ.get("ADMIN_EMAIL")
        if admin_email:
            return admin_email

        # Fallback to platform config
        try:
            config = get_config()
            return config.contact.email
        except Exception as e:
            logger.warning(f"Failed to get admin email from config: {e}")
            return "contact@opencitivibes.local"

    @classmethod
    def _get_instance_name(cls, language: str) -> str:
        """Get instance name from platform config."""
        try:
            config = get_config()
            return config.instance.name.get(
                language, config.instance.name.get("en", "OpenCitiVibes")
            )
        except Exception:
            return "OpenCitiVibes"

    @classmethod
    def _get_subject_label(cls, subject: ContactSubject, language: str) -> str:
        """Get human-readable subject label."""
        labels = cls.SUBJECT_LABELS.get(
            subject, cls.SUBJECT_LABELS[ContactSubject.OTHER]
        )
        return labels.get(language, labels["en"])

    @classmethod
    def _build_admin_email(
        cls,
        form: ContactFormRequest,
        instance_name: str,
    ) -> tuple[str, str, str]:
        """Build email content for admin notification.

        All user-provided data is HTML-escaped to prevent XSS.

        Returns:
            Tuple of (subject, html_body, text_body)
        """
        subject_label = cls._get_subject_label(form.subject, "en")
        email_subject = f"[{instance_name}] Contact Form: {subject_label}"

        # Escape user data for text body (minimal escaping needed)
        text_body = f"""New contact form submission

From: {form.name}
Email: {form.email}
Subject: {subject_label}
Language: {form.language.upper()}

Message:
{form.message}

---
This message was sent via the {instance_name} contact form.
"""

        # Escape all user-provided data for HTML to prevent XSS
        safe_name = html.escape(form.name)
        safe_email = html.escape(form.email)
        safe_message = html.escape(form.message)

        html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f5f5f5;">
    <div style="background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <h2 style="color: #333; margin-top: 0; border-bottom: 2px solid #4F46E5; padding-bottom: 10px;">
            New Contact Form Submission
        </h2>

        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr>
                <td style="padding: 8px 0; color: #666; width: 100px;"><strong>From:</strong></td>
                <td style="padding: 8px 0; color: #333;">{safe_name}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0; color: #666;"><strong>Email:</strong></td>
                <td style="padding: 8px 0;">
                    <a href="mailto:{safe_email}" style="color: #4F46E5;">{safe_email}</a>
                </td>
            </tr>
            <tr>
                <td style="padding: 8px 0; color: #666;"><strong>Subject:</strong></td>
                <td style="padding: 8px 0; color: #333;">{subject_label}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0; color: #666;"><strong>Language:</strong></td>
                <td style="padding: 8px 0; color: #333;">{form.language.upper()}</td>
            </tr>
        </table>

        <div style="background: #f8f9fa; padding: 20px; border-radius: 6px; margin-top: 20px;">
            <h3 style="color: #333; margin-top: 0;">Message:</h3>
            <p style="color: #444; line-height: 1.6; white-space: pre-wrap;">{safe_message}</p>
        </div>

        <p style="color: #888; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
            This message was sent via the {instance_name} contact form.
        </p>
    </div>
</body>
</html>"""

        return email_subject, html_body, text_body

    @classmethod
    def _build_confirmation_email(
        cls,
        form: ContactFormRequest,
        instance_name: str,
    ) -> tuple[str, str, str]:
        """Build confirmation email for the user.

        All user-provided data is HTML-escaped to prevent XSS.

        Returns:
            Tuple of (subject, html_body, text_body)
        """
        # Escape user data for HTML
        safe_name = html.escape(form.name)
        message_ellipsis = "..." if len(form.message) > 200 else ""

        if form.language == "fr":
            email_subject = f"Nous avons reçu votre message - {instance_name}"
            text_body = f"""Bonjour {form.name},

Nous avons bien reçu votre message et nous vous en remercions.

Notre équipe examinera votre demande et vous répondra dans les plus brefs délais.

Résumé de votre message:
- Sujet: {cls._get_subject_label(form.subject, "fr")}
- Message: {form.message[:200]}{message_ellipsis}

Cordialement,
L'équipe {instance_name}
"""
            html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <h2 style="color: #333;">Merci pour votre message!</h2>
        <p>Bonjour {safe_name},</p>
        <p>Nous avons bien reçu votre message et nous vous en remercions.</p>
        <p>Notre équipe examinera votre demande et vous répondra dans les plus brefs délais.</p>
        <div style="background: #f8f9fa; padding: 15px; border-radius: 6px; margin: 20px 0;">
            <p style="margin: 0; color: #666;"><strong>Sujet:</strong> {cls._get_subject_label(form.subject, "fr")}</p>
        </div>
        <p style="color: #888; font-size: 14px;">Cordialement,<br>L'équipe {instance_name}</p>
    </div>
</body>
</html>"""
        else:
            email_subject = f"We received your message - {instance_name}"
            text_body = f"""Hello {form.name},

Thank you for reaching out to us. We have received your message.

Our team will review your inquiry and get back to you as soon as possible.

Summary of your message:
- Subject: {cls._get_subject_label(form.subject, "en")}
- Message: {form.message[:200]}{message_ellipsis}

Best regards,
The {instance_name} Team
"""
            html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <h2 style="color: #333;">Thank you for your message!</h2>
        <p>Hello {safe_name},</p>
        <p>Thank you for reaching out to us. We have received your message.</p>
        <p>Our team will review your inquiry and get back to you as soon as possible.</p>
        <div style="background: #f8f9fa; padding: 15px; border-radius: 6px; margin: 20px 0;">
            <p style="margin: 0; color: #666;"><strong>Subject:</strong> {cls._get_subject_label(form.subject, "en")}</p>
        </div>
        <p style="color: #888; font-size: 14px;">Best regards,<br>The {instance_name} Team</p>
    </div>
</body>
</html>"""

        return email_subject, html_body, text_body

    @classmethod
    def submit_contact_form(cls, form: ContactFormRequest) -> None:
        """Process a contact form submission.

        Sends notification to admin and confirmation to user.

        Args:
            form: The validated contact form data

        Raises:
            EmailDeliveryException: If admin notification email fails to send
        """
        admin_email = cls._get_admin_email()
        instance_name = cls._get_instance_name(form.language)
        provider = get_email_provider()

        # Send notification to admin
        admin_subject, admin_html, admin_text = cls._build_admin_email(
            form, instance_name
        )
        admin_sent = provider.send(admin_email, admin_subject, admin_html, admin_text)

        if not admin_sent:
            logger.error(
                f"Failed to send contact form notification to admin: {admin_email}"
            )
            raise EmailDeliveryException("Failed to send contact form notification")

        logger.info(f"Contact form notification sent to admin: {admin_email}")

        # Send confirmation to user (best-effort, don't fail if this fails)
        user_subject, user_html, user_text = cls._build_confirmation_email(
            form, instance_name
        )
        user_sent = provider.send(form.email, user_subject, user_html, user_text)

        if not user_sent:
            logger.warning(f"Failed to send confirmation email to user: {form.email}")

        logger.info(
            f"Contact form processed: from={form.name} subject={form.subject.value}"
        )
