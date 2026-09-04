import unittest
from tests.skill_vfy.case_module import install_cases


class VfyScopeSubjectCases(unittest.TestCase):
    pass


install_cases(VfyScopeSubjectCases, 10, 19)
