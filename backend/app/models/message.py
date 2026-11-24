from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from ..database import Base
import json


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)

    message_metadata = Column("metadata", Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    def to_dict(self):
        data = {
            "role": self.role,
            "content": self.content,
        }

        if self.role == "assistant" and self.message_metadata:
            try:
                data["metadata"] = json.loads(self.message_metadata)
            except Exception:
                data["metadata"] = self.message_metadata

        return data