# RLS Critical Case Matrix — 87/87

每行对应一个唯一可执行主测试，且包含 Spec、Design、正负向、读写/效果、
测试层、模块、测试文件、测试方法、VFY/Fake/真实项目/授权依赖、Gate 与 Expected。
Coverage Guard 拒绝缺失、重复、乱序、不存在、skipped、expectedFailure 或同一主测试复用。

图例：`+/-`=positive/negative；`R/M/E`=read-only/mutation/effect；
`U/I/X`=unit/integration/external；`Y/N`=yes/no；`P`=fixture authority
`PROVISIONAL`；`TC`=`tests/skill_rls/test_critical_cases.py`；`query_rls.py*` 为
VFY 合入后共享集成。

|Case ID|Spec Clause|Design Clause|±|Class|Level|Module|Test file|Primary test|VFY fixture|Final VFY|Fake target|Real project|Effect auth|Blocks Gate|Fixture authority|Expected|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|RLS-E001|S:Interface|D:Interface|+|M|U|runtime.py|TC|test_rls_e001_interface|Y|Y|N|N|N|N|P|auto create|
|RLS-E002|S:Interface|D:Interface|-|M|U|runtime.py|TC|test_rls_e002_interface|Y|Y|N|N|N|Y|P|用户选择|
|RLS-E003|S:Interface|D:Interface|+|M|U|runtime.py|TC|test_rls_e003_interface|Y|Y|N|N|N|N|P|只创建 open Contract，无 Target effect|
|RLS-E004|S:Interface|D:Interface|-|E|U|runtime.py|TC|test_rls_e004_interface|Y|Y|Y|N|Y|Y|P|需要准确授权|
|RLS-E005|S:Interface|D:Interface|+|E|U|runtime.py|TC|test_rls_e005_interface|Y|Y|Y|N|N|N|P|执行/记录目标侧确认|
|RLS-E006|S:Interface|D:Interface|+|M|U|runtime.py|TC|test_rls_e006_interface|Y|Y|N|N|N|N|P|状态机准确|
|RLS-E007|S:Interface|D:Interface|+|R|U|runtime.py|TC|test_rls_e007_interface|Y|Y|N|N|N|N|P|零扫描、零写入/效果|
|RLS-E008|S:Interface|D:Interface|-|M|U|runtime.py|TC|test_rls_e008_interface|Y|Y|N|N|N|Y|P|stable error|
|RLS-E009|S:Interface|D:Interface|+|M|U|runtime.py|TC|test_rls_e009_interface|Y|Y|N|N|N|N|P|去重 + warning|
|RLS-E010|S:Applicability|D:Applicability|+|M|U|rls_vfy_adapter.py|TC|test_rls_e010_applicability|Y|Y|N|N|N|N|P|创建 RLS Artifact|
|RLS-E011|S:Applicability|D:Applicability|+|M|U|rls_vfy_adapter.py|TC|test_rls_e011_applicability|Y|Y|N|N|N|N|P|completed + artifact=null|
|RLS-E012|S:Applicability|D:Applicability|+|M|U|rls_vfy_adapter.py|TC|test_rls_e012_applicability|Y|Y|N|N|N|N|P|无 Artifact，保留 Exception Evidence|
|RLS-E013|S:Applicability|D:Applicability|-|M|U|rls_vfy_adapter.py|TC|test_rls_e013_applicability|Y|Y|N|N|N|Y|P|action_required|
|RLS-E014|S:Applicability|D:Applicability|-|M|U|rls_vfy_adapter.py|TC|test_rls_e014_applicability|Y|Y|N|N|N|Y|P|拒绝|
|RLS-E015|S:Applicability|D:Applicability|-|M|U|rls_vfy_adapter.py|TC|test_rls_e015_applicability|Y|Y|N|N|N|Y|P|阻止|
|RLS-E016|S:Applicability|D:Applicability|-|M|U|rls_vfy_adapter.py|TC|test_rls_e016_applicability|Y|Y|N|N|N|Y|P|阻止 RLS|
|RLS-E017|S:Applicability|D:Applicability|-|M|U|rls_vfy_adapter.py|TC|test_rls_e017_applicability|Y|Y|N|N|N|Y|P|阻止|
|RLS-E018|S:Applicability|D:Applicability|-|M|U|rls_vfy_adapter.py|TC|test_rls_e018_applicability|Y|Y|N|N|N|Y|P|阻止|
|RLS-E019|S:Applicability|D:Applicability|+|M|U|rls_vfy_adapter.py|TC|test_rls_e019_applicability|Y|Y|N|N|N|N|P|可继续，原 VFY 结论不改写|
|RLS-E020|S:Applicability|D:Applicability|-|M|U|rls_vfy_adapter.py|TC|test_rls_e020_applicability|Y|Y|N|N|N|Y|P|fail closed|
|RLS-E021|S:Applicability|D:Applicability|-|M|U|rls_vfy_adapter.py|TC|test_rls_e021_applicability|Y|Y|N|N|N|Y|P|fail closed|
|RLS-E022|S:Applicability|D:Applicability|-|M|U|rls_vfy_adapter.py|TC|test_rls_e022_applicability|Y|Y|N|N|N|Y|P|拒绝，拆独立 Artifact|
|RLS-E023|S:Applicability|D:Applicability|-|M|U|rls_vfy_adapter.py|TC|test_rls_e023_applicability|Y|Y|N|N|N|Y|P|waiting_input|
|RLS-E024|S:Applicability|D:Applicability|+|M|U|rls_vfy_adapter.py|TC|test_rls_e024_applicability|Y|Y|N|N|N|N|P|固定 N/A — Initial Release|
|RLS-E025|S:Contract|D:Contract|-|M|U|rls_contract.py|TC|test_rls_e025_contract|Y|Y|N|N|N|Y|P|waiting_input|
|RLS-E026|S:Contract|D:Contract|-|M|U|rls_contract.py|TC|test_rls_e026_contract|Y|Y|N|N|N|Y|P|不授予执行权限|
|RLS-E027|S:Contract|D:Contract|-|M|U|rls_contract.py|TC|test_rls_e027_contract|Y|Y|N|N|N|Y|P|RLS-G-002 fail|
|RLS-E028|S:Contract|D:Contract|-|M|U|rls_contract.py|TC|test_rls_e028_contract|Y|Y|N|N|N|Y|P|fail|
|RLS-E029|S:Contract|D:Contract|-|M|U|rls_contract.py|TC|test_rls_e029_contract|Y|Y|N|N|N|Y|P|fail|
|RLS-E030|S:Contract|D:Contract|-|M|U|rls_contract.py|TC|test_rls_e030_contract|Y|Y|N|N|N|Y|P|拒绝为 stale|
|RLS-E031|S:Contract|D:Contract|+|M|U|rls_contract.py|TC|test_rls_e031_contract|Y|Y|N|N|N|N|P|PASS|
|RLS-E032|S:Authorization|D:Authorization|+|E|U|rls_authorization.py|TC|test_rls_e032_authorization|N|N|Y|N|Y|N|-|允许，仅本地 Store 写入|
|RLS-E033|S:Authorization|D:Authorization|-|E|U|rls_authorization.py|TC|test_rls_e033_authorization|N|N|Y|N|Y|Y|-|action_required，目标零变化|
|RLS-E034|S:Authorization|D:Authorization|-|E|U|rls_authorization.py|TC|test_rls_e034_authorization|N|N|Y|N|Y|Y|-|stale/拒绝|
|RLS-E035|S:Authorization|D:Authorization|-|E|U|rls_authorization.py|TC|test_rls_e035_authorization|N|N|Y|N|Y|Y|-|拒绝|
|RLS-E036|S:Authorization|D:Authorization|-|E|U|rls_authorization.py|TC|test_rls_e036_authorization|N|N|Y|N|Y|Y|-|旧授权失效|
|RLS-E037|S:Authorization|D:Authorization|-|E|U|rls_authorization.py|TC|test_rls_e037_authorization|N|N|Y|N|Y|Y|-|仍拒绝外部效果|
|RLS-E038|S:Authorization|D:Authorization|+|E|U|rls_authorization.py|TC|test_rls_e038_authorization|N|N|Y|N|Y|N|-|仅执行授权集合|
|RLS-E039|S:Authorization|D:Authorization|-|E|U|rls_authorization.py|TC|test_rls_e039_authorization|N|N|Y|N|Y|Y|-|不保存/脱敏|
|RLS-E040|S:Authorization|D:Authorization|-|E|U|rls_authorization.py|TC|test_rls_e040_authorization|N|N|Y|N|Y|Y|-|阻止/记录 fail，不扩大授权|
|RLS-E041|S:ReleaseItem|D:ReleaseItem|+|E|I|rls_executor.py|TC|test_rls_e041_releaseitem|N|N|Y|Y|N|N|-|实际结果 Evidence 必填|
|RLS-E042|S:ReleaseItem|D:ReleaseItem|+|E|I|rls_executor.py|TC|test_rls_e042_releaseitem|N|N|Y|Y|N|N|-|Evidence + 唯一 Follow-up|
|RLS-E043|S:ReleaseItem|D:ReleaseItem|-|E|I|rls_executor.py|TC|test_rls_e043_releaseitem|N|N|Y|Y|N|Y|-|Evidence + Follow-up|
|RLS-E044|S:ReleaseItem|D:ReleaseItem|+|E|I|rls_executor.py|TC|test_rls_e044_releaseitem|N|N|Y|Y|Y|N|-|合法|
|RLS-E045|S:ReleaseItem|D:ReleaseItem|-|E|I|rls_executor.py|TC|test_rls_e045_releaseitem|N|N|Y|Y|Y|Y|-|非法，应 partial/failed|
|RLS-E046|S:ReleaseItem|D:ReleaseItem|-|E|I|rls_executor.py|TC|test_rls_e046_releaseitem|N|N|Y|Y|N|Y|-|fail|
|RLS-E047|S:ReleaseItem|D:ReleaseItem|-|E|I|rls_executor.py|TC|test_rls_e047_releaseitem|N|N|Y|Y|N|Y|-|不允许|
|RLS-E048|S:ReleaseItem|D:ReleaseItem|-|E|I|rls_executor.py|TC|test_rls_e048_releaseitem|N|N|Y|Y|N|Y|-|拆分|
|RLS-E049|S:ReleaseItem|D:ReleaseItem|-|E|I|rls_executor.py|TC|test_rls_e049_releaseitem|N|N|Y|Y|N|Y|-|fail|
|RLS-E050|S:ReleaseItem|D:ReleaseItem|-|E|I|rls_executor.py|TC|test_rls_e050_releaseitem|N|N|Y|Y|Y|Y|-|不执行或 fail，保存 Evidence|
|RLS-E051|S:Confirmation|D:Confirmation|-|E|I|rls_confirmation.py|TC|test_rls_e051_confirmation|N|N|Y|Y|N|Y|-|不能 RCF pass|
|RLS-E052|S:Confirmation|D:Confirmation|+|E|I|rls_confirmation.py|TC|test_rls_e052_confirmation|N|N|Y|Y|N|N|-|RCF pass|
|RLS-E053|S:Confirmation|D:Confirmation|-|E|I|rls_confirmation.py|TC|test_rls_e053_confirmation|N|N|Y|Y|N|Y|-|RCF fail + Follow-up|
|RLS-E054|S:Confirmation|D:Confirmation|-|E|I|rls_confirmation.py|TC|test_rls_e054_confirmation|N|N|Y|Y|N|Y|-|fail|
|RLS-E055|S:Confirmation|D:Confirmation|+|E|I|rls_confirmation.py|TC|test_rls_e055_confirmation|N|N|Y|Y|N|N|-|RCF not_run，原因指向 RLI|
|RLS-E056|S:Confirmation|D:Confirmation|-|E|I|rls_confirmation.py|TC|test_rls_e056_confirmation|N|N|Y|Y|N|Y|-|fail|
|RLS-E057|S:Confirmation|D:Confirmation|-|E|I|rls_confirmation.py|TC|test_rls_e057_confirmation|N|N|Y|Y|N|Y|-|fail|
|RLS-E058|S:Confirmation|D:Confirmation|-|E|I|rls_confirmation.py|TC|test_rls_e058_confirmation|N|N|Y|Y|N|Y|-|不得 pass|
|RLS-E059|S:Confirmation|D:Confirmation|+|E|I|rls_confirmation.py|TC|test_rls_e059_confirmation|Y|Y|Y|Y|N|N|P|resolved + Evidence|
|RLS-E060|S:Confirmation|D:Confirmation|-|E|I|rls_confirmation.py|TC|test_rls_e060_confirmation|Y|Y|Y|Y|N|Y|P|fail，需当前 active Exception|
|RLS-E061|S:Conclusion|D:Conclusion|-|M|U|rls_conclusion.py|TC|test_rls_e061_conclusion|N|N|N|N|N|Y|-|Conclusion=pending|
|RLS-E062|S:Conclusion|D:Conclusion|-|M|U|rls_conclusion.py|TC|test_rls_e062_conclusion|N|N|N|N|N|Y|-|Conclusion=failed|
|RLS-E063|S:Conclusion|D:Conclusion|+|E|U|rls_conclusion.py|TC|test_rls_e063_conclusion|N|N|Y|N|N|N|-|cancelled|
|RLS-E064|S:Conclusion|D:Conclusion|+|E|I|rls_conclusion.py|TC|test_rls_e064_conclusion|N|N|Y|Y|N|N|-|success|
|RLS-E065|S:Conclusion|D:Conclusion|-|E|I|rls_conclusion.py|TC|test_rls_e065_conclusion|N|N|Y|Y|N|Y|-|partial|
|RLS-E066|S:Conclusion|D:Conclusion|-|M|U|rls_conclusion.py|TC|test_rls_e066_conclusion|N|N|N|N|N|Y|-|fail|
|RLS-E067|S:Conclusion|D:Conclusion|+|M|U|rls_conclusion.py|TC|test_rls_e067_conclusion|N|N|N|N|N|N|-|下一动作同 RLS 新 Revision|
|RLS-E068|S:Conclusion|D:Conclusion|+|M|U|rls_conclusion.py|TC|test_rls_e068_conclusion|N|N|N|N|N|N|-|生成准确 Issue Reference|
|RLS-E069|S:Conclusion|D:Conclusion|-|M|U|rls_conclusion.py|TC|test_rls_e069_conclusion|N|N|N|N|N|Y|-|应 return_pln|
|RLS-E070|S:Conclusion|D:Conclusion|+|E|I|rls_conclusion.py|TC|test_rls_e070_conclusion|N|N|Y|Y|N|N|-|合法且 UX 明确|
|RLS-E071|S:Conclusion|D:Conclusion|-|M|U|rls_conclusion.py|TC|test_rls_e071_conclusion|N|N|N|N|N|Y|-|Artifact 不可信，不冻结|
|RLS-E072|S:Revision|D:Revision|+|E|I|rls_handler.py|TC|test_rls_e072_revision|Y|Y|Y|Y|Y|N|P|同 Revision|
|RLS-E073|S:Revision|D:Revision|+|E|I|rls_handler.py|TC|test_rls_e073_revision|Y|Y|Y|Y|Y|N|P|同 RLS ID，新 Revision、重新 Baseline/授权|
|RLS-E074|S:Revision|D:Revision|-|M|I|rls_handler.py|TC|test_rls_e074_revision|Y|Y|N|N|N|Y|P|返回上游，不在 RLS revise 换包|
|RLS-E075|S:Revision|D:Revision|-|E|I|rls_handler.py|TC|test_rls_e075_revision|N|N|Y|N|N|Y|-|新 RLS Artifact|
|RLS-E076|S:Revision|D:Revision|+|E|I|rls_handler.py|TC|test_rls_e076_revision|N|N|Y|Y|Y|N|-|记录准确 no-op，不制造新结果|
|RLS-E077|S:Revision|D:Revision|-|M|I|rls_handler.py|TC|test_rls_e077_revision|N|N|N|N|N|Y|-|新 Reservation abandoned|
|RLS-E078|S:Revision|D:Revision|-|M|I|rls_handler.py|TC|test_rls_e078_revision|N|N|N|N|N|Y|-|open/failed，不 freeze|
|RLS-E079|S:Revision|D:Revision|-|M|I|rls_handler.py|TC|test_rls_e079_revision|Y|Y|N|N|N|Y|P|check fail|
|RLS-E080|S:Revision|D:Revision|+|R|I|rls_handler.py|TC|test_rls_e080_revision|N|N|Y|Y|N|N|-|PASS|
|RLS-E081|S:Lifecycle|D:Lifecycle|+|R|I|query_rls.py*|TC|test_rls_e081_lifecycle|Y|Y|N|N|N|N|P|停留 RLS|
|RLS-E082|S:Lifecycle|D:Lifecycle|+|R|I|query_rls.py*|TC|test_rls_e082_lifecycle|Y|Y|Y|Y|N|N|P|生命周期完成|
|RLS-E083|S:Lifecycle|D:Lifecycle|+|R|I|query_rls.py*|TC|test_rls_e083_lifecycle|Y|Y|Y|Y|N|N|P|RLS retry|
|RLS-E084|S:Lifecycle|D:Lifecycle|+|R|I|query_rls.py*|TC|test_rls_e084_lifecycle|Y|Y|Y|Y|N|N|P|IMP Control Input|
|RLS-E085|S:Lifecycle|D:Lifecycle|+|R|I|query_rls.py*|TC|test_rls_e085_lifecycle|Y|Y|Y|Y|N|N|P|指向准确 Phase|
|RLS-E086|S:Lifecycle|D:Lifecycle|+|R|I|query_rls.py*|TC|test_rls_e086_lifecycle|N|N|Y|Y|N|N|-|终态显示未产生效果|
|RLS-E087|S:Lifecycle|D:Lifecycle|+|R|I|query_rls.py*|TC|test_rls_e087_lifecycle|Y|Y|Y|Y|N|N|P|Status 正确区分|
