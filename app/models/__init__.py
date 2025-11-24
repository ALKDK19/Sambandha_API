"""Import model modules to ensure SQLAlchemy mappers are registered when doing `import app.models`.
Importing the modules (not specific names) avoids ImportError when names vary and ensures relationships
that reference other classes by string names (e.g., "Profile") can be resolved.
"""

# 2. Independent models
from . import admin
# Import in dependency order to avoid circular imports
# 1. Base first
from . import base
from . import content
from . import engagement
# 6. Interactions (depends on User, Profile)
from . import interaction
# 5. Preference (depends on User)
from . import preference
# 4. Profile (depends on User)
from . import profile
# 7. Recommender (depends on User)
from . import recommender
# 8. Security (depends on User)
from . import security
# 9. Shortlist (depends on User)
from . import shortlist
# 3. User and related
from . import user

# noinspection PyUnresolvedReferences - Suppress IDE warnings about unused imports
__all__ = [
    'base',
    'admin',
    'content',
    'user',
    'profile',
    'preference',
    'interaction',
    'engagement',
    'recommender',
    'security',
    'shortlist',
]
