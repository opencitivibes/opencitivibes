#!/usr/bin/env python3
# ruff: noqa: E402
# E402 disabled: sys.path modification must occur before imports
"""
Seed the database with multilingual test data.

This script generates ideas and comments in multiple languages based on the
current instance configuration:
- Montreal: French + English
- Quebec: French + English + Spanish
- Calgary: English only

Usage in Docker:
    docker compose exec backend python scripts/seed_data.py

Usage locally:
    cd backend && uv run python scripts/seed_data.py
"""

import json
import os
import random
import sys
from pathlib import Path

# Add parent directory to path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from repositories.database import SessionLocal
from repositories.db_models import Category, Comment, Idea, IdeaTag, Tag, User, Vote
from authentication.auth import get_password_hash


# ============================================================================
# MULTILINGUAL CONTENT DATA
# ============================================================================

# Ideas in French (Montreal, Quebec)
IDEAS_FR = [
    (
        "Améliorer les pistes cyclables du centre-ville",
        "Nous proposons d'élargir et de sécuriser les pistes cyclables du centre-ville pour encourager les déplacements à vélo. Cela réduirait la congestion et améliorerait la qualité de l'air.",
    ),
    (
        "Créer plus d'espaces verts dans les quartiers",
        "Le quartier manque d'espaces verts accessibles. Nous suggérons de convertir certains terrains vacants en mini-parcs avec des arbres et des bancs.",
    ),
    (
        "Installer des fontaines d'eau potable",
        "Pour réduire l'utilisation de bouteilles en plastique, nous proposons d'installer des fontaines d'eau dans tous les parcs majeurs.",
    ),
    (
        "Réduire la pollution sonore nocturne",
        "Les niveaux de bruit dans certains quartiers sont trop élevés la nuit. Des mesures de réduction comme des limites de vitesse et des zones calmes sont nécessaires.",
    ),
    (
        "Ajouter des bancs publics pour les aînés",
        "Les personnes âgées ont besoin de plus d'endroits pour se reposer lors de leurs promenades. Des bancs tous les 200 mètres sur les rues principales.",
    ),
    (
        "Organiser des marchés fermiers hebdomadaires",
        "Un marché fermier régulier permettrait aux résidents d'accéder à des produits locaux frais tout en soutenant nos agriculteurs.",
    ),
    (
        "Améliorer l'éclairage des parcs",
        "Plusieurs parcs sont mal éclairés le soir, ce qui pose des problèmes de sécurité. L'installation de lampadaires solaires serait écologique et efficace.",
    ),
    (
        "Créer un jardin communautaire",
        "Un espace où les résidents peuvent cultiver leurs propres légumes renforcerait les liens communautaires et favoriserait une alimentation saine.",
    ),
]

# Ideas in English (Montreal, Quebec, Calgary)
IDEAS_EN = [
    (
        "Improve downtown bike lanes",
        "We propose widening and securing downtown bike lanes to encourage cycling. This would reduce congestion and improve air quality for everyone.",
    ),
    (
        "Create more green spaces in neighborhoods",
        "Our neighborhood lacks accessible green spaces. We suggest converting vacant lots into mini-parks with trees and benches.",
    ),
    (
        "Install public water fountains",
        "To reduce plastic bottle usage, we propose installing water fountains in all major parks and along popular walking routes.",
    ),
    (
        "Reduce nighttime noise pollution",
        "Noise levels in some neighborhoods are too high at night. Speed limits and quiet zones would help residents sleep better.",
    ),
    (
        "Add public benches for seniors",
        "Elderly residents need more places to rest during walks. Benches every 200 meters on main streets would make a big difference.",
    ),
    (
        "Organize weekly farmers markets",
        "A regular farmers market would give residents access to fresh local produce while supporting our farming community.",
    ),
    (
        "Improve park lighting",
        "Several parks are poorly lit in the evening, creating safety concerns. Solar-powered streetlights would be eco-friendly and effective.",
    ),
    (
        "Create a community garden",
        "A space where residents can grow their own vegetables would strengthen community bonds and promote healthy eating.",
    ),
    (
        "Expand public transit routes",
        "Many neighborhoods lack adequate public transit. Adding new bus routes would reduce car dependency and emissions.",
    ),
    (
        "Build more affordable housing",
        "Housing costs are rising too fast. The city should encourage developers to include affordable units in new projects.",
    ),
]

# Ideas in Spanish (Quebec only)
IDEAS_ES = [
    (
        "Mejorar los carriles para bicicletas",
        "Proponemos ampliar y asegurar los carriles para bicicletas del centro para fomentar el ciclismo. Esto reduciría la congestión y mejoraría la calidad del aire.",
    ),
    (
        "Crear más espacios verdes",
        "Nuestro barrio carece de espacios verdes accesibles. Sugerimos convertir terrenos vacantes en mini-parques con árboles y bancos.",
    ),
    (
        "Instalar fuentes de agua potable",
        "Para reducir el uso de botellas de plástico, proponemos instalar fuentes de agua en todos los parques principales.",
    ),
    (
        "Reducir la contaminación acústica nocturna",
        "Los niveles de ruido en algunos barrios son demasiado altos por la noche. Se necesitan límites de velocidad y zonas tranquilas.",
    ),
    (
        "Organizar mercados de agricultores semanales",
        "Un mercado de agricultores regular daría a los residentes acceso a productos locales frescos mientras apoya a nuestra comunidad agrícola.",
    ),
]

# Comments in French
COMMENTS_FR = [
    "Excellente idée! J'espère que la ville va considérer cette proposition.",
    "Je soutiens cette initiative. C'est exactement ce dont notre quartier a besoin.",
    "J'ai quelques réserves, mais globalement c'est une bonne direction.",
    "Nous avons besoin de plus de projets comme celui-ci pour améliorer notre qualité de vie.",
    "Comment pouvons-nous aider à faire avancer ce projet?",
    "Je vis dans ce quartier depuis 20 ans et je pense que c'est une priorité.",
    "Le budget municipal devrait absolument inclure ce type de projet.",
    "Bravo pour cette suggestion constructive!",
]

# Comments in English
COMMENTS_EN = [
    "Great idea! I hope the city considers this proposal seriously.",
    "I fully support this initiative. It's exactly what our neighborhood needs.",
    "I have some reservations, but overall this is a good direction.",
    "We need more projects like this to improve our quality of life.",
    "How can we help move this project forward?",
    "I've lived in this neighborhood for 20 years and think this should be a priority.",
    "The municipal budget should definitely include this type of project.",
    "Well done on this constructive suggestion!",
    "This would make such a difference for families with children.",
    "I'd volunteer to help implement this if the city approves it.",
]

# Comments in Spanish
COMMENTS_ES = [
    "¡Excelente idea! Espero que la ciudad considere esta propuesta.",
    "Apoyo totalmente esta iniciativa. Es exactamente lo que nuestro barrio necesita.",
    "Tengo algunas reservas, pero en general es una buena dirección.",
    "Necesitamos más proyectos como este para mejorar nuestra calidad de vida.",
    "¿Cómo podemos ayudar a que este proyecto avance?",
]

# Tags (multilingual display names)
TAGS_DATA = [
    ("durable", {"fr": "Durable", "en": "Sustainable", "es": "Sostenible"}),
    ("velo", {"fr": "Vélo", "en": "Cycling", "es": "Ciclismo"}),
    ("vert", {"fr": "Vert", "en": "Green", "es": "Verde"}),
    ("abordable", {"fr": "Abordable", "en": "Affordable", "es": "Asequible"}),
    ("communaute", {"fr": "Communauté", "en": "Community", "es": "Comunidad"}),
    ("innovation", {"fr": "Innovation", "en": "Innovation", "es": "Innovación"}),
    (
        "accessibilite",
        {"fr": "Accessibilité", "en": "Accessibility", "es": "Accesibilidad"},
    ),
    ("securite", {"fr": "Sécurité", "en": "Safety", "es": "Seguridad"}),
]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_instance_config() -> tuple[str, list[str]]:
    """Get instance ID and supported languages from config."""
    config_path = os.environ.get("PLATFORM_CONFIG_PATH")

    if config_path and Path(config_path).exists():
        with open(config_path) as f:
            config = json.load(f)
        instance_id = config.get("instance", {}).get("id", "montreal")
        supported_locales = config.get("localization", {}).get(
            "supported_locales", ["fr", "en"]
        )
        return instance_id, supported_locales

    # Default to Montreal
    return "montreal", ["fr", "en"]


def check_existing_data() -> bool:
    """Check if database already has data."""
    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        return user_count > 1  # More than just admin
    finally:
        db.close()


def seed_multilingual_data():
    """Seed database with multilingual test data based on instance config."""
    instance_id, supported_languages = get_instance_config()

    # Determine language distribution based on instance
    # Montreal: fr/en, Quebec: fr/en/es, Calgary: en only (per user request)
    if instance_id == "calgary":
        languages_for_ideas = ["en"]
    elif instance_id == "quebec":
        languages_for_ideas = ["fr", "en", "es"]
    else:  # montreal or default
        languages_for_ideas = ["fr", "en"]

    db = SessionLocal()

    try:
        print("=" * 60)
        print(f"Seeding database for instance: {instance_id}")
        print(f"Languages: {', '.join(languages_for_ideas)}")
        print("=" * 60)

        # Check if data exists
        if check_existing_data():
            print("\nDatabase already has data. Skipping seed.")
            print("Run db-reset first if you want to reseed.")
            return

        # Create test users
        print("\nCreating test users...")
        users = []
        test_users = [
            ("user1@test.com", "testuser1", "Alice Martin"),
            ("user2@test.com", "testuser2", "Bob Tremblay"),
            ("user3@test.com", "testuser3", "Claire Gagnon"),
            ("user4@test.com", "testuser4", "David Roy"),
            ("user5@test.com", "testuser5", "Emma Côté"),
        ]

        for email, username, display_name in test_users:
            user = User(
                email=email,
                username=username,
                hashed_password=get_password_hash("TestPass123!"),
                display_name=display_name,
                is_active=True,
            )
            db.add(user)
            users.append(user)

        db.commit()
        print(f"  Created {len(users)} test users")

        # Get existing categories
        categories = db.query(Category).all()
        if not categories:
            print("\nNo categories found. Please run migrations first.")
            return

        print(f"  Found {len(categories)} categories")

        # Create tags with language-appropriate display names
        print("\nCreating tags...")
        tags = []
        default_lang = "fr" if instance_id != "calgary" else "en"

        for name, display_names in TAGS_DATA:
            existing = db.query(Tag).filter(Tag.name == name).first()
            if not existing:
                display_name = display_names.get(
                    default_lang, display_names.get("en", name)
                )
                tag = Tag(name=name, display_name=display_name)
                db.add(tag)
                tags.append(tag)
            else:
                tags.append(existing)

        db.commit()
        print(f"  Created/found {len(tags)} tags")

        # Build ideas list based on languages
        print("\nCreating multilingual ideas...")
        ideas_by_lang: dict[str, list[tuple[str, str]]] = {
            "fr": IDEAS_FR,
            "en": IDEAS_EN,
            "es": IDEAS_ES,
        }

        ideas = []
        idea_language_counts: dict[str, int] = {}

        for lang in languages_for_ideas:
            lang_ideas = ideas_by_lang.get(lang, [])
            idea_language_counts[lang] = 0

            for title, description in lang_ideas:
                # Determine status (80% approved, 20% pending)
                status = "approved" if random.random() < 0.8 else "pending"

                idea = Idea(
                    title=title,
                    description=description,
                    user_id=random.choice(users).id,
                    category_id=random.choice(categories).id,
                    status=status,
                    language=lang,
                )
                db.add(idea)
                ideas.append(idea)
                idea_language_counts[lang] += 1

        db.flush()

        for lang, count in idea_language_counts.items():
            print(f"  Created {count} ideas in {lang.upper()}")

        # Add tags to ideas
        for idea in ideas:
            selected_tags = random.sample(tags, min(random.randint(1, 3), len(tags)))
            for tag in selected_tags:
                idea_tag = IdeaTag(idea_id=idea.id, tag_id=tag.id)
                db.add(idea_tag)

        # Add votes
        print("\nCreating votes...")
        vote_count = 0
        for idea in ideas:
            if idea.status == "approved":
                voters = random.sample(users, random.randint(1, len(users)))
                for voter in voters:
                    vote_type = random.choice(["upvote", "downvote"])
                    vote = Vote(
                        user_id=voter.id,
                        idea_id=idea.id,
                        vote_type=vote_type,
                    )
                    db.add(vote)
                    vote_count += 1

        print(f"  Created {vote_count} votes")

        # Add multilingual comments
        print("\nCreating multilingual comments...")
        comments_by_lang: dict[str, list[str]] = {
            "fr": COMMENTS_FR,
            "en": COMMENTS_EN,
            "es": COMMENTS_ES,
        }

        comment_count = 0
        comment_language_counts: dict[str, int] = {}

        for lang in languages_for_ideas:
            comment_language_counts[lang] = 0

        for idea in ideas:
            if idea.status != "approved":
                continue

            # Add 1-4 comments per approved idea
            num_comments = random.randint(1, 4)

            for _ in range(num_comments):
                # Choose language (prefer idea's language, but mix in others)
                if random.random() < 0.7:
                    # 70% chance to match idea language
                    comment_lang = idea.language
                else:
                    # 30% chance to use a different supported language
                    comment_lang = random.choice(languages_for_ideas)

                available_comments = comments_by_lang.get(comment_lang, COMMENTS_EN)
                content = random.choice(available_comments)

                comment = Comment(
                    idea_id=idea.id,
                    user_id=random.choice(users).id,
                    content=content,
                    language=comment_lang,
                    is_moderated=True,
                )
                db.add(comment)
                comment_count += 1
                comment_language_counts[comment_lang] = (
                    comment_language_counts.get(comment_lang, 0) + 1
                )

        for lang, count in comment_language_counts.items():
            print(f"  Created {count} comments in {lang.upper()}")

        print(f"  Total: {comment_count} comments")

        db.commit()

        # Summary
        print("\n" + "=" * 60)
        print("Seed complete!")
        print("=" * 60)
        print(f"\nInstance: {instance_id}")
        print(f"Languages: {', '.join(languages_for_ideas)}")
        print(f"Ideas: {len(ideas)}")
        print(f"Comments: {comment_count}")
        print(f"Votes: {vote_count}")
        print("\nTest user credentials:")
        print("  Email: user1@test.com")
        print("  Password: TestPass123!")
        print("\nAdmin credentials (check your .env file):")
        print("  Email: (ADMIN_EMAIL from .env)")
        print("  Password: (ADMIN_PASSWORD from .env)")
        print("=" * 60)

    except Exception as e:
        print(f"\nError seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_multilingual_data()
