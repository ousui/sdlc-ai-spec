# Checkpoint A — structured persistence and shared domain contract

Base: `f25ed518f662c0ac7306c94f845297f5642c44b2`.
Approved input: the user-reviewed `sdlc-v2-detailed-design.zip` (32-table relational design).

This commit adds the 32-table SQLite schema, immutable content/context guards, managed asset persistence, canonical protocol primitives and a single shared entity/relationship validator. Old runtime replacement is staged after the new installed path is validated.

The five store checkpoint tests are the tests present in this commit. They prove only storage/protocol properties. They are not a host Skill or real-project closure.

Offline implementation work also has phase, execution, local delivery and return modules. At the last local run, 30 new tests passed after fixing a copy/return issue: the copy could contain an earlier `unknown` operation receipt while the origin already held the completed receipt. Returning immutable content must preserve origin progress and retain the incoming observation separately. Those modules are committed in following checkpoints, not claimed as present here.

Remaining: complete public runtime/Skill path, replace old code/contracts, run the recorded Admin/SpringGear JDK21/fansite baseline, then two additional complex-demand rounds. The PR remains Draft.
