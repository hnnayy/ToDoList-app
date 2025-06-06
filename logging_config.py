import logging
import logging.handlers
import os
from datetime import datetime

def setup_logging():
    """Setup application logging"""
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level),
        format=log_format,
        handlers=[
            logging.StreamHandler(),  # Console output
            logging.handlers.RotatingFileHandler(
                'logs/app.log',
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            ),
            logging.handlers.RotatingFileHandler(
                'logs/security.log',
                maxBytes=5*1024*1024,   # 5MB
                backupCount=3
            )
        ]
    )
    
    return logging.getLogger(__name__)

# Security event logging
def log_security_event(event_type, details, user_id=None):
    """Log security events"""
    security_logger = logging.getLogger('security')
    security_logger.info(f"SECURITY_EVENT: {event_type} - {details} - User: {user_id}")
