import os
import json
import threading
from typing import Dict, List, Optional
import logging
from datetime import datetime, timedelta, timezone

STATUS_FILE = 'ipo_status.json'
IGNORE_FILE = 'ipo_ignore.json'
LOCK = threading.Lock()
logger = logging.getLogger(__name__)

IGNORE_DURATION_HOURS = 24  # How long to ignore an IPO after skip/ignore command

def _read_status() -> Dict:
    if not os.path.exists(STATUS_FILE):
        return {}
    try:
        with open(STATUS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read IPO status file: {e}")
        return {}

def _write_status(status: Dict):
    try:
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(status, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to write IPO status file: {e}")

def _read_ignore() -> Dict:
    if not os.path.exists(IGNORE_FILE):
        return {}
    try:
        with open(IGNORE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read IPO ignore file: {e}")
        return {}

def _write_ignore(ignore: Dict):
    try:
        with open(IGNORE_FILE, 'w', encoding='utf-8') as f:
            json.dump(ignore, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to write IPO ignore file: {e}")

def is_ipo_filled_for_user(ipo_id: str, user_alias: str) -> bool:
    with LOCK:
        status = _read_status()
        return status.get(ipo_id, {}).get(user_alias, False)

def mark_ipo_filled_for_user(ipo_id: str, user_alias: str):
    with LOCK:
        status = _read_status()
        if ipo_id not in status:
            status[ipo_id] = {}
        status[ipo_id][user_alias] = True
        _write_status(status)

def get_unfilled_ipos_for_users(ipo_list: List[Dict], user_aliases: List[str], ignore_expired=True) -> List[Dict]:
    """
    Returns IPOs that are not filled for at least one user and not ignored.
    Each IPO dict will have an extra key 'unfilled_users' listing those users.
    """
    with LOCK:
        status = _read_status()
        ignore = _read_ignore()
        now = datetime.now(timezone.utc)
        unfilled = []
        for ipo in ipo_list:
            ipo_id = str(ipo['id'])
            # Ignore logic
            if ignore_entry:=ignore.get(ipo_id):
                ignore_until = datetime.fromisoformat(ignore_entry['until'])
                if now < ignore_until:
                    continue  # Still ignored
                elif ignore_expired:
                    del ignore[ipo_id]  # Clean up expired ignore
                    _write_ignore(ignore)
            if unfilled_users:= [alias for alias in user_aliases if not status.get(ipo_id, {}).get(alias, False)]:
                ipo = dict(ipo)  # copy
                ipo['unfilled_users'] = unfilled_users
                unfilled.append(ipo)
        return unfilled

def mark_ipo_filled_for_users(ipo_id: str, user_aliases: List[str]):
    with LOCK:
        status = _read_status()
        if ipo_id not in status:
            status[ipo_id] = {}
        for alias in user_aliases:
            status[ipo_id][alias] = True
        _write_status(status)

def ignore_ipo(ipo_id: str, hours: int = IGNORE_DURATION_HOURS):
    with LOCK:
        ignore = _read_ignore()
        until = (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
        ignore[ipo_id] = {'until': until}
        _write_ignore(ignore)

def clear_expired_ignores():
    with LOCK:
        ignore = _read_ignore()
        now = datetime.now(timezone.utc)
        changed = False
        for ipo_id in list(ignore.keys()):
            until = datetime.fromisoformat(ignore[ipo_id]['until'])
            if now > until:
                del ignore[ipo_id]
                changed = True
        if changed:
            _write_ignore(ignore)

def needs_status_sync(eligible_ipos: List[Dict]) -> bool:
    """
    Check if any eligible IPOs exist in status or ignore files, indicating sync might be needed.
    Returns True if sync should be performed, False otherwise.
    """
    with LOCK:
        status = _read_status()
        ignore = _read_ignore()
        
        for ipo in eligible_ipos:
            ipo_id = str(ipo['id'])
            # If IPO exists in status or ignore files, sync is not needed
            if ipo_id in status or ipo_id in ignore:
                return False
        return True

def get_ipo_id_by_name(ipo_name: str, api_ipo_list: List[Dict]) -> Optional[str]:
    """
    Find IPO ID by name from API list.
    Returns the IPO ID if found, None otherwise.
    """
    ipo_name_lower = ipo_name.lower().strip()
    for ipo in api_ipo_list:
        if ipo['company_name'].lower().strip() == ipo_name_lower:
            return str(ipo['id'])
    return None

def sync_status_with_open_issues(open_issues: List[Dict], user_aliases: List[str], api_ipo_list: List[Dict]):
    """
    For each user and IPO, if the IPO is not available to apply (not in open_issues for that user), mark as filled.
    open_issues: list of IPO dicts as returned by Meroshare for the current user.
    api_ipo_list: list of IPO dicts from API (with IDs) to map names to IDs.
    """
    with LOCK:
        status = _read_status()
        # Get available IPO names from Meroshare
        available_names = {issue['Issue Name'].strip() for issue in open_issues}
        
        # For each IPO in status, check if it's still available
        for ipo_id in list(status.keys()):
            # Find IPO name by ID from API list
            ipo_name = None
            for api_ipo in api_ipo_list:
                if str(api_ipo['id']) == ipo_id:
                    ipo_name = api_ipo['company_name'].strip()
                    break
            
            if ipo_name and ipo_name not in available_names:
                # IPO is no longer available, mark as filled for all users
                for alias in user_aliases:
                    status[ipo_id][alias] = True
                logger.info(f"Marked IPO {ipo_name} (ID: {ipo_id}) as filled for all users (no longer available)")
        
        _write_status(status)

def get_ipo_name_by_id(ipo_id: str, api_ipo_list: List[Dict]) -> Optional[str]:
    """
    Find IPO name by ID from API list.
    Returns the IPO name if found, None otherwise.
    """
    for ipo in api_ipo_list:
        if str(ipo['id']) == ipo_id:
            return ipo['company_name'].strip()
    return None 