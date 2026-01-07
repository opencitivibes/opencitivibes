#!/usr/bin/env python3
# ruff: noqa: E402
# E402 disabled: sys.path modification must happen before local imports
"""
Generate test data for the OpenCitiVibes platform.

This script creates a comprehensive test database with:
- Multiple users (regular, admins, category admins)
- Ideas with various statuses spread over time
- Tags and idea-tag associations
- Comments (normal, flagged, hidden, pending approval)
- Votes (upvotes and downvotes) with quality selections
- Content flags
- User penalties and appeals
- Law 25 compliance data (policy versions, consent logs)
- Analytics-friendly date distribution

Usage:
    cd backend

    # Small dataset (default) - for quick development testing
    uv run python scripts/generate_test_data.py

    # Medium dataset - realistic small-scale deployment
    uv run python scripts/generate_test_data.py --size medium

    # Large dataset - city-scale stress testing
    uv run python scripts/generate_test_data.py --size large

Instance-specific generation (uses language distribution from config):
    # Montreal instance (70% FR, 30% EN)
    PLATFORM_CONFIG_PATH=/path/to/instances/montreal/platform.config.json \\
        uv run python scripts/generate_test_data.py --size small

    # Quebec instance (50% FR, 35% EN, 15% ES)
    PLATFORM_CONFIG_PATH=/path/to/instances/quebec/platform.config.json \\
        uv run python scripts/generate_test_data.py --size small

    # Calgary instance (100% EN)
    PLATFORM_CONFIG_PATH=/path/to/instances/calgary/platform.config.json \\
        uv run python scripts/generate_test_data.py --size small

    # SOCENV/CDN-NDG instance (65% FR, 35% EN)
    PLATFORM_CONFIG_PATH=/path/to/instances/socenv/platform.config.json \\
        uv run python scripts/generate_test_data.py --size small

The script will create: backend/data/opencitivibes_test_{size}.db
"""

import argparse
import random
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add backend to path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import bcrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from repositories.database import Base
from repositories.db_models import (  # noqa: F401
    AdminNote,
    AdminRole,
    Appeal,
    AppealStatus,
    Category,
    CategoryQuality,
    Comment,
    ContentFlag,
    ContentType,
    EmailLoginCode,
    FlagReason,
    FlagStatus,
    Idea,
    IdeaStatus,
    IdeaTag,
    KeywordWatchlist,
    LoginEvent,
    LoginEventType,
    LoginFailureReason,
    PenaltyStatus,
    PenaltyType,
    PrivacyIncident,
    Quality,
    SecurityAuditLog,
    ShareEvent,
    SharePlatform,
    Tag,
    User,
    UserBackupCode,
    UserPenalty,
    UserTOTPSecret,
    Vote,
    VoteQuality,
    VoteType,
)
from services.config_service import get_config


def _get_admin_email_domain() -> str:
    """Get email domain from contact config.

    Returns:
        Email domain extracted from platform config contact email.
    """
    try:
        config = get_config()
        email = config.contact.email
        return email.split("@")[1] if "@" in email else "opencitivibes.local"
    except Exception:
        return "opencitivibes.local"


def _get_test_admin_email(index: int) -> str:
    """Generate test admin email using config domain.

    Args:
        index: Admin index number.

    Returns:
        Admin email address.
    """
    domain = _get_admin_email_domain()
    return f"admin{index}@{domain}"


def _get_test_category_admin_email(index: int) -> str:
    """Generate test category admin email using config domain.

    Args:
        index: Category admin index number.

    Returns:
        Category admin email address.
    """
    domain = _get_admin_email_domain()
    return f"catadmin{index}@{domain}"


def _get_instance_languages() -> tuple[list[str], list[float]]:
    """Get language distribution based on instance configuration.

    Returns:
        Tuple of (language codes list, probabilities list).
        - Montreal: 70% FR, 30% EN
        - Quebec: 50% FR, 35% EN, 15% ES
        - Calgary: 100% EN
        - SOCENV (CDN-NDG): 65% FR, 35% EN (multicultural neighborhood)
    """
    import json
    import os

    try:
        # Read raw JSON to get instance ID (not in Pydantic model)
        config_path = os.environ.get("PLATFORM_CONFIG_PATH")
        if config_path:
            with open(config_path) as f:
                data = json.load(f)
            instance_id = data.get("instance", {}).get("id", "montreal")
            supported_locales = data.get("localization", {}).get(
                "supported_locales", ["fr", "en"]
            )
        else:
            instance_id = "montreal"
            supported_locales = ["fr", "en"]

        if instance_id == "calgary":
            # Calgary: English only
            return ["en"], [1.0]
        elif instance_id == "quebec" and "es" in supported_locales:
            # Quebec: French dominant with English and Spanish
            return ["fr", "en", "es"], [0.50, 0.35, 0.15]
        elif instance_id == "socenv":
            # SOCENV (CDN-NDG): Multicultural neighborhood, more English
            return ["fr", "en"], [0.65, 0.35]
        else:
            # Montreal (default): French dominant with English
            return ["fr", "en"], [0.70, 0.30]
    except Exception:
        # Default to Montreal distribution
        return ["fr", "en"], [0.70, 0.30]


def _choose_random_language() -> str:
    """Choose a random language based on instance configuration.

    Returns:
        Language code (fr, en, or es).
    """
    languages, weights = _get_instance_languages()
    return random.choices(languages, weights=weights, k=1)[0]


# =============================================================================
# Size Configuration
# =============================================================================


@dataclass
class DatasetConfig:
    """Configuration for dataset size."""

    name: str
    description: str

    # Users
    num_regular_users: int
    num_category_admins: int
    num_global_admins: int

    # Content
    num_ideas: int
    num_tags: int
    comments_per_idea_range: tuple[int, int]
    votes_per_idea_range: tuple[int, int]
    tags_per_idea_range: tuple[int, int]

    # Moderation
    num_flagged_comments: int
    num_flagged_ideas: int
    num_user_penalties: int
    num_appeals: int
    num_admin_notes: int

    # Time distribution
    date_range_days: int

    # Qualities
    quality_selection_probability: float  # Probability that an upvote gets qualities
    qualities_per_vote_range: tuple[int, int]  # Range of qualities per vote

    # Comment likes
    comment_like_probability: float  # Probability that a comment gets likes
    likes_per_comment_range: tuple[int, int]  # Range of likes per comment

    # Security & Analytics (new tables)
    num_login_events: int  # Login events for security audit
    num_share_events: int  # Social share events for analytics
    num_security_audit_logs: int  # Security audit log entries
    num_official_users: int  # Users with official role

    # Ideas with edits (approved then edited flow)
    ideas_with_edits_probability: float  # Probability an approved idea has been edited

    # Batch sizes for large datasets
    batch_size: int = 1000


# Montreal context:
# - Population: ~1.8 million
# - Typical civic engagement: 1-5% of population might register
# - Active users: 10-20% of registered users

DATASET_CONFIGS = {
    "small": DatasetConfig(
        name="SMALL",
        description="Development/testing - quick iteration",
        # Users
        num_regular_users=100,
        num_category_admins=5,
        num_global_admins=3,
        # Content
        num_ideas=500,
        num_tags=30,
        comments_per_idea_range=(0, 15),
        votes_per_idea_range=(0, 50),
        tags_per_idea_range=(0, 5),
        # Moderation
        num_flagged_comments=50,
        num_flagged_ideas=20,
        num_user_penalties=15,
        num_appeals=5,
        num_admin_notes=10,
        # Time
        date_range_days=365,
        # Qualities
        quality_selection_probability=0.4,  # 40% of upvotes have qualities
        qualities_per_vote_range=(1, 3),
        # Comment likes
        comment_like_probability=0.3,  # 30% of comments get likes
        likes_per_comment_range=(1, 8),
        # Security & Analytics
        num_login_events=500,
        num_share_events=200,
        num_security_audit_logs=100,
        num_official_users=5,
        # Edit tracking
        ideas_with_edits_probability=0.05,  # 5% of approved ideas have edits
        batch_size=500,
    ),
    "medium": DatasetConfig(
        name="MEDIUM",
        description="Realistic small-scale deployment (~0.05% of Montreal)",
        # Users: ~1,000 registered users
        num_regular_users=1_000,
        num_category_admins=10,
        num_global_admins=5,
        # Content: active community
        num_ideas=5_000,
        num_tags=50,
        comments_per_idea_range=(0, 20),
        votes_per_idea_range=(0, 100),
        tags_per_idea_range=(0, 5),
        # Moderation
        num_flagged_comments=500,
        num_flagged_ideas=200,
        num_user_penalties=150,
        num_appeals=50,
        num_admin_notes=100,
        # Time: 2 years of data
        date_range_days=730,
        # Qualities
        quality_selection_probability=0.5,  # 50% of upvotes have qualities
        qualities_per_vote_range=(1, 4),
        # Comment likes
        comment_like_probability=0.4,  # 40% of comments get likes
        likes_per_comment_range=(1, 15),
        # Security & Analytics
        num_login_events=5_000,
        num_share_events=2_000,
        num_security_audit_logs=1_000,
        num_official_users=20,
        # Edit tracking
        ideas_with_edits_probability=0.08,  # 8% of approved ideas have edits
        batch_size=1000,
    ),
    "large": DatasetConfig(
        name="LARGE",
        description="City-scale stress test (~0.5% of Montreal)",
        # Users: ~10,000 registered users (realistic for popular civic platform)
        num_regular_users=10_000,
        num_category_admins=20,
        num_global_admins=10,
        # Content: very active community
        num_ideas=50_000,
        num_tags=100,
        comments_per_idea_range=(0, 30),
        votes_per_idea_range=(0, 200),
        tags_per_idea_range=(0, 5),
        # Moderation
        num_flagged_comments=5_000,
        num_flagged_ideas=2_000,
        num_user_penalties=1_500,
        num_appeals=500,
        num_admin_notes=1_000,
        # Time: 3 years of data
        date_range_days=1095,
        # Qualities
        quality_selection_probability=0.6,  # 60% of upvotes have qualities
        qualities_per_vote_range=(1, 4),
        # Comment likes
        comment_like_probability=0.5,  # 50% of comments get likes
        likes_per_comment_range=(1, 25),
        # Security & Analytics
        num_login_events=50_000,
        num_share_events=20_000,
        num_security_audit_logs=10_000,
        num_official_users=100,
        # Edit tracking
        ideas_with_edits_probability=0.10,  # 10% of approved ideas have edits
        batch_size=5000,
    ),
}

# Test database path (set by main based on size)
TEST_DB_PATH: Path = backend_dir / "data" / "opencitivibes_test.db"


def get_db_path(size: str) -> Path:
    """Get database path for given size."""
    return backend_dir / "data" / f"opencitivibes_test_{size}.db"


# Current config (set by main)
config: DatasetConfig = DATASET_CONFIGS["small"]


def get_password_hash(password: str) -> str:
    """Hash password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def random_date_in_range(start_days_ago: int | None = None) -> datetime:
    """Generate a random datetime within the date range."""
    if start_days_ago is None:
        start_days_ago = config.date_range_days
    days_ago = random.randint(0, start_days_ago)
    hours = random.randint(0, 23)
    minutes = random.randint(0, 59)
    return datetime.now(timezone.utc) - timedelta(
        days=days_ago, hours=hours, minutes=minutes
    )


def random_date_after(base_date: datetime, max_days: int = 30) -> datetime:
    """Generate a random datetime after base_date."""
    days = random.randint(1, max_days)
    hours = random.randint(0, 23)
    return base_date + timedelta(days=days, hours=hours)


# Sample data for generating realistic content
FIRST_NAMES_FR = [
    "Jean",
    "Marie",
    "Pierre",
    "Sophie",
    "Marc",
    "Isabelle",
    "François",
    "Catherine",
    "Michel",
    "Nathalie",
    "André",
    "Julie",
    "Paul",
    "Mélanie",
    "Robert",
    "Anne",
    "Claude",
    "Émilie",
    "Jacques",
    "Sarah",
    "Louis",
    "Camille",
    "Philippe",
    "Laura",
    "Nicolas",
    "Emma",
    "Alexandre",
    "Léa",
    "Thomas",
    "Chloé",
    "Daniel",
    "Alice",
    "Martin",
    "Charlotte",
    "Bruno",
    "Juliette",
    "David",
    "Zoé",
    "Patrick",
    "Amélie",
    "Étienne",
    "Gabrielle",
    "Simon",
    "Valérie",
    "Mathieu",
    "Caroline",
    "Vincent",
    "Audrey",
    "Yves",
    "Stéphanie",
    "Benoit",
    "Karine",
    "Guillaume",
    "Martine",
    "Olivier",
    "Sylvie",
    "Sébastien",
    "Hélène",
    "Maxime",
    "Josée",
    "Frédéric",
    "Manon",
    "Éric",
    "Geneviève",
]

LAST_NAMES_FR = [
    "Tremblay",
    "Gagnon",
    "Roy",
    "Côté",
    "Bouchard",
    "Gauthier",
    "Morin",
    "Lavoie",
    "Fortin",
    "Gagné",
    "Ouellet",
    "Pelletier",
    "Bélanger",
    "Lévesque",
    "Bergeron",
    "Leblanc",
    "Paquette",
    "Girard",
    "Simard",
    "Boucher",
    "Caron",
    "Beaulieu",
    "Cloutier",
    "Dubois",
    "Poirier",
    "Fournier",
    "Lapointe",
    "Leclerc",
    "Martin",
    "Lefebvre",
    "Bernard",
    "Richard",
    "Dupont",
    "Moreau",
    "Lambert",
    "Giroux",
    "Hébert",
    "Desjardins",
    "Carrier",
    "Breton",
    "Bélisle",
    "Mercier",
    "Dufour",
    "Arsenault",
    "Champagne",
    "Paradis",
    "Bolduc",
    "Fontaine",
    "Gosselin",
    "Michaud",
]

IDEA_TITLES_FR = [
    "Améliorer les pistes cyclables dans le quartier",
    "Plus d'espaces verts dans le centre-ville",
    "Réduire le bruit sur les grandes artères",
    "Installer des fontaines d'eau potable",
    "Créer un marché fermier hebdomadaire",
    "Améliorer l'éclairage des parcs",
    "Développer le covoiturage municipal",
    "Créer des jardins communautaires",
    "Améliorer l'accessibilité des transports",
    "Installer des stations de réparation vélo",
    "Réduire les îlots de chaleur urbains",
    "Améliorer la propreté des rues",
    "Créer des zones piétonnes",
    "Développer le compostage collectif",
    "Améliorer la sécurité aux intersections",
    "Créer des aires de jeux pour enfants",
    "Développer les espaces de travail partagés",
    "Améliorer la signalisation touristique",
    "Installer des bornes de recharge électrique",
    "Créer des ruelles vertes",
    "Améliorer le déneigement des trottoirs",
    "Développer les toits verts",
    "Créer un réseau de bibliothèques de rue",
    "Améliorer la gestion des eaux pluviales",
    "Installer des panneaux solaires communautaires",
    "Créer des parcours de santé urbains",
    "Améliorer l'accès aux arts et culture",
    "Développer le transport fluvial",
    "Créer des espaces de détente extérieurs",
    "Améliorer les connexions inter-quartiers",
    "Ajouter des bancs publics dans les parcs",
    "Créer des corridors de biodiversité",
    "Installer des abreuvoirs pour animaux",
    "Développer le réseau de métro",
    "Créer des zones de livraison urbaine",
    "Améliorer l'accès pour personnes à mobilité réduite",
    "Installer des capteurs de qualité de l'air",
    "Créer des espaces de coworking municipaux",
    "Développer l'agriculture urbaine",
    "Améliorer la connectivité WiFi publique",
]

IDEA_DESCRIPTIONS_FR = [
    "Cette initiative permettrait d'améliorer la qualité de vie des résidents en offrant des alternatives de transport plus durables et accessibles.",
    "En développant cette idée, nous pourrions créer un environnement plus sain et plus agréable pour tous les citoyens du quartier.",
    "Ce projet s'inscrit dans une vision à long terme pour rendre notre ville plus verte et plus résiliente face aux changements climatiques.",
    "L'implantation de cette solution permettrait de résoudre un problème récurrent signalé par de nombreux résidents.",
    "Cette proposition vise à renforcer le tissu social de notre communauté en créant des espaces de rencontre et d'échange.",
    "En adoptant cette mesure, la ville pourrait réaliser des économies tout en améliorant les services aux citoyens.",
    "Ce concept innovant a déjà fait ses preuves dans d'autres villes et pourrait être adapté à notre contexte local.",
    "Cette idée répond à un besoin exprimé lors des consultations publiques et mérite d'être étudiée sérieusement.",
    "L'objectif principal est de favoriser l'inclusion et l'accessibilité pour tous les groupes de la population.",
    "Ce projet pilote pourrait être déployé progressivement dans différents quartiers de la ville.",
    "Cette amélioration contribuerait à réduire notre empreinte carbone collective.",
    "La mise en œuvre de cette idée favoriserait le développement économique local.",
    "Ce projet permettrait de moderniser nos infrastructures vieillissantes.",
    "Cette initiative renforcerait le sentiment d'appartenance à notre communauté.",
    "L'adoption de cette mesure placerait Montréal en tête des villes innovantes.",
]

COMMENT_TEMPLATES_FR = [
    "Excellente idée ! J'espère que la ville l'adopera.",
    "Je suis totalement d'accord avec cette proposition.",
    "Il faudrait aussi considérer l'impact sur les commerces locaux.",
    "C'est exactement ce dont notre quartier a besoin.",
    "Bonne idée, mais les coûts pourraient être un obstacle.",
    "J'aimerais voir plus de détails sur la mise en œuvre.",
    "Cette initiative serait bénéfique pour toute la communauté.",
    "Il y a des projets similaires à Toronto qui fonctionnent bien.",
    "Je soutiens cette idée à 100% !",
    "Il faudrait consulter les résidents avant de procéder.",
    "Comment cette idée serait-elle financée ?",
    "J'ai quelques réserves, mais le concept est intéressant.",
    "Bravo pour cette proposition constructive !",
    "C'est une priorité selon moi.",
    "Il faudrait un plan d'action détaillé.",
    "Je me porte volontaire pour aider à la réalisation.",
    "Cette idée devrait être étendue à toute la ville.",
    "Pas convaincu que ce soit la meilleure approche.",
    "Belle initiative citoyenne !",
    "Quelle serait l'échéance pour ce projet ?",
    "Cela améliorerait vraiment notre qualité de vie.",
    "Je vis dans ce quartier et j'approuve totalement.",
    "Avez-vous consulté les experts du domaine ?",
    "C'est un investissement pour l'avenir.",
    "La ville devrait prioriser ce type de projets.",
]

# English content templates
IDEA_TITLES_EN = [
    "Improve bike lanes in the neighborhood",
    "More green spaces downtown",
    "Reduce noise on major roads",
    "Install drinking water fountains",
    "Create a weekly farmers market",
    "Improve park lighting",
    "Develop municipal carpooling",
    "Create community gardens",
    "Improve transit accessibility",
    "Install bike repair stations",
    "Reduce urban heat islands",
    "Improve street cleanliness",
    "Create pedestrian zones",
    "Develop community composting",
    "Improve intersection safety",
    "Create children's playgrounds",
    "Develop shared workspaces",
    "Improve tourist signage",
    "Install electric vehicle charging stations",
    "Create green alleys",
    "Improve sidewalk snow clearing",
    "Develop green roofs",
    "Create a street library network",
    "Improve stormwater management",
    "Install community solar panels",
    "Create urban fitness trails",
    "Improve access to arts and culture",
    "Develop river transportation",
    "Create outdoor relaxation spaces",
    "Improve inter-neighborhood connections",
    "Add public benches in parks",
    "Create biodiversity corridors",
    "Install pet water fountains",
    "Expand the subway network",
    "Create urban delivery zones",
    "Improve accessibility for mobility-impaired",
    "Install air quality sensors",
    "Create municipal coworking spaces",
    "Develop urban agriculture",
    "Improve public WiFi connectivity",
]

IDEA_DESCRIPTIONS_EN = [
    "This initiative would improve residents' quality of life by offering more sustainable and accessible transportation alternatives.",
    "By developing this idea, we could create a healthier and more pleasant environment for all neighborhood citizens.",
    "This project aligns with a long-term vision to make our city greener and more resilient to climate change.",
    "Implementing this solution would address a recurring problem reported by many residents.",
    "This proposal aims to strengthen our community's social fabric by creating spaces for meeting and exchange.",
    "By adopting this measure, the city could save money while improving services to citizens.",
    "This innovative concept has already proven successful in other cities and could be adapted to our local context.",
    "This idea responds to a need expressed during public consultations and deserves serious consideration.",
    "The main objective is to promote inclusion and accessibility for all population groups.",
    "This pilot project could be gradually deployed in different neighborhoods of the city.",
    "This improvement would contribute to reducing our collective carbon footprint.",
    "Implementing this idea would foster local economic development.",
    "This project would modernize our aging infrastructure.",
    "This initiative would strengthen the sense of belonging to our community.",
    "Adopting this measure would place our city at the forefront of innovative cities.",
]

COMMENT_TEMPLATES_EN = [
    "Excellent idea! I hope the city adopts it.",
    "I totally agree with this proposal.",
    "We should also consider the impact on local businesses.",
    "This is exactly what our neighborhood needs.",
    "Good idea, but costs could be an obstacle.",
    "I'd like to see more details on implementation.",
    "This initiative would benefit the entire community.",
    "There are similar projects in Toronto that work well.",
    "I support this idea 100%!",
    "Residents should be consulted before proceeding.",
    "How would this idea be funded?",
    "I have some reservations, but the concept is interesting.",
    "Well done on this constructive proposal!",
    "This is a priority in my opinion.",
    "A detailed action plan would be needed.",
    "I volunteer to help with implementation.",
    "This idea should be extended citywide.",
    "Not convinced this is the best approach.",
    "Great citizen initiative!",
    "What would be the timeline for this project?",
    "This would really improve our quality of life.",
    "I live in this neighborhood and fully approve.",
    "Have you consulted experts in this field?",
    "This is an investment for the future.",
    "The city should prioritize these types of projects.",
]

# Spanish content templates
IDEA_TITLES_ES = [
    "Mejorar los carriles para bicicletas en el barrio",
    "Más espacios verdes en el centro",
    "Reducir el ruido en las avenidas principales",
    "Instalar fuentes de agua potable",
    "Crear un mercado de agricultores semanal",
    "Mejorar la iluminación de los parques",
    "Desarrollar el transporte compartido municipal",
    "Crear jardines comunitarios",
    "Mejorar la accesibilidad del transporte",
    "Instalar estaciones de reparación de bicicletas",
    "Reducir las islas de calor urbanas",
    "Mejorar la limpieza de las calles",
    "Crear zonas peatonales",
    "Desarrollar el compostaje colectivo",
    "Mejorar la seguridad en las intersecciones",
    "Crear áreas de juego para niños",
    "Desarrollar espacios de trabajo compartidos",
    "Mejorar la señalización turística",
    "Instalar estaciones de carga para vehículos eléctricos",
    "Crear callejones verdes",
    "Mejorar la limpieza de nieve en las aceras",
    "Desarrollar techos verdes",
    "Crear una red de bibliotecas callejeras",
    "Mejorar la gestión del agua de lluvia",
    "Instalar paneles solares comunitarios",
    "Crear senderos de salud urbanos",
    "Mejorar el acceso a las artes y la cultura",
    "Desarrollar el transporte fluvial",
    "Crear espacios de descanso al aire libre",
    "Mejorar las conexiones entre barrios",
    "Agregar bancos públicos en los parques",
    "Crear corredores de biodiversidad",
    "Instalar bebederos para mascotas",
    "Expandir la red del metro",
    "Crear zonas de entrega urbana",
    "Mejorar la accesibilidad para personas con movilidad reducida",
    "Instalar sensores de calidad del aire",
    "Crear espacios de coworking municipales",
    "Desarrollar la agricultura urbana",
    "Mejorar la conectividad WiFi pública",
]

IDEA_DESCRIPTIONS_ES = [
    "Esta iniciativa mejoraría la calidad de vida de los residentes al ofrecer alternativas de transporte más sostenibles y accesibles.",
    "Al desarrollar esta idea, podríamos crear un ambiente más saludable y agradable para todos los ciudadanos del barrio.",
    "Este proyecto se alinea con una visión a largo plazo para hacer nuestra ciudad más verde y resistente al cambio climático.",
    "La implementación de esta solución abordaría un problema recurrente reportado por muchos residentes.",
    "Esta propuesta busca fortalecer el tejido social de nuestra comunidad creando espacios de encuentro e intercambio.",
    "Al adoptar esta medida, la ciudad podría ahorrar dinero mientras mejora los servicios a los ciudadanos.",
    "Este concepto innovador ya ha demostrado ser exitoso en otras ciudades y podría adaptarse a nuestro contexto local.",
    "Esta idea responde a una necesidad expresada durante las consultas públicas y merece seria consideración.",
    "El objetivo principal es promover la inclusión y accesibilidad para todos los grupos de la población.",
    "Este proyecto piloto podría implementarse gradualmente en diferentes barrios de la ciudad.",
    "Esta mejora contribuiría a reducir nuestra huella de carbono colectiva.",
    "La implementación de esta idea fomentaría el desarrollo económico local.",
    "Este proyecto modernizaría nuestra infraestructura envejecida.",
    "Esta iniciativa fortalecería el sentido de pertenencia a nuestra comunidad.",
    "Adoptar esta medida colocaría a nuestra ciudad a la vanguardia de las ciudades innovadoras.",
]

COMMENT_TEMPLATES_ES = [
    "¡Excelente idea! Espero que la ciudad la adopte.",
    "Estoy totalmente de acuerdo con esta propuesta.",
    "También deberíamos considerar el impacto en los negocios locales.",
    "Esto es exactamente lo que nuestro barrio necesita.",
    "Buena idea, pero los costos podrían ser un obstáculo.",
    "Me gustaría ver más detalles sobre la implementación.",
    "Esta iniciativa beneficiaría a toda la comunidad.",
    "Hay proyectos similares en otras ciudades que funcionan bien.",
    "¡Apoyo esta idea al 100%!",
    "Se debería consultar a los residentes antes de proceder.",
    "¿Cómo se financiaría esta idea?",
    "Tengo algunas reservas, pero el concepto es interesante.",
    "¡Bien hecho con esta propuesta constructiva!",
    "Esto es una prioridad en mi opinión.",
    "Se necesitaría un plan de acción detallado.",
    "Me ofrezco como voluntario para ayudar con la implementación.",
    "Esta idea debería extenderse a toda la ciudad.",
    "No estoy convencido de que este sea el mejor enfoque.",
    "¡Gran iniciativa ciudadana!",
    "¿Cuál sería el plazo para este proyecto?",
    "Esto realmente mejoraría nuestra calidad de vida.",
    "Vivo en este barrio y apruebo totalmente.",
    "¿Han consultado a expertos en este campo?",
    "Esta es una inversión para el futuro.",
    "La ciudad debería priorizar este tipo de proyectos.",
]

# Language-indexed content maps for easy lookup
IDEA_TITLES = {"fr": IDEA_TITLES_FR, "en": IDEA_TITLES_EN, "es": IDEA_TITLES_ES}
IDEA_DESCRIPTIONS = {
    "fr": IDEA_DESCRIPTIONS_FR,
    "en": IDEA_DESCRIPTIONS_EN,
    "es": IDEA_DESCRIPTIONS_ES,
}
COMMENT_TEMPLATES = {
    "fr": COMMENT_TEMPLATES_FR,
    "en": COMMENT_TEMPLATES_EN,
    "es": COMMENT_TEMPLATES_ES,
}

BASE_TAG_NAMES = [
    "Transport",
    "Environnement",
    "Sécurité",
    "Culture",
    "Parcs",
    "Vélo",
    "Piétons",
    "Commerces",
    "Logement",
    "Éducation",
    "Santé",
    "Accessibilité",
    "Technologie",
    "Alimentation",
    "Sports",
    "Loisirs",
    "Patrimoine",
    "Urbanisme",
    "Économie",
    "Famille",
    "Aînés",
    "Jeunesse",
    "Diversité",
    "Innovation",
    "Climat",
    "Propreté",
    "Éclairage",
    "Bruit",
    "Arbres",
    "Eau",
    "Déneigement",
    "Stationnement",
    "Mobilité",
    "Recyclage",
    "Compostage",
    "Biodiversité",
    "Energie",
    "Wifi",
    "Événements",
    "Festivals",
    "Musées",
    "Bibliothèques",
    "Piscines",
    "Patinoires",
    "Marchés",
    "Jardins",
    "Ruelles",
    "Trottoirs",
    "Chaussées",
    "Ponts",
]

# =============================================================================
# Quality Definitions
# =============================================================================

DEFAULT_QUALITIES = [
    {
        "key": "community_benefit",
        "name_en": "Benefits everyone",
        "name_fr": "Bénéficie à tous",
        "description_en": "This idea would help the broader community",
        "description_fr": "Cette idée aiderait la communauté en général",
        "icon": "heart",
        "color": "rose",
        "is_default": True,
        "display_order": 1,
    },
    {
        "key": "quality_of_life",
        "name_en": "Improves daily life",
        "name_fr": "Améliore le quotidien",
        "description_en": "This would make day-to-day life better",
        "description_fr": "Cela améliorerait la vie au quotidien",
        "icon": "sun",
        "color": "amber",
        "is_default": True,
        "display_order": 2,
    },
    {
        "key": "urgent",
        "name_en": "Addresses urgent problem",
        "name_fr": "Problème urgent",
        "description_en": "This solves a pressing issue that needs attention",
        "description_fr": "Cela résout un problème pressant",
        "icon": "alert-triangle",
        "color": "red",
        "is_default": True,
        "display_order": 3,
    },
    {
        "key": "would_volunteer",
        "name_en": "I'd help make this happen",
        "name_fr": "Je participerais",
        "description_en": "I would volunteer my time to help implement this",
        "description_fr": "Je donnerais de mon temps pour aider à réaliser ceci",
        "icon": "hand-helping",
        "color": "emerald",
        "is_default": True,
        "display_order": 4,
    },
]

CATEGORY_SPECIFIC_QUALITIES = [
    {
        "key": "eco_friendly",
        "name_en": "Environmentally friendly",
        "name_fr": "Écologique",
        "description_en": "This idea helps the environment",
        "description_fr": "Cette idée aide l'environnement",
        "icon": "leaf",
        "color": "green",
        "is_default": False,
        "display_order": 5,
    },
    {
        "key": "family_friendly",
        "name_en": "Family-friendly",
        "name_fr": "Familial",
        "description_en": "Good for families with children",
        "description_fr": "Bon pour les familles avec enfants",
        "icon": "users",
        "color": "blue",
        "is_default": False,
        "display_order": 6,
    },
]


def create_policy_versions(session):
    """Create policy version records for Law 25 compliance testing.

    Creates version history for both privacy policy and terms of service,
    enabling testing of reconsent flows when policies are updated.
    """
    from repositories.db_models import PolicyVersion

    print("  Creating policy versions...")
    now = datetime.now(timezone.utc)
    versions = []

    # Privacy policy versions
    privacy_v1 = PolicyVersion(
        policy_type="privacy",
        version="1.0",
        effective_date=now - timedelta(days=365),
        summary_en="Initial privacy policy covering data collection and usage.",
        summary_fr="Politique de confidentialité initiale couvrant la collecte et "
        "l'utilisation des données.",
        requires_reconsent=False,
        created_at=now - timedelta(days=365),
    )
    session.add(privacy_v1)
    versions.append(privacy_v1)

    privacy_v1_1 = PolicyVersion(
        policy_type="privacy",
        version="1.1",
        effective_date=now - timedelta(days=90),
        summary_en="Added Law 25 compliance: consent management, data export, "
        "privacy settings.",
        summary_fr="Ajout de la conformité Loi 25 : gestion du consentement, "
        "exportation des données, paramètres de confidentialité.",
        requires_reconsent=True,  # Major update requires reconsent
        created_at=now - timedelta(days=90),
    )
    session.add(privacy_v1_1)
    versions.append(privacy_v1_1)

    # Terms of service versions
    terms_v1 = PolicyVersion(
        policy_type="terms",
        version="1.0",
        effective_date=now - timedelta(days=365),
        summary_en="Initial terms of service for platform usage.",
        summary_fr="Conditions d'utilisation initiales pour l'utilisation de la "
        "plateforme.",
        requires_reconsent=False,
        created_at=now - timedelta(days=365),
    )
    session.add(terms_v1)
    versions.append(terms_v1)

    session.commit()
    print(f"  Created {len(versions)} policy versions")
    return versions


def create_consent_logs(session, users):
    """Create consent log entries for Law 25 audit trail testing.

    Creates initial consent logs simulating user registration consent,
    plus some consent updates (marketing opt-in/out).
    """
    from repositories.db_models import ConsentLog

    print("  Creating consent logs...")
    logs = []

    # Create registration consent logs for all users
    for user in users:
        # Terms consent at registration
        terms_log = ConsentLog(
            user_id=user.id,
            consent_type="terms",
            action="granted",
            policy_version="1.0",
            ip_address="192.168.1." + str(random.randint(1, 254)),
            user_agent="Mozilla/5.0 (Test Data Generator)",
            created_at=user.created_at,
        )
        session.add(terms_log)
        logs.append(terms_log)

        # Privacy consent at registration
        privacy_log = ConsentLog(
            user_id=user.id,
            consent_type="privacy",
            action="granted",
            policy_version="1.0",
            ip_address="192.168.1." + str(random.randint(1, 254)),
            user_agent="Mozilla/5.0 (Test Data Generator)",
            created_at=user.created_at,
        )
        session.add(privacy_log)
        logs.append(privacy_log)

        # Marketing consent at registration (if opted in)
        if user.marketing_consent:
            marketing_log = ConsentLog(
                user_id=user.id,
                consent_type="marketing",
                action="granted",
                policy_version=None,
                ip_address="192.168.1." + str(random.randint(1, 254)),
                user_agent="Mozilla/5.0 (Test Data Generator)",
                created_at=user.created_at,
            )
            session.add(marketing_log)
            logs.append(marketing_log)

    # Add some marketing consent changes (opt-out then opt-in)
    sample_users = random.sample(users, min(20, len(users)))
    for user in sample_users:
        if user.marketing_consent:
            # Simulate opt-out then opt-in
            opt_out_date = random_date_after(user.created_at, max_days=60)
            opt_out_log = ConsentLog(
                user_id=user.id,
                consent_type="marketing",
                action="withdrawn",
                policy_version=None,
                ip_address="192.168.1." + str(random.randint(1, 254)),
                user_agent="Mozilla/5.0 (Test Data Generator)",
                created_at=opt_out_date,
            )
            session.add(opt_out_log)
            logs.append(opt_out_log)

            opt_in_log = ConsentLog(
                user_id=user.id,
                consent_type="marketing",
                action="granted",
                policy_version=None,
                ip_address="192.168.1." + str(random.randint(1, 254)),
                user_agent="Mozilla/5.0 (Test Data Generator)",
                created_at=random_date_after(opt_out_date, max_days=30),
            )
            session.add(opt_in_log)
            logs.append(opt_in_log)

    session.commit()
    print(f"  Created {len(logs)} consent log entries")
    return logs


def create_categories(session):
    """Create default categories."""
    categories_data = [
        (
            "Transport & Mobility",
            "Transport et Mobilité",
            "Ideas about public transit, cycling, walking, and vehicle traffic",
            "Idées sur le transport en commun, le vélo, la marche et la circulation",
        ),
        (
            "Environment & Green Spaces",
            "Environnement et Espaces verts",
            "Ideas about parks, urban greening, sustainability, and climate action",
            "Idées sur les parcs, le verdissement urbain, le développement durable et l'action climatique",
        ),
        (
            "Safety & Security",
            "Sécurité et Sûreté",
            "Ideas about public safety, lighting, crime prevention, and emergency services",
            "Idées sur la sécurité publique, l'éclairage, la prévention du crime et les services d'urgence",
        ),
        (
            "Culture & Community",
            "Culture et Communauté",
            "Ideas about arts, festivals, community centers, and social programs",
            "Idées sur les arts, les festivals, les centres communautaires et les programmes sociaux",
        ),
        (
            "Urban Development",
            "Développement urbain",
            "Ideas about housing, construction, zoning, and city planning",
            "Idées sur le logement, la construction, le zonage et l'aménagement urbain",
        ),
        (
            "Economy & Business",
            "Économie et Commerce",
            "Ideas about local businesses, employment, and economic development",
            "Idées sur les commerces locaux, l'emploi et le développement économique",
        ),
        (
            "Technology & Innovation",
            "Technologie et Innovation",
            "Ideas about smart city initiatives, digital services, and innovation",
            "Idées sur les initiatives de ville intelligente, les services numériques et l'innovation",
        ),
        (
            "Health & Wellness",
            "Santé et Bien-être",
            "Ideas about healthcare, sports facilities, and quality of life",
            "Idées sur les soins de santé, les installations sportives et la qualité de vie",
        ),
    ]

    categories = []
    for name_en, name_fr, desc_en, desc_fr in categories_data:
        cat = Category(
            name_en=name_en,
            name_fr=name_fr,
            description_en=desc_en,
            description_fr=desc_fr,
        )
        session.add(cat)
        categories.append(cat)

    session.commit()
    print(f"  Created {len(categories)} categories")
    return categories


def create_tags(session):
    """Create tags."""
    tags = []
    tag_names = BASE_TAG_NAMES[: config.num_tags]

    for name in tag_names:
        tag = Tag(
            name=name.lower(),
            display_name=name,
            created_at=random_date_in_range(),
        )
        session.add(tag)
        tags.append(tag)

    session.commit()
    print(f"  Created {len(tags)} tags")
    return tags


def create_qualities(session, categories):
    """Create quality definitions."""
    print("  Creating qualities...")

    qualities = []
    now = datetime.now(timezone.utc)

    # Create default qualities
    for quality_data in DEFAULT_QUALITIES:
        quality = Quality(
            key=quality_data["key"],
            name_en=quality_data["name_en"],
            name_fr=quality_data["name_fr"],
            description_en=quality_data.get("description_en"),
            description_fr=quality_data.get("description_fr"),
            icon=quality_data.get("icon"),
            color=quality_data.get("color"),
            is_default=quality_data["is_default"],
            is_active=True,
            display_order=quality_data["display_order"],
            created_at=now,
        )
        session.add(quality)
        qualities.append(quality)

    # Create category-specific qualities
    category_specific = []
    for quality_data in CATEGORY_SPECIFIC_QUALITIES:
        quality = Quality(
            key=quality_data["key"],
            name_en=quality_data["name_en"],
            name_fr=quality_data["name_fr"],
            description_en=quality_data.get("description_en"),
            description_fr=quality_data.get("description_fr"),
            icon=quality_data.get("icon"),
            color=quality_data.get("color"),
            is_default=False,
            is_active=True,
            display_order=quality_data["display_order"],
            created_at=now,
        )
        session.add(quality)
        category_specific.append(quality)

    session.commit()

    # Assign category-specific qualities to categories
    print("  Assigning category-specific qualities...")
    for category in categories:
        category_name_lower = category.name_en.lower()

        # Eco-friendly for environment-related categories
        if any(
            word in category_name_lower
            for word in ["environment", "green", "nature", "park"]
        ):
            eco_quality = next(
                (q for q in category_specific if q.key == "eco_friendly"), None
            )
            if eco_quality:
                cat_quality = CategoryQuality(
                    category_id=category.id,
                    quality_id=eco_quality.id,
                    is_enabled=True,
                    display_order=5,
                )
                session.add(cat_quality)

        # Family-friendly for recreation/community categories
        if any(
            word in category_name_lower
            for word in ["family", "recreation", "community", "children", "park"]
        ):
            family_quality = next(
                (q for q in category_specific if q.key == "family_friendly"), None
            )
            if family_quality:
                cat_quality = CategoryQuality(
                    category_id=category.id,
                    quality_id=family_quality.id,
                    is_enabled=True,
                    display_order=6,
                )
                session.add(cat_quality)

    session.commit()
    print(
        f"  Created {len(qualities)} default + {len(category_specific)} "
        "category-specific qualities"
    )
    return qualities + category_specific


def create_users(session, password_map: dict):
    """Create users with various roles."""
    users = []
    print("  Creating users...")

    # Create global admins
    admin_password = "Admin123!"
    for i in range(config.num_global_admins):
        email = _get_test_admin_email(i + 1)
        username = f"admin{i + 1}"
        created_at = random_date_in_range()
        last_activity = random_date_after(created_at, max_days=30)
        user = User(
            email=email,
            username=username,
            display_name=f"Admin {i + 1}",
            hashed_password=get_password_hash(admin_password),
            is_global_admin=True,
            is_active=True,
            created_at=created_at,
            trust_score=100,
            approved_comments_count=random.randint(10, 50),
            requires_comment_approval=False,
            # Consent fields (Law 25 compliance)
            consent_terms_accepted=True,
            consent_privacy_accepted=True,
            consent_terms_version="1.0",
            consent_privacy_version="1.0",
            consent_timestamp=created_at,
            marketing_consent=False,
            # Retention tracking (Law 25 Phase 3)
            last_login_at=last_activity,
            last_activity_at=last_activity,
            # Privacy settings (Law 25 Phase 4)
            profile_visibility="public",
            show_display_name=True,
            show_avatar=True,
            show_activity=True,
            show_join_date=True,
        )
        session.add(user)
        users.append(user)
        password_map[email] = admin_password

    # Create category admins
    cat_admin_password = "CatAdmin123!"
    for i in range(config.num_category_admins):
        email = _get_test_category_admin_email(i + 1)
        username = f"catadmin{i + 1}"
        created_at = random_date_in_range()
        last_activity = random_date_after(created_at, max_days=30)
        user = User(
            email=email,
            username=username,
            display_name=f"Category Admin {i + 1}",
            hashed_password=get_password_hash(cat_admin_password),
            is_global_admin=False,
            is_active=True,
            created_at=created_at,
            trust_score=90,
            approved_comments_count=random.randint(5, 30),
            requires_comment_approval=False,
            # Consent fields (Law 25 compliance)
            consent_terms_accepted=True,
            consent_privacy_accepted=True,
            consent_terms_version="1.0",
            consent_privacy_version="1.0",
            consent_timestamp=created_at,
            marketing_consent=(has_marketing := random.random() > 0.5),
            marketing_consent_timestamp=created_at if has_marketing else None,
            # Retention tracking (Law 25 Phase 3)
            last_login_at=last_activity,
            last_activity_at=last_activity,
            # Privacy settings (Law 25 Phase 4)
            profile_visibility="public",
            show_display_name=True,
            show_avatar=True,
            show_activity=True,
            show_join_date=True,
        )
        session.add(user)
        users.append(user)
        password_map[email] = cat_admin_password

    session.commit()
    print(
        f"    Created {config.num_global_admins} global admins, {config.num_category_admins} category admins"
    )

    # Create regular users in batches
    regular_password = "User123!"
    used_emails: set[str] = set()
    used_usernames: set[str] = set()

    batch_count = 0
    for i in range(config.num_regular_users):
        first_name = random.choice(FIRST_NAMES_FR)
        last_name = random.choice(LAST_NAMES_FR)

        # Generate unique email
        base_email = f"{first_name.lower()}.{last_name.lower()}@example.com"
        email = base_email
        counter = 1
        while email in used_emails:
            email = f"{first_name.lower()}.{last_name.lower()}{counter}@example.com"
            counter += 1
        used_emails.add(email)

        # Generate unique username
        base_username = f"{first_name.lower()}{last_name.lower()[:3]}"
        username = base_username
        counter = 1
        while username in used_usernames:
            username = f"{base_username}{counter}"
            counter += 1
        used_usernames.add(username)

        # Vary trust scores
        trust_score = random.randint(20, 100)
        requires_approval = trust_score < 50

        # Some users inactive
        is_active = random.random() > 0.05  # 5% inactive

        created_at = random_date_in_range()
        last_activity = random_date_after(created_at, max_days=60)
        user = User(
            email=email,
            username=username,
            display_name=f"{first_name} {last_name}",
            hashed_password=get_password_hash(regular_password),
            is_global_admin=False,
            is_active=is_active,
            created_at=created_at,
            trust_score=trust_score,
            approved_comments_count=random.randint(0, 20),
            total_flags_received=random.randint(0, 5) if trust_score < 60 else 0,
            valid_flags_received=random.randint(0, 2) if trust_score < 50 else 0,
            requires_comment_approval=requires_approval,
            # Consent fields (Law 25 compliance)
            consent_terms_accepted=True,
            consent_privacy_accepted=True,
            consent_terms_version="1.0",
            consent_privacy_version="1.0",
            consent_timestamp=created_at,
            marketing_consent=(has_marketing := random.random() > 0.7),
            marketing_consent_timestamp=created_at if has_marketing else None,
            # Retention tracking (Law 25 Phase 3)
            last_login_at=last_activity,
            last_activity_at=last_activity,
            # Privacy settings (Law 25 Phase 4) - varied for testing
            profile_visibility=random.choice(
                ["public", "public", "public", "registered", "private"]
            ),  # 60% public, 20% registered, 20% private
            show_display_name=random.random() > 0.1,  # 90% show
            show_avatar=random.random() > 0.15,  # 85% show
            show_activity=random.random() > 0.2,  # 80% show
            show_join_date=random.random() > 0.1,  # 90% show
        )
        session.add(user)
        users.append(user)
        password_map[email] = regular_password

        batch_count += 1
        if batch_count >= config.batch_size:
            session.commit()
            print(f"    Progress: {i + 1}/{config.num_regular_users} regular users")
            batch_count = 0

    session.commit()
    total_users = (
        config.num_global_admins + config.num_category_admins + config.num_regular_users
    )
    print(f"  Created {total_users} users total")
    return users


def create_admin_roles(session, users, categories):
    """Assign category admin roles."""
    cat_admin_users = users[
        config.num_global_admins : config.num_global_admins + config.num_category_admins
    ]

    roles = []
    for user in cat_admin_users:
        num_categories = random.randint(1, 2)
        assigned_cats = random.sample(categories, num_categories)
        for cat in assigned_cats:
            role = AdminRole(user_id=user.id, category_id=cat.id)
            session.add(role)
            roles.append(role)

    session.commit()
    print(f"  Created {len(roles)} admin roles")
    return roles


def create_ideas(session, users, categories, tags):
    """Create ideas with various statuses."""
    print(f"  Creating {config.num_ideas} ideas...")
    ideas = []

    regular_users = users[config.num_global_admins + config.num_category_admins :]

    batch_count = 0
    for i in range(config.num_ideas):
        user = random.choice(regular_users)
        category = random.choice(categories)
        created_at = random_date_in_range()

        # Status distribution: 60% approved, 25% pending, 15% rejected
        rand = random.random()
        if rand < 0.60:
            status = IdeaStatus.APPROVED
            validated_at = random_date_after(created_at, max_days=7)
            admin_comment = None
        elif rand < 0.85:
            status = IdeaStatus.PENDING
            validated_at = None
            admin_comment = None
        else:
            status = IdeaStatus.REJECTED
            validated_at = random_date_after(created_at, max_days=7)
            admin_comment = random.choice(
                [
                    "Cette idée ne respecte pas les critères de recevabilité.",
                    "Projet déjà en cours de réalisation par la ville.",
                    "Idée trop vague, veuillez préciser.",
                    "Ne relève pas de la compétence municipale.",
                    "Doublon d'une idée existante.",
                ]
            )

        # Instance-aware language distribution
        language = _choose_random_language()

        # Use language-specific content
        titles = IDEA_TITLES.get(language, IDEA_TITLES_EN)
        descriptions = IDEA_DESCRIPTIONS.get(language, IDEA_DESCRIPTIONS_EN)

        title_base = random.choice(titles)
        variant = i // len(titles)
        title = f"{title_base} - Variante {variant}" if variant > 0 else title_base

        description = random.choice(descriptions)

        idea = Idea(
            title=title,
            description=description,
            category_id=category.id,
            user_id=user.id,
            status=status,
            admin_comment=admin_comment,
            created_at=created_at,
            validated_at=validated_at,
            is_hidden=False,
            flag_count=0,
            language=language,
        )
        session.add(idea)
        ideas.append(idea)

        batch_count += 1
        if batch_count >= config.batch_size:
            session.commit()
            print(f"    Progress: {i + 1}/{config.num_ideas} ideas")
            batch_count = 0

    session.commit()

    # Add tags to ideas
    print("  Adding tags to ideas...")
    idea_tag_count = 0
    batch_count = 0
    for idx, idea in enumerate(ideas):
        num_tags = random.randint(*config.tags_per_idea_range)
        if num_tags > 0:
            selected_tags = random.sample(tags, min(num_tags, len(tags)))
            for tag in selected_tags:
                idea_tag = IdeaTag(
                    idea_id=idea.id, tag_id=tag.id, created_at=idea.created_at
                )
                session.add(idea_tag)
                idea_tag_count += 1

        batch_count += 1
        if batch_count >= config.batch_size:
            session.commit()
            batch_count = 0

    session.commit()
    print(f"  Created {len(ideas)} ideas with {idea_tag_count} tag associations")
    return ideas


def create_votes(session, users, ideas, qualities):
    """Create votes for ideas with optional qualities."""
    print("  Creating votes...")
    votes = []
    vote_qualities_count = 0
    regular_users = users[config.num_global_admins :]

    # Get default qualities (for random selection)
    default_qualities = [q for q in qualities if q.is_default]

    approved_ideas = [i for i in ideas if i.status == IdeaStatus.APPROVED]
    batch_count = 0
    idea_count = 0

    # Build a map of category -> available qualities
    category_qualities_map = {}
    for idea in approved_ideas:
        if idea.category_id not in category_qualities_map:
            # Get category-specific qualities
            cat_specific = (
                session.query(Quality)
                .join(CategoryQuality, Quality.id == CategoryQuality.quality_id)
                .filter(
                    CategoryQuality.category_id == idea.category_id,
                    CategoryQuality.is_enabled == True,  # noqa: E712
                )
                .all()
            )
            category_qualities_map[idea.category_id] = default_qualities + cat_specific

    for idea in approved_ideas:
        num_votes = random.randint(*config.votes_per_idea_range)
        voters = random.sample(regular_users, min(num_votes, len(regular_users)))
        available_qualities = category_qualities_map.get(
            idea.category_id, default_qualities
        )

        for voter in voters:
            if voter.id == idea.user_id:
                continue

            vote_type = VoteType.UPVOTE if random.random() < 0.7 else VoteType.DOWNVOTE

            vote = Vote(
                idea_id=idea.id,
                user_id=voter.id,
                vote_type=vote_type,
                created_at=random_date_after(idea.created_at, max_days=60),
            )
            session.add(vote)
            session.flush()  # Get vote.id for quality assignment
            votes.append(vote)

            # Add qualities for upvotes (with probability)
            if (
                vote_type == VoteType.UPVOTE
                and random.random() < config.quality_selection_probability
                and available_qualities
            ):
                num_qualities = random.randint(*config.qualities_per_vote_range)
                num_qualities = min(num_qualities, len(available_qualities))
                selected_qualities = random.sample(available_qualities, num_qualities)

                for quality in selected_qualities:
                    vote_quality = VoteQuality(
                        vote_id=vote.id,
                        quality_id=quality.id,
                        created_at=vote.created_at,
                    )
                    session.add(vote_quality)
                    vote_qualities_count += 1

            batch_count += 1

        if batch_count >= config.batch_size:
            session.commit()
            idea_count += 1
            if idea_count % 100 == 0:
                print(f"    Progress: {idea_count}/{len(approved_ideas)} ideas voted")
            batch_count = 0

    session.commit()
    print(
        f"  Created {len(votes)} votes with {vote_qualities_count} quality selections"
    )
    return votes


def create_comments(session, users, ideas):
    """Create comments for ideas."""
    print("  Creating comments...")
    comments = []
    regular_users = users[config.num_global_admins :]

    batch_count = 0
    for idea in ideas:
        if idea.status != IdeaStatus.APPROVED:
            if random.random() > 0.1:
                continue

        num_comments = random.randint(*config.comments_per_idea_range)
        commenters = random.sample(regular_users, min(num_comments, len(regular_users)))

        for commenter in commenters:
            # Instance-aware language distribution
            language = _choose_random_language()

            # Use language-specific content
            templates = COMMENT_TEMPLATES.get(language, COMMENT_TEMPLATES_EN)
            content = random.choice(templates)

            requires_approval = (
                commenter.requires_comment_approval and random.random() < 0.3
            )

            comment = Comment(
                idea_id=idea.id,
                user_id=commenter.id,
                content=content,
                is_moderated=False,
                created_at=random_date_after(idea.created_at, max_days=90),
                requires_approval=requires_approval,
                is_hidden=False,
                flag_count=0,
                language=language,
            )
            session.add(comment)
            comments.append(comment)

            batch_count += 1
            if batch_count >= config.batch_size:
                session.commit()
                print(f"    Progress: ~{len(comments)} comments created")
                batch_count = 0

    session.commit()
    print(f"  Created {len(comments)} comments")
    return comments


def create_comment_likes(session, users, comments):
    """Create likes on comments."""
    print("  Creating comment likes...")
    from repositories.db_models import CommentLike

    likes_count = 0
    regular_users = users[config.num_global_admins :]

    batch_count = 0
    for comment in comments:
        # Skip if not selected for likes
        if random.random() > config.comment_like_probability:
            continue

        # Get number of likes for this comment
        num_likes = random.randint(*config.likes_per_comment_range)
        available_likers = [u for u in regular_users if u.id != comment.user_id]
        likers = random.sample(available_likers, min(num_likes, len(available_likers)))

        for liker in likers:
            like = CommentLike(
                comment_id=comment.id,
                user_id=liker.id,
                created_at=random_date_after(comment.created_at, max_days=30),
            )
            session.add(like)
            likes_count += 1

            # Update comment's like_count
            comment.like_count = (comment.like_count or 0) + 1

        batch_count += len(likers)
        if batch_count >= config.batch_size:
            session.commit()
            print(f"    Progress: ~{likes_count} comment likes created")
            batch_count = 0

    session.commit()
    print(f"  Created {likes_count} comment likes")
    return likes_count


def create_content_flags(session, users, comments, ideas):
    """Create content flags for moderation testing."""
    print("  Creating content flags...")
    flags = []
    admin_users = users[: config.num_global_admins]
    regular_users = users[config.num_global_admins :]

    # Flag some comments
    num_to_flag = min(config.num_flagged_comments, len(comments))
    flagged_comments = random.sample(comments, num_to_flag)

    for comment in flagged_comments:
        reporter = random.choice(regular_users)
        if reporter.id == comment.user_id:
            continue

        reason = random.choice(list(FlagReason))
        status = random.choice(
            [FlagStatus.PENDING, FlagStatus.DISMISSED, FlagStatus.ACTIONED]
        )

        flag = ContentFlag(
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            reporter_id=reporter.id,
            reason=reason,
            details="Contenu signalé automatiquement pour les tests."
            if random.random() < 0.5
            else None,
            status=status,
            created_at=random_date_after(comment.created_at, max_days=30),
        )

        if status != FlagStatus.PENDING:
            flag.reviewed_at = random_date_after(flag.created_at, max_days=7)
            flag.reviewed_by = random.choice(admin_users).id
            flag.review_notes = "Examiné lors des tests."

        comment.flag_count += 1
        if comment.flag_count >= 3 or status == FlagStatus.ACTIONED:
            comment.is_hidden = True
            comment.hidden_at = flag.reviewed_at or flag.created_at

        session.add(flag)
        flags.append(flag)

    # Flag some ideas
    approved_ideas = [i for i in ideas if i.status == IdeaStatus.APPROVED]
    num_to_flag = min(config.num_flagged_ideas, len(approved_ideas))
    flagged_ideas = random.sample(approved_ideas, num_to_flag)

    for idea in flagged_ideas:
        reporter = random.choice(regular_users)
        if reporter.id == idea.user_id:
            continue

        reason = random.choice(list(FlagReason))
        status = random.choice([FlagStatus.PENDING, FlagStatus.DISMISSED])

        flag = ContentFlag(
            content_type=ContentType.IDEA,
            content_id=idea.id,
            reporter_id=reporter.id,
            reason=reason,
            status=status,
            created_at=random_date_after(idea.created_at, max_days=60),
        )

        if status != FlagStatus.PENDING:
            flag.reviewed_at = random_date_after(flag.created_at, max_days=7)
            flag.reviewed_by = random.choice(admin_users).id

        idea.flag_count += 1

        session.add(flag)
        flags.append(flag)

    session.commit()
    print(f"  Created {len(flags)} content flags")
    return flags


def create_user_penalties(session, users):
    """Create user penalties for testing."""
    print("  Creating user penalties...")
    penalties = []
    admin_users = users[: config.num_global_admins]
    regular_users = users[config.num_global_admins + config.num_category_admins :]

    num_to_penalize = min(config.num_user_penalties, len(regular_users))
    penalized_users = random.sample(regular_users, num_to_penalize)

    for user in penalized_users:
        penalty_type = random.choice(list(PenaltyType))
        status = random.choice(
            [PenaltyStatus.ACTIVE, PenaltyStatus.EXPIRED, PenaltyStatus.REVOKED]
        )
        issued_at = random_date_in_range(180)

        expires_at = None
        if penalty_type == PenaltyType.WARNING:
            expires_at = issued_at + timedelta(days=7)
        elif penalty_type == PenaltyType.TEMP_BAN_24H:
            expires_at = issued_at + timedelta(hours=24)
        elif penalty_type == PenaltyType.TEMP_BAN_7D:
            expires_at = issued_at + timedelta(days=7)
        elif penalty_type == PenaltyType.TEMP_BAN_30D:
            expires_at = issued_at + timedelta(days=30)

        penalty = UserPenalty(
            user_id=user.id,
            penalty_type=penalty_type,
            reason="Violation des règles communautaires lors des tests de données.",
            status=status,
            issued_by=random.choice(admin_users).id,
            issued_at=issued_at,
            expires_at=expires_at,
        )

        if status == PenaltyStatus.REVOKED:
            penalty.revoked_at = random_date_after(issued_at, max_days=14)
            penalty.revoked_by = random.choice(admin_users).id
            penalty.revoke_reason = "Révoqué suite à un appel accepté."

        session.add(penalty)
        penalties.append(penalty)

        user.trust_score = max(0, user.trust_score - 10)

    session.commit()
    print(f"  Created {len(penalties)} user penalties")
    return penalties


def create_appeals(session, users, penalties):
    """Create appeals for penalties."""
    appeals = []

    appealable = [
        p
        for p in penalties
        if p.status in [PenaltyStatus.ACTIVE, PenaltyStatus.EXPIRED]
    ]
    num_to_appeal = min(config.num_appeals, len(appealable))
    appealed_penalties = random.sample(appealable, num_to_appeal)

    admin_users = users[: config.num_global_admins]

    for penalty in appealed_penalties:
        status = random.choice(list(AppealStatus))

        appeal = Appeal(
            penalty_id=penalty.id,
            user_id=penalty.user_id,
            reason="Je conteste cette sanction car je n'ai pas violé les règles intentionnellement. "
            "Je m'engage à respecter les règles communautaires à l'avenir.",
            status=status,
            created_at=random_date_after(penalty.issued_at, max_days=7),
        )

        if status != AppealStatus.PENDING:
            appeal.reviewed_at = random_date_after(appeal.created_at, max_days=14)
            appeal.reviewed_by = random.choice(admin_users).id
            appeal.review_notes = (
                "Appel accepté après examen."
                if status == AppealStatus.APPROVED
                else "Appel rejeté - violation confirmée."
            )

            if status == AppealStatus.APPROVED:
                penalty.status = PenaltyStatus.APPEALED

        session.add(appeal)
        appeals.append(appeal)

    session.commit()
    print(f"  Created {len(appeals)} appeals")
    return appeals


def create_keyword_watchlist(session, users):
    """Create keyword watchlist entries."""
    admin_users = users[: config.num_global_admins]

    keywords = [
        ("spam", FlagReason.SPAM, False),
        ("publicité", FlagReason.SPAM, False),
        (r"bit\.ly", FlagReason.SPAM, True),
        ("haine", FlagReason.HATE_SPEECH, False),
        ("stupide", FlagReason.HARASSMENT, False),
    ]

    entries = []
    for keyword, reason, is_regex in keywords:
        entry = KeywordWatchlist(
            keyword=keyword,
            is_regex=is_regex,
            auto_flag_reason=reason,
            is_active=True,
            created_by=random.choice(admin_users).id,
            created_at=random_date_in_range(180),
            match_count=random.randint(0, 10),
        )
        session.add(entry)
        entries.append(entry)

    session.commit()
    print(f"  Created {len(entries)} keyword watchlist entries")
    return entries


def create_admin_notes(session, users):
    """Create admin notes on some users."""
    admin_users = users[: config.num_global_admins]
    regular_users = users[config.num_global_admins + config.num_category_admins :]

    num_to_note = min(config.num_admin_notes, len(regular_users))
    noted_users = random.sample(regular_users, num_to_note)
    notes = []

    note_templates = [
        "Utilisateur actif, contributions de qualité.",
        "À surveiller - plusieurs signalements récents.",
        "Nouveau contributeur, semble prometteur.",
        "Historique de commentaires hors sujet.",
        "Membre de longue date, très respectueux.",
    ]

    for user in noted_users:
        note = AdminNote(
            user_id=user.id,
            content=random.choice(note_templates),
            created_by=random.choice(admin_users).id,
            created_at=random_date_in_range(90),
        )
        session.add(note)
        notes.append(note)

    session.commit()
    print(f"  Created {len(notes)} admin notes")
    return notes


def create_official_users(session, users) -> int:
    """Assign official role to some regular users.

    Creates users with official status (e.g., city representatives,
    elected officials) who can have verified badges.

    Returns:
        Number of users assigned official role.
    """
    print("  Assigning official roles to users...")
    regular_users = users[config.num_global_admins + config.num_category_admins :]

    num_officials = min(config.num_official_users, len(regular_users))
    official_users = random.sample(regular_users, num_officials)

    official_titles = [
        "City Councillor",
        "Borough Mayor",
        "Urban Planner",
        "Transportation Director",
        "Environment Coordinator",
        "Community Liaison",
        "Public Works Manager",
        "Parks Director",
        "Heritage Officer",
        "Accessibility Coordinator",
    ]

    for user in official_users:
        user.is_official = True
        user.official_title = random.choice(official_titles)
        user.official_verified_at = random_date_after(user.created_at, max_days=30)

    session.commit()
    print(f"  Assigned official role to {num_officials} users")
    return num_officials


def create_login_events(session, users) -> int:
    """Create login event records for security audit testing.

    Creates a mix of successful logins, failed logins, logouts,
    and password reset requests.

    Returns:
        Number of login events created.
    """
    print(f"  Creating {config.num_login_events} login events...")
    events_count = 0
    batch_count = 0

    # Sample IPs for realistic distribution
    sample_ips = (
        ["192.168.1." + str(i) for i in range(1, 255)]
        + ["10.0.0." + str(i) for i in range(1, 100)]
        + ["172.16.0." + str(i) for i in range(1, 50)]
    )

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
        "Mozilla/5.0 (Android 14; Mobile) AppleWebKit/537.36",
    ]

    for i in range(config.num_login_events):
        # Distribution: 70% success, 20% failed, 8% logout, 2% password reset
        rand = random.random()

        if rand < 0.70:
            # Successful login
            user = random.choice(users)
            event = LoginEvent(
                user_id=user.id,
                email=user.email,
                event_type=LoginEventType.LOGIN_SUCCESS,
                ip_address=random.choice(sample_ips),
                user_agent=random.choice(user_agents),
                failure_reason=None,
                created_at=random_date_in_range(),
            )
        elif rand < 0.90:
            # Failed login
            user = random.choice(users) if random.random() > 0.3 else None
            failure_reason = random.choice(
                [
                    LoginFailureReason.INVALID_PASSWORD,
                    LoginFailureReason.USER_NOT_FOUND,
                    LoginFailureReason.ACCOUNT_INACTIVE,
                    LoginFailureReason.RATE_LIMITED,
                    LoginFailureReason.TWO_FACTOR_FAILED,
                ]
            )
            event = LoginEvent(
                user_id=user.id if user else None,
                email=user.email if user else f"unknown{i}@example.com",
                event_type=LoginEventType.LOGIN_FAILED,
                ip_address=random.choice(sample_ips),
                user_agent=random.choice(user_agents),
                failure_reason=failure_reason,
                created_at=random_date_in_range(),
            )
        elif rand < 0.98:
            # Logout
            user = random.choice(users)
            event = LoginEvent(
                user_id=user.id,
                email=user.email,
                event_type=LoginEventType.LOGOUT,
                ip_address=random.choice(sample_ips),
                user_agent=random.choice(user_agents),
                failure_reason=None,
                created_at=random_date_in_range(),
            )
        else:
            # Password reset request
            user = random.choice(users)
            event = LoginEvent(
                user_id=user.id,
                email=user.email,
                event_type=LoginEventType.PASSWORD_RESET_REQUEST,
                ip_address=random.choice(sample_ips),
                user_agent=random.choice(user_agents),
                failure_reason=None,
                created_at=random_date_in_range(),
            )

        session.add(event)
        events_count += 1
        batch_count += 1

        if batch_count >= config.batch_size:
            session.commit()
            print(
                f"    Progress: {events_count}/{config.num_login_events} login events"
            )
            batch_count = 0

    session.commit()
    print(f"  Created {events_count} login events")
    return events_count


def create_share_events(session, ideas) -> int:
    """Create share event records for analytics testing.

    Creates social media share tracking events for approved ideas.

    Returns:
        Number of share events created.
    """
    print(f"  Creating {config.num_share_events} share events...")

    approved_ideas = [i for i in ideas if i.status == IdeaStatus.APPROVED]
    if not approved_ideas:
        print("    No approved ideas to create share events for")
        return 0

    events_count = 0
    batch_count = 0
    platforms = list(SharePlatform)

    for _ in range(config.num_share_events):
        idea = random.choice(approved_ideas)
        platform = random.choice(platforms)

        event = ShareEvent(
            idea_id=idea.id,
            platform=platform,
            referrer_url=f"https://opencitivibes.local/ideas/{idea.id}"
            if random.random() > 0.3
            else None,
            created_at=random_date_after(idea.created_at, max_days=90),
        )
        session.add(event)
        events_count += 1
        batch_count += 1

        if batch_count >= config.batch_size:
            session.commit()
            print(
                f"    Progress: {events_count}/{config.num_share_events} share events"
            )
            batch_count = 0

    session.commit()
    print(f"  Created {events_count} share events")
    return events_count


def create_security_audit_logs(session, users) -> int:
    """Create security audit log entries.

    Creates various security-related audit log entries for testing
    security monitoring and compliance features.

    Returns:
        Number of audit log entries created.
    """
    print(f"  Creating {config.num_security_audit_logs} security audit logs...")

    admin_users = users[: config.num_global_admins]
    regular_users = users[config.num_global_admins :]

    events_count = 0
    batch_count = 0

    event_types = [
        ("login_failed", "warning", "authenticate"),
        ("login_success", "info", "authenticate"),
        ("data_export", "info", "export"),
        ("admin_access_pii", "warning", "view"),
        ("password_change", "info", "update"),
        ("permission_change", "warning", "update"),
        ("bulk_data_access", "warning", "view"),
        ("consent_change", "info", "update"),
    ]

    sample_ips = ["192.168.1." + str(i) for i in range(1, 100)]

    for _ in range(config.num_security_audit_logs):
        event_type, severity, action = random.choice(event_types)

        # Admin actions target other users
        if event_type in ["admin_access_pii", "permission_change", "bulk_data_access"]:
            user = random.choice(admin_users) if admin_users else random.choice(users)
            target_user = random.choice(regular_users) if regular_users else None
        else:
            user = random.choice(users)
            target_user = None

        log = SecurityAuditLog(
            event_type=event_type,
            severity=severity,
            user_id=user.id if user else None,
            target_user_id=target_user.id if target_user else None,
            ip_address=random.choice(sample_ips),
            user_agent="Mozilla/5.0 (Test Data Generator)",
            resource_type="user" if target_user else None,
            resource_id=target_user.id if target_user else None,
            action=action,
            details=None,
            success=random.random() > 0.1,  # 90% success rate
            created_at=random_date_in_range(),
        )
        session.add(log)
        events_count += 1
        batch_count += 1

        if batch_count >= config.batch_size:
            session.commit()
            print(
                f"    Progress: {events_count}/{config.num_security_audit_logs} "
                "audit logs"
            )
            batch_count = 0

    session.commit()
    print(f"  Created {events_count} security audit logs")
    return events_count


def apply_idea_edit_tracking(session, ideas) -> int:
    """Apply edit tracking fields to some approved ideas.

    Simulates the workflow where approved ideas have been edited
    and are either pending re-moderation or have been re-approved.

    Returns:
        Number of ideas with edit tracking applied.
    """
    print("  Applying edit tracking to ideas...")

    approved_ideas = [i for i in ideas if i.status == IdeaStatus.APPROVED]
    if not approved_ideas:
        print("    No approved ideas to apply edit tracking to")
        return 0

    num_to_edit = int(len(approved_ideas) * config.ideas_with_edits_probability)
    ideas_to_edit = random.sample(approved_ideas, min(num_to_edit, len(approved_ideas)))

    edited_count = 0
    for idea in ideas_to_edit:
        # Set edit count (1-3 edits)
        idea.edit_count = random.randint(1, 3)
        idea.last_edit_at = random_date_after(
            idea.validated_at or idea.created_at, max_days=60
        )

        # Some ideas are still pending re-moderation (20%)
        if random.random() < 0.2:
            idea.previous_status = IdeaStatus.APPROVED.value
            idea.status = IdeaStatus.PENDING_EDIT

        edited_count += 1

    session.commit()
    print(f"  Applied edit tracking to {edited_count} ideas")
    return edited_count


def setup_fts5(engine) -> int:
    """Set up FTS5 full-text search for ideas.

    Creates the virtual table, populates it with existing ideas, and sets up
    triggers to keep it in sync.

    Returns the number of ideas indexed.
    """
    from sqlalchemy import text

    FTS_TABLE_NAME = "ideas_fts"

    print("  Setting up FTS5 full-text search...")

    with engine.connect() as conn:
        # Check FTS5 support
        try:
            conn.execute(text("CREATE VIRTUAL TABLE temp_fts5_test USING fts5(test)"))
            conn.execute(text("DROP TABLE temp_fts5_test"))
            conn.commit()
        except Exception as e:
            print(f"    WARNING: FTS5 not supported, skipping: {e}")
            return 0

        # Create FTS5 virtual table
        conn.execute(
            text(f"""
            CREATE VIRTUAL TABLE {FTS_TABLE_NAME} USING fts5(
                idea_id UNINDEXED,
                title,
                description,
                tags,
                tokenize='porter unicode61'
            )
        """)
        )
        conn.commit()

        # Populate with existing data
        result = conn.execute(
            text("""
            SELECT
                i.id,
                i.title,
                i.description,
                COALESCE(GROUP_CONCAT(t.name, ' '), '') as tags
            FROM ideas i
            LEFT JOIN idea_tags it ON i.id = it.idea_id
            LEFT JOIN tags t ON it.tag_id = t.id
            GROUP BY i.id
        """)
        )
        ideas = result.fetchall()

        for idea in ideas:
            conn.execute(
                text(f"""
                    INSERT INTO {FTS_TABLE_NAME}(idea_id, title, description, tags)
                    VALUES (:idea_id, :title, :description, :tags)
                """),  # nosec B608 - FTS_TABLE_NAME is hardcoded constant
                {
                    "idea_id": idea[0],
                    "title": idea[1] or "",
                    "description": idea[2] or "",
                    "tags": idea[3] or "",
                },
            )
        conn.commit()

        # Create sync triggers
        # nosec B608 - FTS_TABLE_NAME is hardcoded constant "ideas_fts", not user input
        triggers = [
            f"""
            CREATE TRIGGER ideas_fts_insert AFTER INSERT ON ideas
            BEGIN
                INSERT INTO {FTS_TABLE_NAME}(idea_id, title, description, tags)
                VALUES (NEW.id, NEW.title, COALESCE(NEW.description, ''),
                    (SELECT COALESCE(GROUP_CONCAT(t.name, ' '), '')
                     FROM tags t JOIN idea_tags it ON t.id = it.tag_id
                     WHERE it.idea_id = NEW.id));
            END
            """,  # nosec B608
            f"""
            CREATE TRIGGER ideas_fts_update AFTER UPDATE ON ideas
            BEGIN
                UPDATE {FTS_TABLE_NAME} SET title = NEW.title,
                    description = COALESCE(NEW.description, '')
                WHERE idea_id = NEW.id;
            END
            """,  # nosec B608
            f"""
            CREATE TRIGGER ideas_fts_delete AFTER DELETE ON ideas
            BEGIN
                DELETE FROM {FTS_TABLE_NAME} WHERE idea_id = OLD.id;
            END
            """,  # nosec B608
            f"""
            CREATE TRIGGER idea_tags_insert_fts AFTER INSERT ON idea_tags
            BEGIN
                UPDATE {FTS_TABLE_NAME} SET
                    tags = (SELECT COALESCE(GROUP_CONCAT(t.name, ' '), '')
                            FROM tags t JOIN idea_tags it ON t.id = it.tag_id
                            WHERE it.idea_id = NEW.idea_id)
                WHERE idea_id = NEW.idea_id;
            END
            """,  # nosec B608
            f"""
            CREATE TRIGGER idea_tags_delete_fts AFTER DELETE ON idea_tags
            BEGIN
                UPDATE {FTS_TABLE_NAME} SET
                    tags = (SELECT COALESCE(GROUP_CONCAT(t.name, ' '), '')
                            FROM tags t JOIN idea_tags it ON t.id = it.tag_id
                            WHERE it.idea_id = OLD.idea_id)
                WHERE idea_id = OLD.idea_id;
            END
            """,  # nosec B608
        ]
        for trigger_sql in triggers:
            conn.execute(text(trigger_sql))
        conn.commit()

        print(f"  Created FTS5 table and indexed {len(ideas)} ideas")
        return len(ideas)


def generate_markdown_report(
    password_map: dict, output_path: Path, actual_counts: dict, size: str
):
    """Generate markdown documentation with test users."""
    content = f"""# Test Data - User Credentials

This file contains the credentials for test users in the development database.

**Dataset Size:** {config.name} - {config.description}

**Database file:** `backend/data/opencitivibes_test_{size}.db`

> **WARNING:** These credentials are for development/testing only. Never use in production!

## Quick Start

```bash
# Start the backend with this test database
cd backend
DATABASE_URL=sqlite:///./data/opencitivibes_test_{size}.db uv run uvicorn main:app --reload
```

## Test Users

### Global Administrators

| Email | Password | Role |
|-------|----------|------|
"""

    for i in range(config.num_global_admins):
        email = _get_test_admin_email(i + 1)
        password = password_map.get(email, "Admin123!")
        content += f"| `{email}` | `{password}` | Global Admin |\n"

    content += """
### Category Administrators

| Email | Password | Role |
|-------|----------|------|
"""

    for i in range(min(10, config.num_category_admins)):  # Show first 10
        email = _get_test_category_admin_email(i + 1)
        password = password_map.get(email, "CatAdmin123!")
        content += f"| `{email}` | `{password}` | Category Admin |\n"

    if config.num_category_admins > 10:
        content += (
            f"| ... | `CatAdmin123!` | +{config.num_category_admins - 10} more |\n"
        )

    content += f"""
### Regular Users

All {config.num_regular_users:,} regular users use the same password: `User123!`

Sample users:

| Email Pattern | Password |
|---------------|----------|
| `firstname.lastname@example.com` | `User123!` |

## Data Statistics

| Entity | Count |
|--------|-------|
| Users (Total) | {actual_counts["users"]:,} |
| - Global Admins | {config.num_global_admins:,} |
| - Category Admins | {config.num_category_admins:,} |
| - Regular Users | {config.num_regular_users:,} |
| - Official Users | {actual_counts["official_users"]:,} |
| Ideas | {actual_counts["ideas"]:,} |
| - Ideas with edits | {actual_counts["edited_ideas"]:,} |
| Tags | {config.num_tags:,} |
| Tag Associations | {actual_counts["idea_tags"]:,} |
| Votes | {actual_counts["votes"]:,} |
| Comments | {actual_counts["comments"]:,} |
| Comment Likes | {actual_counts["comment_likes"]:,} |
| Content Flags | {actual_counts["flags"]:,} |
| User Penalties | {actual_counts["penalties"]:,} |
| Appeals | {actual_counts["appeals"]:,} |
| **Security & Analytics** | |
| Login Events | {actual_counts["login_events"]:,} |
| Share Events | {actual_counts["share_events"]:,} |
| Security Audit Logs | {actual_counts["security_audit_logs"]:,} |
| **Law 25 Compliance** | |
| Policy Versions | {actual_counts["policy_versions"]:,} |
| Consent Logs | {actual_counts["consent_logs"]:,} |

## Date Distribution

Data is spread over the last {config.date_range_days:,} days ({config.date_range_days // 365} year(s)) to provide realistic analytics charts.

## Categories

1. Transport & Mobility / Transport et Mobilité
2. Environment & Green Spaces / Environnement et Espaces verts
3. Safety & Security / Sécurité et Sûreté
4. Culture & Community / Culture et Communauté
5. Urban Development / Développement urbain
6. Economy & Business / Économie et Commerce
7. Technology & Innovation / Technologie et Innovation
8. Health & Wellness / Santé et Bien-être

## Testing Scenarios

### Performance Testing
- Pagination: Test with large offsets (skip={config.num_ideas // 2}, limit=20)
- Search: Test full-text search across {config.num_ideas:,} ideas
- Leaderboard: Test sorting with {actual_counts["votes"]:,} votes

### Moderation Testing
- Review flagged content queue ({config.num_flagged_comments:,} flagged comments)
- Test penalty workflow with {config.num_user_penalties:,} existing penalties
- Review {config.num_appeals:,} pending/resolved appeals

### Analytics Testing
- Test trend charts with {config.date_range_days // 365}-year date distribution
- Test category analytics with varied data per category
- Test top contributors rankings

### Law 25 Compliance Testing
- Verify consent logs are created on registration
- Test reconsent flow with policy version updates
- Test marketing consent opt-in/opt-out audit trail
- Verify privacy settings (profile visibility) filtering
- Test data export endpoint with complete user data
- Verify marketing_consent_timestamp is set correctly

### Security Audit Testing
- Test login event tracking with {config.num_login_events:,} login events
- Review security audit logs ({actual_counts["security_audit_logs"]:,} entries)
- Test failed login analysis and suspicious activity detection
- Verify official user badge display ({actual_counts["official_users"]:,} officials)

### Social Sharing Analytics
- Test share event tracking ({actual_counts["share_events"]:,} share events)
- Verify platform distribution (Twitter, Facebook, LinkedIn, WhatsApp, Copy Link)
- Test share analytics dashboard with realistic data

### Idea Edit Workflow Testing
- Test edit-approved-ideas flow with {actual_counts["edited_ideas"]:,} edited ideas
- Verify PENDING_EDIT status transition
- Test re-moderation workflow for edited ideas

## Dataset Sizes

| Size | Users | Ideas | Est. Generation Time |
|------|-------|-------|---------------------|
| SMALL | 108 | 500 | ~10 seconds |
| MEDIUM | 1,015 | 5,000 | ~2 minutes |
| LARGE | 10,030 | 50,000 | ~20 minutes |

## Available Test Databases

```bash
# Small dataset
DATABASE_URL=sqlite:///./data/opencitivibes_test_small.db uv run uvicorn main:app --reload

# Medium dataset
DATABASE_URL=sqlite:///./data/opencitivibes_test_medium.db uv run uvicorn main:app --reload

# Large dataset
DATABASE_URL=sqlite:///./data/opencitivibes_test_large.db uv run uvicorn main:app --reload

# Production database (default)
uv run uvicorn main:app --reload
```

## Regenerating Data

```bash
cd backend

# Small (default)
uv run python scripts/generate_test_data.py

# Medium
uv run python scripts/generate_test_data.py --size medium

# Large
uv run python scripts/generate_test_data.py --size large
```
"""

    output_path.write_text(content)
    print(f"\nMarkdown report saved to: {output_path}")


def main():
    """Main entry point."""
    global config

    parser = argparse.ArgumentParser(
        description="Generate test data for OpenCitiVibes platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Dataset sizes:
  small   Development/testing - ~100 users, ~500 ideas (default)
  medium  Small-scale deployment - ~1,000 users, ~5,000 ideas
  large   City-scale stress test - ~10,000 users, ~50,000 ideas

Examples:
  uv run python scripts/generate_test_data.py
  uv run python scripts/generate_test_data.py --size medium
  uv run python scripts/generate_test_data.py --size large
        """,
    )
    parser.add_argument(
        "--size",
        choices=["small", "medium", "large"],
        default="small",
        help="Dataset size (default: small)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Custom output database path (default: data/opencitivibes_test_{size}.db)",
    )
    args = parser.parse_args()

    global TEST_DB_PATH
    config = DATASET_CONFIGS[args.size]
    if args.output:
        TEST_DB_PATH = Path(args.output)
        if not TEST_DB_PATH.is_absolute():
            TEST_DB_PATH = backend_dir / TEST_DB_PATH
    else:
        TEST_DB_PATH = get_db_path(args.size)

    print("=" * 70)
    print("OpenCitiVibes - Test Data Generator")
    print("=" * 70)
    print(f"\nDataset: {config.name}")
    print(f"Description: {config.description}")
    print(f"Database: {TEST_DB_PATH.name}")
    print("\nTargets:")
    print(
        f"  - Users: {config.num_regular_users + config.num_category_admins + config.num_global_admins:,}"
    )
    print(f"  - Ideas: {config.num_ideas:,}")
    print(f"  - Tags: {config.num_tags:,}")
    print(f"  - Date range: {config.date_range_days} days")

    # Remove existing test database
    if TEST_DB_PATH.exists():
        print(f"\nRemoving existing test database: {TEST_DB_PATH}")
        TEST_DB_PATH.unlink()

    # Create engine and session
    engine = create_engine(f"sqlite:///{TEST_DB_PATH}", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    password_map: dict[str, str] = {}
    actual_counts: dict[str, int] = {}

    try:
        print("\nGenerating test data...\n")

        print("1. Creating policy versions (Law 25)...")
        policy_versions = create_policy_versions(session)

        print("\n2. Creating categories...")
        categories = create_categories(session)

        print("\n3. Creating qualities...")
        qualities = create_qualities(session, categories)

        print("\n4. Creating tags...")
        tags = create_tags(session)

        print("\n5. Creating users...")
        users = create_users(session, password_map)
        create_admin_roles(session, users, categories)

        print("\n6. Creating consent logs (Law 25)...")
        consent_logs = create_consent_logs(session, users)

        print("\n7. Creating ideas...")
        ideas = create_ideas(session, users, categories, tags)

        print("\n8. Creating votes...")
        votes = create_votes(session, users, ideas, qualities)

        print("\n9. Creating comments...")
        comments = create_comments(session, users, ideas)

        print("\n10. Creating comment likes...")
        comment_likes_count = create_comment_likes(session, users, comments)

        print("\n11. Creating moderation data...")
        flags = create_content_flags(session, users, comments, ideas)
        penalties = create_user_penalties(session, users)
        appeals = create_appeals(session, users, penalties)
        create_keyword_watchlist(session, users)
        create_admin_notes(session, users)

        print("\n12. Assigning official roles...")
        official_count = create_official_users(session, users)

        print("\n13. Creating login events (Security Audit)...")
        login_events_count = create_login_events(session, users)

        print("\n14. Creating share events (Analytics)...")
        share_events_count = create_share_events(session, ideas)

        print("\n15. Creating security audit logs...")
        security_logs_count = create_security_audit_logs(session, users)

        print("\n16. Applying idea edit tracking...")
        edited_ideas_count = apply_idea_edit_tracking(session, ideas)

        # Set up FTS5 full-text search
        print("\n17. Setting up FTS5...")
        setup_fts5(engine)

        # Collect actual counts
        actual_counts = {
            "users": len(users),
            "ideas": len(ideas),
            "idea_tags": session.query(IdeaTag).count(),
            "votes": len(votes),
            "comments": len(comments),
            "comment_likes": comment_likes_count,
            "flags": len(flags),
            "penalties": len(penalties),
            "appeals": len(appeals),
            "policy_versions": len(policy_versions),
            "consent_logs": len(consent_logs),
            "official_users": official_count,
            "login_events": login_events_count,
            "share_events": share_events_count,
            "security_audit_logs": security_logs_count,
            "edited_ideas": edited_ideas_count,
        }

        print("\n" + "=" * 70)
        print("Test database created successfully!")
        print(f"Location: {TEST_DB_PATH}")
        print(f"Size: {TEST_DB_PATH.stat().st_size / (1024 * 1024):.1f} MB")
        print("=" * 70)

        # Generate markdown documentation
        docs_dir = backend_dir.parent / "claude-docs" / "testing"
        docs_dir.mkdir(parents=True, exist_ok=True)
        generate_markdown_report(
            password_map, docs_dir / "TEST_USERS.md", actual_counts, args.size
        )

    except Exception as e:
        session.rollback()
        print(f"\nError: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
