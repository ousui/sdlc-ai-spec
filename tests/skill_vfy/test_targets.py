import unittest
from tests.skill_vfy.case_module import install_cases


class VfyTargetCases(unittest.TestCase):
    pass


install_cases(VfyTargetCases, 20, 25)
