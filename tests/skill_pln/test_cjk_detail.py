"""Regress real non-space-delimited PLN input without weakening other gates."""
from .support import PlnFixture


class PlnLocalizedDetailTests(PlnFixture):
    def test_complete_chinese_criteria_do_not_require_inserted_spaces(self):
        plan = self.plan()
        for item in plan['work_items']:
            item['completion_criteria'] = '四个有效模块使用JDK26完成编译打包并保留原有公开接口'
            item['expected_evidence'] = '可复现的构建命令、完整日志与字节码版本检查'
        result = self.execute_pln(plan=plan, final=False)
        self.assertNotIn('PLN-G-003', result['gate']['failed_checks'])
        self.assertFalse(result['ok'])  # Content detail does not replace confirmation.
        self.assertEqual('pending', result['gate']['result'])

    def test_complete_japanese_detail_is_supported(self):
        plan = self.plan()
        plan['work_items'][0]['completion_criteria'] = '全ての対象モジュールをコンパイルし公開インターフェースを保持する'
        plan['work_items'][0]['expected_evidence'] = '実行したコマンドと全ての検証結果を記録する'
        result = self.execute_pln(plan=plan, final=False)
        self.assertNotIn('PLN-G-003', result['gate']['failed_checks'])

    def test_generic_chinese_completion_remains_rejected(self):
        for value in ('完成', '已完成'):
            with self.subTest(value=value):
                plan = self.plan()
                plan['work_items'][0]['completion_criteria'] = value
                result = self.execute_pln(plan=plan, final=False)
                self.assertIn('PLN-G-003', result['gate']['failed_checks'])

    def test_generic_chinese_evidence_remains_rejected(self):
        for value in ('证据', '结果'):
            with self.subTest(value=value):
                plan = self.plan()
                plan['work_items'][0]['expected_evidence'] = value
                result = self.execute_pln(plan=plan, final=False)
                self.assertIn('PLN-G-003', result['gate']['failed_checks'])

    def test_short_or_punctuation_only_text_is_not_detail(self):
        for value in ('合格', '完成测试', '。。。！！！', '✓✓✓✓✓✓✓✓✓✓✓✓', '1234567890123456'):
            with self.subTest(value=value):
                plan = self.plan()
                plan['work_items'][0]['completion_criteria'] = value
                result = self.execute_pln(plan=plan, final=False)
                self.assertIn('PLN-G-003', result['gate']['failed_checks'])

    def test_existing_english_minimum_is_unchanged(self):
        plan = self.plan()
        plan['work_items'][0]['completion_criteria'] = 'Tests pass'
        result = self.execute_pln(plan=plan, final=False)
        self.assertIn('PLN-G-003', result['gate']['failed_checks'])

    def test_localized_detail_cannot_override_scope(self):
        plan = self.plan()
        plan['work_items'][0]['completion_criteria'] = '四个有效模块使用JDK26完成编译打包并保留原有公开接口'
        plan['work_items'][0]['expected_evidence'] = '可复现的构建命令、完整日志与字节码版本检查'
        plan['work_items'][0]['source_references'] = [self.dsn_reference + '#CHG-999']
        result = self.execute_pln(plan=plan, final=False)
        self.assertIn('PLN-G-006', result['gate']['failed_checks'])
