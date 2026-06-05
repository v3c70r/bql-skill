#!/usr/bin/env python3
"""
BQL Skill — Pipeline Orchestrator (cross-platform entry point)

Usage:
  python scripts/run_pipeline.py              # Full pipeline
  python scripts/run_pipeline.py --agent 1    # Only Agent 1
  python scripts/run_pipeline.py --loop       # Continuous improvement loop
"""

import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone
import yaml

# Resolve to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "automation"))


def run_agent1(project_dir: Path) -> dict:
    from agent1.corpus_builder import CorpusBuilder
    builder = CorpusBuilder()
    return builder.run_full_corpus_build()


def run_agent2(project_dir: Path) -> dict:
    from agent2.skill_builder import SkillBuilder
    builder = SkillBuilder()
    return builder.run_full_skill_build()


def run_agent3(project_dir: Path, query_map: dict = None) -> dict:
    from agent3.auditor import Auditor
    auditor = Auditor()
    return auditor.run_full_audit(query_map)


def run_agent4(project_dir: Path) -> dict:
    from agent4.adversarial_user import AdversarialUser
    adversary = AdversarialUser()
    return adversary.run_adversarial_generation()


def run_full_pipeline(project_dir: Path):
    start_time = time.time()
    results = {"pipeline_run": datetime.now(timezone.utc).isoformat(), "agents": {}}
    results["agents"]["agent1"] = run_agent1(project_dir)
    results["agents"]["agent2"] = run_agent2(project_dir)
    results["agents"]["agent3"] = run_agent3(project_dir)
    results["agents"]["agent4"] = run_agent4(project_dir)
    
    elapsed = time.time() - start_time
    results["elapsed_seconds"] = round(elapsed, 1)
    
    reports_dir = project_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = reports_dir / f"pipeline_run_{run_id}.yaml"
    report_path.write_text(yaml.dump(results, default_flow_style=False, sort_keys=False))
    
    print(f"\nPipeline complete in {elapsed:.1f}s")
    print(f"Report: {report_path}")
    
    agent3 = results["agents"].get("agent3", {})
    eval_run = agent3.get("evaluation_run", {})
    if eval_run:
        print(f"\nOverall Score: {eval_run.get('overall_score', 'N/A')}%")
        print(f"Passed: {eval_run.get('passed_tests', 0)}/{eval_run.get('total_tests', 0)}")
    
    return results


def run_improvement_loop(project_dir: Path, max_iterations: int = 10):
    from agent3.auditor import Auditor
    from agent2.skill_builder import SkillBuilder
    
    auditor = Auditor()
    builder = SkillBuilder()
    history = []
    
    for iteration in range(1, max_iterations + 1):
        print(f"\n{'='*40}\nIteration {iteration}/{max_iterations}\n{'='*40}")
        audit_result = auditor.run_full_audit()
        eval_run = audit_result.get("evaluation_run", {})
        score = eval_run.get("overall_score", 0)
        history.append({"iteration": iteration, "score": score})
        
        criteria = audit_result.get("criteria_report", {})
        if criteria.get("mature"):
            print("\n✅ Success criteria met!")
            break
        
        if len(history) >= 3 and len(set(h["score"] for h in history[-3:])) == 1:
            print(f"\n⚠️ Converged at {score}%")
            break
        
        failures = [r for r in eval_run.get("results", []) if not r.get("passed")]
        if failures:
            for failure in failures[:5]:
                builder.improve_from_failure(failure)
    
    history_path = project_dir / "reports" / "improvement_loop_history.yaml"
    history_path.write_text(yaml.dump(history, default_flow_style=False, sort_keys=False))


def main():
    parser = argparse.ArgumentParser(description="BQL Skill — Pipeline Orchestrator")
    parser.add_argument("--agent", type=int, choices=[1, 2, 3, 4])
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--max-iterations", type=int, default=10)
    args = parser.parse_args()
    
    project_dir = PROJECT_ROOT
    print(f"BQL Skill Pipeline — {project_dir}")
    
    if args.loop:
        run_improvement_loop(project_dir, args.max_iterations)
    elif args.agent == 1:
        run_agent1(project_dir)
    elif args.agent == 2:
        run_agent2(project_dir)
    elif args.agent == 3:
        run_agent3(project_dir)
    elif args.agent == 4:
        run_agent4(project_dir)
    else:
        run_full_pipeline(project_dir)


if __name__ == "__main__":
    main()
