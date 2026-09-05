# RLS Validation Close Loop

Final unified entrypoint:

```bash
python3 tools/run_rls_delivery_validation.py \
  --profile <quick|phase|full|external|attest> \
  --source-sha <exact-sha> --json-out <path>
```

Profiles:

- `quick`: syntax, JSON/schema, focused private tests, case coverage;
- `phase`: quick + Fixed Eval, Source Lock, Runtime Independence, authorization review;
- `full`: phase + VFY gates and full repository regression;
- `external`: full + two exact real-project full chains using local sandbox targets;
- `attest`: fresh exact implementation-SHA rerun, Evidence hashes and repository manifest.

The Web implementation provides only `provisional/quick`. The final validator
fails closed on missing files/commands, binds exact SHA, emits JSON, retains logs,
and records argv, cwd, exit code, duration and log digest with secret redaction.
It never relies on GitHub Actions, modifies main or performs a real target effect.
