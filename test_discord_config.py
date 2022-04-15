guild = 959875396126511116
staffIndex = []
staffId = 123
admin = 959807738756608082


class Roles:
    observer = 964185043327156325

    ROLES_DICT = {"observer": [observer], "student": [observer]}

    TIMEZONE_ROLES = {"A": observer, "B": observer}

    @staticmethod
    def get_roles(role):
        return Roles.ROLES_DICT.get(role)

    @staticmethod
    def get_timezone_role(timezone):
        return Roles.TIMEZONE_ROLES.get(timezone)
