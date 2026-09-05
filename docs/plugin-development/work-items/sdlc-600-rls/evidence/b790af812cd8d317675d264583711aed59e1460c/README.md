# RLS propagation repair evidence

Exact Subject: `b790af812cd8d317675d264583711aed59e1460c`; sole parent D: `c9615cec2da3b39949a3fdd8be32396eae6db3aa`.

All five validation profiles and detached fresh profiles executed successfully on this Subject. Actual RLS private/repository counts are 435/1068; RLS critical 87, strict VFY 80, Web repair 120 (original 64 plus propagation 56), real Store 10, Source Lock 14, interface rows 12. All required suites have zero skips, expected failures and unexpected successes.

`raw/` contains this run only. `archive-map.json` maps each original local locator to its byte-identical archived file. stdout/stderr and receipts were scrubbed before their original first write using policy v2; no packaging-time redaction or log rewrite was performed. Expected timeout/error/nonzero outcomes in the independent negative probes are explicitly asserted and are not skipped tests.

`focused/` and `focused-independent/` bind the repair checkpoint; `raw/` and `subject-independent/` bind S3. No old S2/E2 PASS is used for S3. Interface test mappings and verifier structure were reused from the old archive; all verdicts, source bindings and hashes were computed from this run.

Run the read-only byte/schema/receipt verifier from a complete checkout:

```bash
python3 docs/plugin-development/work-items/sdlc-600-rls/evidence/b790af812cd8d317675d264583711aed59e1460c/verify_evidence.py --repository . --directory docs/plugin-development/work-items/sdlc-600-rls/evidence/b790af812cd8d317675d264583711aed59e1460c
```

The sibling delivery package supplies the complete historical Git bundle, final Git bundle, exact S3/E3 source archives and their SHA-256 Manifest. This commit does not embed its own unknown hash; E3 is recorded by post-commit publication readback and PR #10.

Only next work package: independent Web Review. No Web ACCEPTED decision is signed here.

The complete review package also includes precommit-probe-archives.tar.gz: the byte-identical first independent-probe archives preserved after git diff --check rejected an extra print newline. E3 retains its checksum and full file Manifest under precommit-discovery/. The final independent-probe directories are fresh executions of the same 12 assertions with the corrected stdout call.
