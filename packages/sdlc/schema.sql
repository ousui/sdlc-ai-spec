-- SDLC v2 relational schema, migration 1.
-- Derived from the approved v2 model; runtime validates graph and workflow semantics.
PRAGMA foreign_keys=ON;

CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY,migration_digest TEXT NOT NULL,applied_at TEXT NOT NULL) STRICT;
CREATE TABLE projects (project_id TEXT PRIMARY KEY NOT NULL,name TEXT NOT NULL,created_at TEXT NOT NULL) STRICT;
CREATE TABLE contexts (
 context_id TEXT PRIMARY KEY NOT NULL,project_id TEXT NOT NULL,parent_id TEXT,summary TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('draft','committed')),digest TEXT,created_at TEXT NOT NULL,
 UNIQUE(project_id,context_id),FOREIGN KEY(project_id) REFERENCES projects(project_id),
 FOREIGN KEY(project_id,parent_id) REFERENCES contexts(project_id,context_id)
) STRICT;
CREATE TABLE context_entries (
 context_id TEXT NOT NULL,entry_id TEXT NOT NULL,kind TEXT NOT NULL CHECK(kind IN ('fact','rule','resource','command')),
 name TEXT NOT NULL,content TEXT NOT NULL,origin TEXT,settings_json TEXT NOT NULL DEFAULT '{}',
 PRIMARY KEY(context_id,entry_id),UNIQUE(context_id,kind,name),FOREIGN KEY(context_id) REFERENCES contexts(context_id)
) STRICT;
CREATE TABLE workspaces (
 workspace_id TEXT PRIMARY KEY NOT NULL,project_id TEXT NOT NULL,label TEXT NOT NULL,instance_id TEXT NOT NULL,created_at TEXT NOT NULL,
 UNIQUE(project_id,workspace_id),FOREIGN KEY(project_id) REFERENCES projects(project_id)
) STRICT;
CREATE TABLE changes (
 change_id TEXT PRIMARY KEY NOT NULL,project_id TEXT NOT NULL,slug TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('active','completed','archived')),active_revision_id TEXT,initial_base_commit TEXT,
 delivery_mode TEXT NOT NULL CHECK(delivery_mode IN ('local','git','deployment')),delivery_target TEXT NOT NULL,created_at TEXT NOT NULL,
 UNIQUE(project_id,change_id),UNIQUE(project_id,slug),FOREIGN KEY(project_id) REFERENCES projects(project_id),
 FOREIGN KEY(change_id,active_revision_id) REFERENCES revisions(change_id,revision_id)
) STRICT;
CREATE TABLE revisions (
 revision_id TEXT PRIMARY KEY NOT NULL,project_id TEXT NOT NULL,change_id TEXT NOT NULL,context_id TEXT NOT NULL,parent_id TEXT,merged_from_id TEXT,
 created_phase TEXT NOT NULL CHECK(created_phase IN ('REQ','DSN','PLN','IMP','VFY','RLS')),
 state TEXT NOT NULL CHECK(state IN ('draft','committed','abandoned')),generation INTEGER NOT NULL DEFAULT 0 CHECK(generation>=0),
 title TEXT NOT NULL,summary TEXT NOT NULL,goal TEXT NOT NULL,in_scope TEXT NOT NULL,out_of_scope TEXT NOT NULL,digest TEXT,created_at TEXT NOT NULL,
 UNIQUE(change_id,revision_id),UNIQUE(project_id,revision_id),UNIQUE(project_id,change_id,revision_id),
 FOREIGN KEY(project_id,change_id) REFERENCES changes(project_id,change_id),FOREIGN KEY(project_id,context_id) REFERENCES contexts(project_id,context_id),
 FOREIGN KEY(change_id,parent_id) REFERENCES revisions(change_id,revision_id),FOREIGN KEY(change_id,merged_from_id) REFERENCES revisions(change_id,revision_id)
) STRICT;
CREATE TABLE sources (
 revision_id TEXT NOT NULL,source_id TEXT NOT NULL,kind TEXT NOT NULL CHECK(kind IN ('text','document','image','observation','assumption')),
 original_text TEXT NOT NULL,origin_uri TEXT,observed_at TEXT,ordinal INTEGER NOT NULL CHECK(ordinal>=0),
 FOREIGN KEY(revision_id) REFERENCES revisions(revision_id),PRIMARY KEY(revision_id,source_id)
) STRICT;
CREATE TABLE requirements (
 revision_id TEXT NOT NULL,requirement_id TEXT NOT NULL,kind TEXT NOT NULL CHECK(kind IN ('behavior','rule','quality','constraint')),
 statement TEXT NOT NULL,ordinal INTEGER NOT NULL,FOREIGN KEY(revision_id) REFERENCES revisions(revision_id),PRIMARY KEY(revision_id,requirement_id)
) STRICT;
CREATE TABLE criteria (
 revision_id TEXT NOT NULL,criterion_id TEXT NOT NULL,condition_text TEXT NOT NULL,expected_result TEXT NOT NULL,ordinal INTEGER NOT NULL,
 FOREIGN KEY(revision_id) REFERENCES revisions(revision_id),PRIMARY KEY(revision_id,criterion_id)
) STRICT;
CREATE TABLE requirement_sources (
 revision_id TEXT NOT NULL,requirement_id TEXT NOT NULL,source_id TEXT NOT NULL,
 FOREIGN KEY(revision_id) REFERENCES revisions(revision_id),PRIMARY KEY(revision_id,requirement_id,source_id),
 FOREIGN KEY(revision_id,requirement_id) REFERENCES requirements(revision_id,requirement_id),FOREIGN KEY(revision_id,source_id) REFERENCES sources(revision_id,source_id)
) STRICT;
CREATE TABLE criterion_requirements (
 revision_id TEXT NOT NULL,criterion_id TEXT NOT NULL,requirement_id TEXT NOT NULL,
 FOREIGN KEY(revision_id) REFERENCES revisions(revision_id),PRIMARY KEY(revision_id,criterion_id,requirement_id),
 FOREIGN KEY(revision_id,criterion_id) REFERENCES criteria(revision_id,criterion_id),FOREIGN KEY(revision_id,requirement_id) REFERENCES requirements(revision_id,requirement_id)
) STRICT;
CREATE TABLE designs (
 revision_id TEXT NOT NULL,design_id TEXT NOT NULL,domain TEXT NOT NULL,title TEXT NOT NULL,decision TEXT NOT NULL,rationale TEXT NOT NULL,
 alternatives TEXT NOT NULL,detail TEXT NOT NULL,ordinal INTEGER NOT NULL,
 FOREIGN KEY(revision_id) REFERENCES revisions(revision_id),PRIMARY KEY(revision_id,design_id)
) STRICT;
CREATE TABLE design_requirements (
 revision_id TEXT NOT NULL,design_id TEXT NOT NULL,requirement_id TEXT NOT NULL,
 FOREIGN KEY(revision_id) REFERENCES revisions(revision_id),PRIMARY KEY(revision_id,design_id,requirement_id),
 FOREIGN KEY(revision_id,design_id) REFERENCES designs(revision_id,design_id),FOREIGN KEY(revision_id,requirement_id) REFERENCES requirements(revision_id,requirement_id)
) STRICT;
CREATE TABLE tasks (
 revision_id TEXT NOT NULL,task_id TEXT NOT NULL,target_phase TEXT NOT NULL CHECK(target_phase IN ('IMP','VFY','RLS')),
 kind TEXT NOT NULL CHECK(kind IN ('prepare','implement','verify','review','deliver')),title TEXT NOT NULL,description TEXT NOT NULL,
 completion_text TEXT NOT NULL,scope_paths_json TEXT NOT NULL,ordinal INTEGER NOT NULL,
 FOREIGN KEY(revision_id) REFERENCES revisions(revision_id),PRIMARY KEY(revision_id,task_id)
) STRICT;
CREATE TABLE task_designs (
 revision_id TEXT NOT NULL,task_id TEXT NOT NULL,design_id TEXT NOT NULL,
 FOREIGN KEY(revision_id) REFERENCES revisions(revision_id),PRIMARY KEY(revision_id,task_id,design_id),
 FOREIGN KEY(revision_id,task_id) REFERENCES tasks(revision_id,task_id),FOREIGN KEY(revision_id,design_id) REFERENCES designs(revision_id,design_id)
) STRICT;
CREATE TABLE task_criteria (
 revision_id TEXT NOT NULL,task_id TEXT NOT NULL,criterion_id TEXT NOT NULL,
 FOREIGN KEY(revision_id) REFERENCES revisions(revision_id),PRIMARY KEY(revision_id,task_id,criterion_id),
 FOREIGN KEY(revision_id,task_id) REFERENCES tasks(revision_id,task_id),FOREIGN KEY(revision_id,criterion_id) REFERENCES criteria(revision_id,criterion_id)
) STRICT;
CREATE TABLE task_dependencies (
 revision_id TEXT NOT NULL,task_id TEXT NOT NULL,predecessor_id TEXT NOT NULL,reason TEXT NOT NULL,
 FOREIGN KEY(revision_id) REFERENCES revisions(revision_id),PRIMARY KEY(revision_id,task_id,predecessor_id),CHECK(task_id<>predecessor_id),
 FOREIGN KEY(revision_id,task_id) REFERENCES tasks(revision_id,task_id),FOREIGN KEY(revision_id,predecessor_id) REFERENCES tasks(revision_id,task_id)
) STRICT;
CREATE TABLE checks (
 revision_id TEXT NOT NULL,check_id TEXT NOT NULL,task_id TEXT,
 purpose TEXT NOT NULL CHECK(purpose IN ('acceptance','precondition','convergence','release_readback')),
 method TEXT NOT NULL CHECK(method IN ('test','inspection','analysis','demonstration')),executor TEXT NOT NULL CHECK(executor IN ('command','agent','human')),
 description TEXT NOT NULL,expected_result TEXT NOT NULL,argv_json TEXT,required INTEGER NOT NULL CHECK(required IN (0,1)),
 timeout_seconds INTEGER CHECK(timeout_seconds>0),max_age_seconds INTEGER CHECK(max_age_seconds>=0),
 FOREIGN KEY(revision_id) REFERENCES revisions(revision_id),PRIMARY KEY(revision_id,check_id),
 FOREIGN KEY(revision_id,task_id) REFERENCES tasks(revision_id,task_id),
 CHECK((executor='command' AND argv_json IS NOT NULL) OR (executor<>'command' AND argv_json IS NULL))
) STRICT;
CREATE TABLE check_criteria (
 revision_id TEXT NOT NULL,check_id TEXT NOT NULL,criterion_id TEXT NOT NULL,
 FOREIGN KEY(revision_id) REFERENCES revisions(revision_id),PRIMARY KEY(revision_id,check_id,criterion_id),
 FOREIGN KEY(revision_id,check_id) REFERENCES checks(revision_id,check_id),FOREIGN KEY(revision_id,criterion_id) REFERENCES criteria(revision_id,criterion_id)
) STRICT;
CREATE TABLE preconditions (
 revision_id TEXT NOT NULL,condition_id TEXT NOT NULL,consumer_task_id TEXT NOT NULL,check_id TEXT NOT NULL,producer_task_id TEXT,
 enforce_at TEXT NOT NULL CHECK(enforce_at IN ('start','execute','complete')),reason TEXT NOT NULL,
 FOREIGN KEY(revision_id) REFERENCES revisions(revision_id),PRIMARY KEY(revision_id,condition_id),
 FOREIGN KEY(revision_id,consumer_task_id) REFERENCES tasks(revision_id,task_id),FOREIGN KEY(revision_id,producer_task_id) REFERENCES tasks(revision_id,task_id),
 FOREIGN KEY(revision_id,check_id) REFERENCES checks(revision_id,check_id),
 CHECK(producer_task_id IS NULL OR producer_task_id<>consumer_task_id OR enforce_at='complete')
) STRICT;
CREATE TABLE assets (
 asset_id TEXT PRIMARY KEY NOT NULL,project_id TEXT NOT NULL,sha256 TEXT NOT NULL CHECK(length(sha256)=64),
 size_bytes INTEGER NOT NULL CHECK(size_bytes>=0),media_type TEXT NOT NULL,created_at TEXT NOT NULL,
 UNIQUE(project_id,asset_id),UNIQUE(project_id,sha256),FOREIGN KEY(project_id) REFERENCES projects(project_id)
) STRICT;
CREATE TABLE runs (
 run_id TEXT PRIMARY KEY NOT NULL,project_id TEXT NOT NULL,change_id TEXT,workspace_id TEXT NOT NULL,input_revision_id TEXT,
 status TEXT NOT NULL CHECK(status IN ('created','running','blocked','completed','failed','interrupted','cancelled')),
 actor_id TEXT NOT NULL,runtime_version TEXT NOT NULL,contract_version TEXT NOT NULL,skill_version TEXT NOT NULL,
 review_mode TEXT NOT NULL CHECK(review_mode IN ('auto','assisted')),error_code TEXT,error_message TEXT,started_at TEXT NOT NULL,finished_at TEXT,
 UNIQUE(project_id,run_id),UNIQUE(change_id,run_id),
 FOREIGN KEY(project_id,workspace_id) REFERENCES workspaces(project_id,workspace_id),FOREIGN KEY(project_id,change_id) REFERENCES changes(project_id,change_id),
 FOREIGN KEY(change_id,input_revision_id) REFERENCES revisions(change_id,revision_id)
) STRICT;
CREATE TABLE code_snapshots (
 snapshot_id TEXT PRIMARY KEY NOT NULL,project_id TEXT NOT NULL,run_id TEXT NOT NULL,resource_key TEXT NOT NULL,head_commit TEXT,tree_id TEXT,patch_asset_id TEXT,
 untracked_json TEXT NOT NULL DEFAULT '[]',environment_digest TEXT NOT NULL,digest TEXT NOT NULL,captured_at TEXT NOT NULL,
 UNIQUE(project_id,snapshot_id),FOREIGN KEY(project_id,run_id) REFERENCES runs(project_id,run_id),FOREIGN KEY(project_id,patch_asset_id) REFERENCES assets(project_id,asset_id)
) STRICT;
CREATE TABLE steps (
 step_id TEXT PRIMARY KEY NOT NULL,project_id TEXT NOT NULL,change_id TEXT,run_id TEXT NOT NULL,
 phase TEXT NOT NULL CHECK(phase IN ('INIT','CTX','REQ','DSN','PLN','IMP','VFY','RLS')),step_key TEXT NOT NULL,attempt INTEGER NOT NULL CHECK(attempt>0),
 input_revision_id TEXT,output_revision_id TEXT,task_id TEXT,snapshot_id TEXT,
 status TEXT NOT NULL CHECK(status IN ('running','completed','blocked','failed','interrupted','cancelled')),
 outcome TEXT CHECK(outcome IN ('pass','fail','not_applicable','unknown')),started_at TEXT NOT NULL,finished_at TEXT,
 UNIQUE(run_id,step_key,attempt),UNIQUE(project_id,step_id),FOREIGN KEY(project_id,run_id) REFERENCES runs(project_id,run_id),
 CHECK((phase IN ('INIT','CTX') AND change_id IS NULL) OR (phase NOT IN ('INIT','CTX') AND change_id IS NOT NULL)),
 FOREIGN KEY(project_id,change_id) REFERENCES changes(project_id,change_id),FOREIGN KEY(change_id,run_id) REFERENCES runs(change_id,run_id),
 FOREIGN KEY(change_id,input_revision_id) REFERENCES revisions(change_id,revision_id),FOREIGN KEY(change_id,output_revision_id) REFERENCES revisions(change_id,revision_id),
 FOREIGN KEY(input_revision_id,task_id) REFERENCES tasks(revision_id,task_id),FOREIGN KEY(project_id,snapshot_id) REFERENCES code_snapshots(project_id,snapshot_id)
) STRICT;
CREATE TABLE check_results (
 result_id TEXT PRIMARY KEY NOT NULL,project_id TEXT NOT NULL,change_id TEXT NOT NULL,revision_id TEXT NOT NULL,check_id TEXT NOT NULL,step_id TEXT NOT NULL,snapshot_id TEXT,
 status TEXT NOT NULL CHECK(status IN ('pass','fail','blocked','unknown')),evidence_asset_id TEXT NOT NULL,
 source_kind TEXT NOT NULL CHECK(source_kind IN ('command','agent','human','reused')),reused_from_id TEXT,observed_at TEXT NOT NULL,expires_at TEXT,summary TEXT NOT NULL,
 UNIQUE(project_id,result_id),FOREIGN KEY(project_id,change_id,revision_id) REFERENCES revisions(project_id,change_id,revision_id),
 FOREIGN KEY(revision_id,check_id) REFERENCES checks(revision_id,check_id),FOREIGN KEY(project_id,step_id) REFERENCES steps(project_id,step_id),
 FOREIGN KEY(project_id,snapshot_id) REFERENCES code_snapshots(project_id,snapshot_id),FOREIGN KEY(project_id,evidence_asset_id) REFERENCES assets(project_id,asset_id),
 FOREIGN KEY(project_id,reused_from_id) REFERENCES check_results(project_id,result_id)
) STRICT;
CREATE TABLE findings (
 finding_id TEXT PRIMARY KEY NOT NULL,project_id TEXT NOT NULL,change_id TEXT NOT NULL,revision_id TEXT NOT NULL,result_id TEXT NOT NULL,criterion_id TEXT,design_id TEXT,task_id TEXT,
 return_phase TEXT NOT NULL CHECK(return_phase IN ('REQ','DSN','PLN','IMP','VFY','RLS')),kind TEXT NOT NULL CHECK(kind IN ('missing','partial','contradicts','unrequested','environment')),
 severity TEXT NOT NULL CHECK(severity IN ('blocking','advisory')),status TEXT NOT NULL CHECK(status IN ('open','addressed','resolved','rejected')),
 fingerprint TEXT NOT NULL,description TEXT NOT NULL,resolution_result_id TEXT,UNIQUE(change_id,fingerprint),
 FOREIGN KEY(project_id,change_id,revision_id) REFERENCES revisions(project_id,change_id,revision_id),FOREIGN KEY(project_id,result_id) REFERENCES check_results(project_id,result_id),
 FOREIGN KEY(revision_id,criterion_id) REFERENCES criteria(revision_id,criterion_id),FOREIGN KEY(revision_id,design_id) REFERENCES designs(revision_id,design_id),
 FOREIGN KEY(revision_id,task_id) REFERENCES tasks(revision_id,task_id),FOREIGN KEY(project_id,resolution_result_id) REFERENCES check_results(project_id,result_id),
 CHECK(status NOT IN ('resolved','rejected') OR resolution_result_id IS NOT NULL)
) STRICT;
CREATE TABLE deliveries (
 delivery_id TEXT PRIMARY KEY NOT NULL,project_id TEXT NOT NULL,change_id TEXT NOT NULL,revision_id TEXT NOT NULL,step_id TEXT NOT NULL,snapshot_id TEXT NOT NULL,vfy_result_id TEXT NOT NULL,
 mode TEXT NOT NULL CHECK(mode IN ('local','git','deployment')),target TEXT NOT NULL,effect_key TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('prepared','succeeded','failed','unknown','cancelled')),readback_result_id TEXT,summary TEXT NOT NULL,
 UNIQUE(project_id,delivery_id),UNIQUE(project_id,effect_key),FOREIGN KEY(project_id,change_id,revision_id) REFERENCES revisions(project_id,change_id,revision_id),
 FOREIGN KEY(project_id,step_id) REFERENCES steps(project_id,step_id),FOREIGN KEY(project_id,snapshot_id) REFERENCES code_snapshots(project_id,snapshot_id),
 FOREIGN KEY(project_id,vfy_result_id) REFERENCES check_results(project_id,result_id),FOREIGN KEY(project_id,readback_result_id) REFERENCES check_results(project_id,result_id)
) STRICT;
CREATE TABLE asset_links (
 project_id TEXT NOT NULL,link_id TEXT PRIMARY KEY NOT NULL,asset_id TEXT NOT NULL,revision_id TEXT,source_id TEXT,design_id TEXT,result_id TEXT,delivery_id TEXT,
 original_name TEXT NOT NULL,purpose TEXT NOT NULL,ordinal INTEGER NOT NULL DEFAULT 0,
 FOREIGN KEY(project_id,asset_id) REFERENCES assets(project_id,asset_id),FOREIGN KEY(project_id,revision_id) REFERENCES revisions(project_id,revision_id),
 FOREIGN KEY(revision_id,source_id) REFERENCES sources(revision_id,source_id),FOREIGN KEY(revision_id,design_id) REFERENCES designs(revision_id,design_id),
 FOREIGN KEY(project_id,result_id) REFERENCES check_results(project_id,result_id),FOREIGN KEY(project_id,delivery_id) REFERENCES deliveries(project_id,delivery_id),
 CHECK((source_id IS NOT NULL)+(design_id IS NOT NULL)+(result_id IS NOT NULL)+(delivery_id IS NOT NULL)=1),
 CHECK((source_id IS NULL AND design_id IS NULL) OR revision_id IS NOT NULL)
) STRICT;
CREATE TABLE authorizations (
 authorization_id TEXT PRIMARY KEY NOT NULL,project_id TEXT NOT NULL,change_id TEXT NOT NULL,actor_id TEXT NOT NULL,
 action TEXT NOT NULL CHECK(action IN ('edit_local','run_check','package_local','git_commit','git_push','create_pr','merge','deploy')),
 target TEXT NOT NULL,issued_by TEXT NOT NULL,basis_text TEXT NOT NULL,issued_at TEXT NOT NULL,expires_at TEXT,revoked_at TEXT,
 FOREIGN KEY(project_id,change_id) REFERENCES changes(project_id,change_id)
) STRICT;
CREATE TABLE operations (
 operation_id TEXT PRIMARY KEY NOT NULL,project_id TEXT NOT NULL,run_id TEXT,command TEXT NOT NULL,request_digest TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('succeeded','rejected','unknown')),response_json TEXT NOT NULL,created_at TEXT NOT NULL,
 FOREIGN KEY(project_id) REFERENCES projects(project_id),FOREIGN KEY(project_id,run_id) REFERENCES runs(project_id,run_id)
) STRICT;
CREATE TABLE imports (
 import_id TEXT PRIMARY KEY NOT NULL,source_store_id TEXT NOT NULL,bundle_digest TEXT NOT NULL UNIQUE,
 status TEXT NOT NULL CHECK(status IN ('imported','conflict','rejected')),summary TEXT NOT NULL,created_at TEXT NOT NULL
) STRICT;
CREATE UNIQUE INDEX one_draft_per_change ON revisions(change_id) WHERE state='draft';
CREATE INDEX changes_by_project ON changes(project_id,state);
CREATE INDEX runs_by_change ON runs(change_id,started_at);
CREATE INDEX results_by_subject ON check_results(revision_id,check_id,snapshot_id,observed_at);
CREATE INDEX findings_open ON findings(change_id,status,severity);
CREATE INDEX steps_by_task ON steps(change_id,task_id,status);

CREATE TRIGGER lock_sources_insert BEFORE INSERT ON sources WHEN (SELECT state FROM revisions WHERE revision_id=NEW.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_sources_update BEFORE UPDATE ON sources WHEN (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_sources_delete BEFORE DELETE ON sources WHEN (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_sources_move BEFORE UPDATE ON sources WHEN NEW.revision_id<>OLD.revision_id BEGIN SELECT RAISE(ABORT,'revision identity cannot change'); END;
CREATE TRIGGER lock_requirements_insert BEFORE INSERT ON requirements WHEN (SELECT state FROM revisions WHERE revision_id=NEW.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_requirements_update BEFORE UPDATE ON requirements WHEN (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_requirements_delete BEFORE DELETE ON requirements WHEN (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_requirements_move BEFORE UPDATE ON requirements WHEN NEW.revision_id<>OLD.revision_id BEGIN SELECT RAISE(ABORT,'revision identity cannot change'); END;
CREATE TRIGGER lock_criteria_insert BEFORE INSERT ON criteria WHEN (SELECT state FROM revisions WHERE revision_id=NEW.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_criteria_update BEFORE UPDATE ON criteria WHEN (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_criteria_delete BEFORE DELETE ON criteria WHEN (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_criteria_move BEFORE UPDATE ON criteria WHEN NEW.revision_id<>OLD.revision_id BEGIN SELECT RAISE(ABORT,'revision identity cannot change'); END;
CREATE TRIGGER lock_requirement_sources_insert BEFORE INSERT ON requirement_sources WHEN (SELECT state FROM revisions WHERE revision_id=NEW.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_requirement_sources_update BEFORE UPDATE ON requirement_sources WHEN (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_requirement_sources_delete BEFORE DELETE ON requirement_sources WHEN (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_requirement_sources_move BEFORE UPDATE ON requirement_sources WHEN NEW.revision_id<>OLD.revision_id BEGIN SELECT RAISE(ABORT,'revision identity cannot change'); END;
CREATE TRIGGER lock_criterion_requirements_insert BEFORE INSERT ON criterion_requirements WHEN (SELECT state FROM revisions WHERE revision_id=NEW.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_criterion_requirements_update BEFORE UPDATE ON criterion_requirements WHEN (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_criterion_requirements_delete BEFORE DELETE ON criterion_requirements WHEN (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_criterion_requirements_move BEFORE UPDATE ON criterion_requirements WHEN NEW.revision_id<>OLD.revision_id BEGIN SELECT RAISE(ABORT,'revision identity cannot change'); END;
CREATE TRIGGER lock_designs_insert BEFORE INSERT ON designs WHEN (SELECT state FROM revisions WHERE revision_id=NEW.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_designs_update BEFORE UPDATE ON designs WHEN (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_designs_delete BEFORE DELETE ON designs WHEN (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_designs_move BEFORE UPDATE ON designs WHEN NEW.revision_id<>OLD.revision_id BEGIN SELECT RAISE(ABORT,'revision identity cannot change'); END;
CREATE TRIGGER lock_design_requirements_insert BEFORE INSERT ON design_requirements WHEN (SELECT state FROM revisions WHERE revision_id=NEW.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_design_requirements_update BEFORE UPDATE ON design_requirements WHEN (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_design_requirements_delete BEFORE DELETE ON design_requirements WHEN (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_design_requirements_move BEFORE UPDATE ON design_requirements WHEN NEW.revision_id<>OLD.revision_id BEGIN SELECT RAISE(ABORT,'revision identity cannot change'); END;
CREATE TRIGGER lock_tasks_insert BEFORE INSERT ON tasks WHEN (SELECT state FROM revisions WHERE revision_id=NEW.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_tasks_update BEFORE UPDATE ON tasks WHEN (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_tasks_delete BEFORE DELETE ON tasks WHEN (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_tasks_move BEFORE UPDATE ON tasks WHEN NEW.revision_id<>OLD.revision_id BEGIN SELECT RAISE(ABORT,'revision identity cannot change'); END;
CREATE TRIGGER lock_task_designs_insert BEFORE INSERT ON task_designs WHEN (SELECT state FROM revisions WHERE revision_id=NEW.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_task_designs_update BEFORE UPDATE ON task_designs WHEN (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_task_designs_delete BEFORE DELETE ON task_designs WHEN (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_task_designs_move BEFORE UPDATE ON task_designs WHEN NEW.revision_id<>OLD.revision_id BEGIN SELECT RAISE(ABORT,'revision identity cannot change'); END;
CREATE TRIGGER lock_task_criteria_insert BEFORE INSERT ON task_criteria WHEN (SELECT state FROM revisions WHERE revision_id=NEW.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_task_criteria_update BEFORE UPDATE ON task_criteria WHEN (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_task_criteria_delete BEFORE DELETE ON task_criteria WHEN (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_task_criteria_move BEFORE UPDATE ON task_criteria WHEN NEW.revision_id<>OLD.revision_id BEGIN SELECT RAISE(ABORT,'revision identity cannot change'); END;
CREATE TRIGGER lock_task_dependencies_insert BEFORE INSERT ON task_dependencies WHEN (SELECT state FROM revisions WHERE revision_id=NEW.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_task_dependencies_update BEFORE UPDATE ON task_dependencies WHEN (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_task_dependencies_delete BEFORE DELETE ON task_dependencies WHEN (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_task_dependencies_move BEFORE UPDATE ON task_dependencies WHEN NEW.revision_id<>OLD.revision_id BEGIN SELECT RAISE(ABORT,'revision identity cannot change'); END;
CREATE TRIGGER lock_checks_insert BEFORE INSERT ON checks WHEN (SELECT state FROM revisions WHERE revision_id=NEW.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_checks_update BEFORE UPDATE ON checks WHEN (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_checks_delete BEFORE DELETE ON checks WHEN (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_checks_move BEFORE UPDATE ON checks WHEN NEW.revision_id<>OLD.revision_id BEGIN SELECT RAISE(ABORT,'revision identity cannot change'); END;
CREATE TRIGGER lock_check_criteria_insert BEFORE INSERT ON check_criteria WHEN (SELECT state FROM revisions WHERE revision_id=NEW.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_check_criteria_update BEFORE UPDATE ON check_criteria WHEN (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_check_criteria_delete BEFORE DELETE ON check_criteria WHEN (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_check_criteria_move BEFORE UPDATE ON check_criteria WHEN NEW.revision_id<>OLD.revision_id BEGIN SELECT RAISE(ABORT,'revision identity cannot change'); END;
CREATE TRIGGER lock_preconditions_insert BEFORE INSERT ON preconditions WHEN (SELECT state FROM revisions WHERE revision_id=NEW.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_preconditions_update BEFORE UPDATE ON preconditions WHEN (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_preconditions_delete BEFORE DELETE ON preconditions WHEN (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_preconditions_move BEFORE UPDATE ON preconditions WHEN NEW.revision_id<>OLD.revision_id BEGIN SELECT RAISE(ABORT,'revision identity cannot change'); END;
CREATE TRIGGER lock_revision_update BEFORE UPDATE ON revisions WHEN OLD.state<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_revision_delete BEFORE DELETE ON revisions WHEN OLD.state<>'draft' BEGIN SELECT RAISE(ABORT,'committed revision is immutable'); END;
CREATE TRIGGER lock_asset_links_insert BEFORE INSERT ON asset_links WHEN NEW.revision_id IS NOT NULL AND (SELECT state FROM revisions WHERE revision_id=NEW.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed attachment link is immutable'); END;
CREATE TRIGGER lock_asset_links_update BEFORE UPDATE ON asset_links WHEN OLD.revision_id IS NOT NULL AND (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed attachment link is immutable'); END;
CREATE TRIGGER lock_asset_links_delete BEFORE DELETE ON asset_links WHEN OLD.revision_id IS NOT NULL AND (SELECT state FROM revisions WHERE revision_id=OLD.revision_id)<>'draft' BEGIN SELECT RAISE(ABORT,'committed attachment link is immutable'); END;
CREATE TRIGGER lock_asset_links_move BEFORE UPDATE ON asset_links WHEN NEW.revision_id IS NOT OLD.revision_id BEGIN SELECT RAISE(ABORT,'attachment revision identity cannot change'); END;
CREATE TRIGGER lock_ctx_entry_insert BEFORE INSERT ON context_entries WHEN (SELECT state FROM contexts WHERE context_id=NEW.context_id)='committed' BEGIN SELECT RAISE(ABORT,'committed context is immutable'); END;
CREATE TRIGGER lock_ctx_entry_update BEFORE UPDATE ON context_entries WHEN (SELECT state FROM contexts WHERE context_id=OLD.context_id)='committed' BEGIN SELECT RAISE(ABORT,'committed context is immutable'); END;
CREATE TRIGGER lock_ctx_entry_delete BEFORE DELETE ON context_entries WHEN (SELECT state FROM contexts WHERE context_id=OLD.context_id)='committed' BEGIN SELECT RAISE(ABORT,'committed context is immutable'); END;
CREATE TRIGGER lock_ctx_entry_move BEFORE UPDATE ON context_entries WHEN NEW.context_id<>OLD.context_id BEGIN SELECT RAISE(ABORT,'context identity cannot change'); END;
CREATE TRIGGER lock_ctx_update BEFORE UPDATE ON contexts WHEN OLD.state='committed' BEGIN SELECT RAISE(ABORT,'committed context is immutable'); END;
CREATE TRIGGER lock_ctx_delete BEFORE DELETE ON contexts WHEN OLD.state='committed' BEGIN SELECT RAISE(ABORT,'committed context is immutable'); END;

CREATE TRIGGER adopted_revision_committed BEFORE UPDATE OF active_revision_id ON changes
WHEN NEW.active_revision_id IS NOT NULL AND (SELECT state FROM revisions WHERE revision_id=NEW.active_revision_id)<>'committed'
BEGIN SELECT RAISE(ABORT,'only committed revisions may be adopted'); END;
