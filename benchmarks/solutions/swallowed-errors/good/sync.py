import logging

logger = logging.getLogger(__name__)


def sync_contacts(contacts, push):
    """Push every contact to the CRM. Returns the list of contact ids that failed."""
    failed = []
    for c in contacts:
        try:
            push(c)
        except Exception:  # one bad contact must not stop the sync; KeyboardInterrupt still does
            logger.exception("failed to push contact %s", c.get("id"))
            failed.append(c.get("id"))
    return failed
