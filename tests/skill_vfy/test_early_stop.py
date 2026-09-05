import unittest
from tests.skill_vfy.case_module import install_cases


class VfyEarlyStopCases(unittest.TestCase):
    pass


install_cases(VfyEarlyStopCases, 65, 70)
