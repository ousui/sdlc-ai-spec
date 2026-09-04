import unittest
from tests.skill_vfy.case_module import install_cases


class VfyMethodCases(unittest.TestCase):
    pass


install_cases(VfyMethodCases, 26, 40)
