import discord


def _role(guild, name):
    return discord.utils.get(guild.roles, name=name)


def describe_members(guild, members) -> str:
    """One line per non-staff member, labelled (Lead TA) / (TA) where applicable."""
    staff = [_role(guild, "Organizers"), _role(guild, "Staffers"), _role(guild, "Robots")]
    lead_ta, ta = _role(guild, "Lead TA"), _role(guild, "Teaching Assistant")
    lines = ''
    for member in members:
        if not isinstance(member, discord.Member) or any(r in member.roles for r in staff):
            continue
        if lead_ta in member.roles:
            lines += f'{member.name} **(Lead TA)**\n'
        elif ta in member.roles:
            lines += f'{member.name} **(TA)**\n'
        else:
            lines += f'{member.name}\n'
    return lines
