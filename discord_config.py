guild = 867751492408573982
staffIndex = [867751492417355836, 867751492417355835]
admin = 126473945787531264


class Roles:
    user = 867751492408573983
    observer = 867751492417355827
    student = 867751492417355828
    ta = 867751492417355829
    leadTa = 867751492417355830
    projectTa = 867751492417355831
    consultant = 868124117067509770
    mentor = 867751492417355832
    speaker = 867751492417355833
    sponsor = 867751492417355834
    support = 867751492417355835

    ROLES_DICT = {
        "observer": [user, observer],
        "student": [user, student],
        "TA": [user, student, ta],
        "leadTA": [user, student, ta, leadTa],
        "projectTA": [user, student, ta, projectTa],
        "consultant": [user, student, consultant],
        "mentor": [user, student, mentor],
        "speaker": [user, student, speaker],
        "sponsor": [user, student, sponsor],
        "support": [user, student, support],
    }

    @staticmethod
    def get_roles(role):
        return Roles.ROLES_DICT.get(role)
