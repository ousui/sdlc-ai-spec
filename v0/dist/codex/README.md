# SDLC engineering package

Fixed repository: https://github.com/ousui/sdlc-ai-spec

Source port of Spec Kit v1.0.5. Nine local skills; no INIT, GitHub, translation, workflow engine or event hooks. This package is not yet an end-user release. Only engineering/fixture checks are claimed. Native host discovery and real-project behavior have not been tested.

Requires Bash and Python 3.9+ plus standard POSIX tools. Core resources stay in this package; project data belongs in .sdlc. No uv/specify-cli is needed at runtime. Plugin location must be obtained from the loaded skill path (or the documented Claude plugin variable), never stored in project metadata. Missing project state is an error, not automatic init.
