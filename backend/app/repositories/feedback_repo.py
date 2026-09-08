from app.models.feedback import Feedback
from app.repositories.base import BaseRepository


class FeedbackRepository(BaseRepository[Feedback]):
    """Product feedback. Create-only from the client; read is admin/reporting."""
