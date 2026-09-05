import unittest
from tests.skill_vfy.case_module import install_cases


class VfyExecutorEvidenceCases(unittest.TestCase):
    pass


install_cases(VfyExecutorEvidenceCases, 41, 51)
