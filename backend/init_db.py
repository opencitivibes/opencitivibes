"""Initialize the database with default categories and an admin user."""

from authentication.auth import get_password_hash
from models.config import settings
from repositories.database import Base, SessionLocal, engine
from repositories.db_models import Category, User
from services.config_service import get_entity_name

# Create tables
Base.metadata.create_all(bind=engine)


def get_default_categories() -> list[dict]:
    """Get default categories based on instance configuration.

    Returns:
        List of category dictionaries with localized names and descriptions.
    """
    entity_en = get_entity_name("en")
    entity_fr = get_entity_name("fr")

    # Generic categories that work for any city/organization
    return [
        {
            "name_en": "Transportation",
            "name_fr": "Transport",
            "description_en": f"Ideas to improve transportation and mobility in {entity_en}"
            if entity_en
            else "Ideas to improve transportation and mobility",
            "description_fr": f"Idées pour améliorer les transports et la mobilité à {entity_fr}"
            if entity_fr
            else "Idées pour améliorer les transports et la mobilité",
        },
        {
            "name_en": "Environment",
            "name_fr": "Environnement",
            "description_en": f"Ideas for a greener and more sustainable {entity_en}"
            if entity_en
            else "Ideas for a greener and more sustainable community",
            "description_fr": f"Idées pour un(e) {entity_fr} plus vert(e) et durable"
            if entity_fr
            else "Idées pour une communauté plus verte et durable",
        },
        {
            "name_en": "Culture & Events",
            "name_fr": "Culture et événements",
            "description_en": "Ideas for cultural activities and events",
            "description_fr": "Idées pour les activités culturelles et événements",
        },
        {
            "name_en": "Public Spaces",
            "name_fr": "Espaces publics",
            "description_en": "Ideas to improve parks, streets, and public areas",
            "description_fr": "Idées pour améliorer les parcs, rues et espaces publics",
        },
        {
            "name_en": "Technology & Innovation",
            "name_fr": "Technologie et innovation",
            "description_en": "Ideas for smart initiatives and tech improvements",
            "description_fr": "Idées pour les initiatives intelligentes et améliorations technologiques",
        },
        {
            "name_en": "Community & Social",
            "name_fr": "Communauté et social",
            "description_en": "Ideas to strengthen community bonds and social programs",
            "description_fr": "Idées pour renforcer les liens communautaires et programmes sociaux",
        },
    ]


def init_db():
    """Initialize the database with default data."""
    db = SessionLocal()

    try:
        # Check if categories already exist
        existing_categories = db.query(Category).first()
        if not existing_categories:
            categories = [Category(**cat) for cat in get_default_categories()]
            for category in categories:
                db.add(category)
            db.commit()
            print("[OK] Default categories created")

        # Check if admin user exists
        existing_admin = (
            db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()
        )
        if not existing_admin:
            # Create default admin user with password from settings/.env
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)
            admin = User(
                email=settings.ADMIN_EMAIL,
                username="admin",
                display_name="Administrator",
                hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                is_global_admin=True,
                # Consent fields (Law 25 compliance) - admin implicitly consents
                consent_terms_accepted=True,
                consent_privacy_accepted=True,
                consent_terms_version="1.0",
                consent_privacy_version="1.0",
                consent_timestamp=now,
                marketing_consent=False,
            )
            db.add(admin)
            db.commit()
            print("[OK] Admin user created")
            print(f"  Email: {settings.ADMIN_EMAIL}")
            print("  Password: (from ADMIN_PASSWORD in .env)")
            print("  IMPORTANT: Change this password in production!")

        print("\n[OK] Database initialization complete!")

    except Exception as e:
        print(f"Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
