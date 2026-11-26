import os

from . import interact

ADMIN_ROLE = "Organizers"


def admin_ids() -> set[int]:
    """User IDs from the ADMIN_USER_IDS env var (comma-separated); invalid entries are ignored."""
    ids = set()
    for part in os.getenv("ADMIN_USER_IDS", "").split(","):
        part = part.strip()
        if part.isdecimal():
            ids.add(int(part))
    return ids


def is_super_admin(member) -> bool:
    return member.id in admin_ids()


def is_admin(member) -> bool:
    return is_super_admin(member) or any(r.name == ADMIN_ROLE for r in getattr(member, "roles", []))


async def require_admin(interaction, *, super_admin: bool = False) -> bool:
    """Return True if the invoker may proceed; otherwise send an ephemeral denial and return False."""
    check = is_super_admin if super_admin else is_admin
    if check(interaction.user):
        return True
    text = ("Only authorised administrators can do this." if super_admin
            else "Only Organizers can use this.")
    await interaction.response.send_message(
        embed=interact.send_embed('custom', 'Administrative Notice', text), ephemeral=True)
    return False
