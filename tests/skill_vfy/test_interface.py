import unittest
from tests.skill_vfy.case_module import install_cases


class VfyInterfaceCases(unittest.TestCase):
    pass


install_cases(VfyInterfaceCases, 1, 9)
