"""Contact form router for handling user inquiries."""

from fastapi import APIRouter, Request
from loguru import logger

from helpers.rate_limiter import limiter
from models.schemas import ContactFormRequest, ContactFormResponse
from services.contact_service import ContactService

router = APIRouter(prefix="/contact", tags=["contact"])


@router.post("", response_model=ContactFormResponse)
@limiter.limit("5/hour")
def submit_contact_form(
    request: Request, form: ContactFormRequest
) -> ContactFormResponse:
    """Submit a contact form.

    Sends notification email to administrators and confirmation to user.
    No authentication required - public endpoint.
    Rate limited to 5 submissions per hour per IP.

    Args:
        request: FastAPI request object (required for rate limiter)
        form: Contact form data with name, email, subject, and message

    Returns:
        Success response with localized message

    Raises:
        EmailDeliveryException: 500 if email sending fails (handled by global exception handler)
    """
    logger.info(
        f"Contact form submitted: name={form.name}, subject={form.subject.value}"
    )

    # Service raises ServiceException on failure, handled by main.py exception handler
    ContactService.submit_contact_form(form)

    # Return localized success message
    if form.language == "fr":
        message = (
            "Votre message a été envoyé avec succès. Nous vous répondrons bientôt."
        )
    else:
        message = "Your message has been sent successfully. We will respond soon."

    return ContactFormResponse(success=True, message=message)
