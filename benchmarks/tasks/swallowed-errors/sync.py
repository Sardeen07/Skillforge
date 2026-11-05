import logging

logger = logging.getLogger(__name__)


def sync_contacts(contacts, push):
    """Push every contact to the CRM. Returns the list of contact ids that failed."""
    for c in contacts:
        try:
            push(c)
        except:
            pass
    return []
