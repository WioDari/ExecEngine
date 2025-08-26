#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from datetime import datetime
from app.models.orm_models import ApiTokenModel

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("cleanup_api_tokens.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def clear_expired_tokens(db: Session):
    try:
        now = datetime.utcnow()
        result = db.execute(
            delete(APIToken).where(APIToken.expires_at < now)
        )
        deleted_count = result.rowcount
        db.commit()
        logger.info(f"Successfully deleted {deleted_count} expired tokens.")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error while deleting tokens: {e}")
    except Exception as e:
        logger.error(f"Something went wrong: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    clear_expired_tokens()