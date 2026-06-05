#!/usr/bin/env python3
"""
BQL Skill Research Project — Main Pipeline Orchestrator

Runs the full multi-agent pipeline:
  Agent 1 → Corpus Builder (collect data)
  Agent 2 → Skill Builder (create BQL skill)
  Agent 3 → Independent Auditor (evaluate)
  Agent 4 → Adversarial User (find weaknesses)

Usage:
  python run_pipeline.py              # Full pipeline
  python run_pipeline.py --agent 1    # Only Agent 1
  python run_pipeline.py --agent 2    # Only Agent 2
  python run_pipeline.py --agent 3    # Only Agent 3
  python run_pipeline.py --agent 4    # Only Agent 4
  python run_pipeline.py --loop       # Continuous improvement loop
"""

import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone

import yaml


def resolve_path():
    """Resolve to the automation directory for imports."""
    return Path(__file__).resolve().parent / "automation"


def run_agent1(project_dir: Path) -> dict:
    """Run Agent 1 — Corpus Builder."""
    print("\n" + "=" * 60)
    print("AGENT 1: CORPUS BUILDER")
    print("=" * 60)
    sys.path.insert(0, str(project_dir / "automation"))
    from agent1.corpus_builder import CorpusBuilder
    builder = CorpusBuilder()
    return builder.run_full_corpus_build()


def run_agent2(project_dir: Path) -> dict:
    """Run Agent 2 — Skill Builder."""
    print("\n" + "=" * 60)
    print("AGENT 2: SKILL BUILDER")
    print("=" * 60)
    sys.path.insert(0, str(project_dir / "automation"))
    from agent2.skill_builder import SkillBuilder
    builder = SkillBuilder()
    return builder.run_full_skill_build()


def run_agent3(project_dir: Path, query_map: dict = None) -> dict:
    """Run Agent 3 — Independent Auditor."""
    print("\n" + "=" * 60)
    print("AGENT 3: INDEPENDENT AUDITOR")
    print("=" * 60)
    sys.path.insert(0, str(project_dir / "automation"))
    from agent3.auditor import Auditor
    auditor = Auditor()
    return auditor.run_full_audit(query_map)


def run_agent4(project_dir: Path) -> dict:
    """Run Agent 4 — Adversarial User."""
    print("\n" + "=" * 60)
    print("AGENT 4: ADVERSARIAL USER")
    print("=" * 60)
    sys.path.insert(0, str(project_dir / "automation"))
    from agent4.adversarial_user import AdversarialUser
    adversary = AdversarialUser()
    return adversary.run_adversarial_generation()


def load_query_map(skill_dir: Path) -> dict:
    """Load query responses from skill outputs (for evaluation)."""
    query_map = {}
    
    # Try loading from query patterns as a fallback
    patterns_dir = skill_dir / "query_patterns"
    if patterns_dir.exists():
        for pf in patterns_dir.glob("*.yaml"):
            if pf.name == "index.yaml":
                continue
            try:
                pattern = yaml.safe_load(pf.read_text())
                # Generate a sample query from each pattern
                template = pattern.get("query_template", "")
                if template:
                    # Store pattern info
                    pass
            except Exception:
                pass

    return query_map


def run_full_pipeline(project_dir: Path):
    """Run the complete pipeline: Agent 1 → 2 → 3 → 4."""
    start_time = time.time()
    
    results = {
        "pipeline_run": datetime.now(timezone.utc).isoformat(),
        "agents": {},
    }

    # Agent 1: Build corpus
    agent1_result = run_agent1(project_dir)
    results["agents"]["agent1"] = agent1_result

    # Agent 2: Build skill
    agent2_result = run_agent2(project_dir)
    results["agents"]["agent2"] = agent2_result

    # Agent 3: Evaluate (with generated queries since no LLM is available)
    agent3_result = run_agent3(project_dir)
    results["agents"]["agent3"] = agent3_result

    # Agent 4: Generate adversarial questions
    agent4_result = run_agent4(project_dir)
    results["agents"]["agent4"] = agent4_result

    # Pipeline summary
    elapsed = time.time() - start_time
    results["elapsed_seconds"] = round(elapsed, 1)

    # Save pipeline run report
    reports_dir = project_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = reports_dir / f"pipeline_run_{run_id}.yaml"
    report_path.write_text(yaml.dump(results, default_flow_style=False, sort_keys=False))

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Total time: {elapsed:.1f}s")
    print(f"Report: {report_path}")

    # Print score summary
    agent3 = results["agents"].get("agent3", {})
    eval_run = agent3.get("evaluation_run", {})
    if eval_run:
        print(f"\nOverall Score: {eval_run.get('overall_score', 'N/A')}%")
        print(f"Passed: {eval_run.get('passed_tests', 0)}/{eval_run.get('total_tests', 0)}")

    return results


def run_improvement_loop(project_dir: Path, max_iterations: int = 10):
    """Run a continuous improvement loop: Agent 3 → Agent 2 → Agent 3."""
    print("\n" + "=" * 60)
    print("CONTINUOUS IMPROVEMENT LOOP")
    print(f"Max iterations: {max_iterations}")
    print("=" * 60)

    sys.path.insert(0, str(project_dir / "automation"))
    from agent3.auditor import Auditor
    from agent2.skill_builder import SkillBuilder

    auditor = Auditor()
    builder = SkillBuilder()

    history = []

    for iteration in range(1, max_iterations + 1):
        print(f"\n{'=' * 40}")
        print(f"Iteration {iteration}/{max_iterations}")
        print(f"{'=' * 40}")

        # Evaluate
        audit_result = auditor.run_full_audit()
        eval_run = audit_result.get("evaluation_run", {})
        score = eval_run.get("overall_score", 0)

        history.append({
            "iteration": iteration,
            "score": score,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        print(f"\nScore: {score}%")

        # Check success criteria
        criteria = audit_result.get("criteria_report", {})
        if criteria.get("mature"):
            print("\n✅ Success criteria met! Pipeline is mature.")
            break

        # Check convergence
        if len(history) >= 3:
            last_3 = [h["score"] for h in history[-3:]]
            if len(set(last_3)) == 1:
                print(f"\n⚠️ Score converged at {score}%. Stopping.")
                break

        # Improve based on failures
        results = eval_run.get("results", [])
        failures = [r for r in results if not r.get("passed")]
        
        if failures:
            print(f"\nAnalyzing {len(failures)} failures...")
            for failure in failures[:5]:  # Process top 5 failures
                builder.improve_from_failure(failure)
        else:
            print("\nNo failures to improve. Regenerating adversarial tests...")
            run_agent4(project_dir)

        # Small delay between iterations
        time.sleep(0.5)

    # Save loop history
    history_path = project_dir / "reports" / "improvement_loop_history.yaml"
    history_path.write_text(yaml.dump(history, default_flow_style=False, sort_keys=False))
    print(f"\nLoop history saved to: {history_path}")


def main():
    parser = argparse.ArgumentParser(
        description="BQL Skill Research Project — Pipeline Orchestrator"
    )
    parser.add_argument(
        "--agent", type=int, choices=[1, 2, 3, 4],
        help="Run only a specific agent (1-4)"
    )
    parser.add_argument(
        "--loop", action="store_true",
        help="Run continuous improvement loop"
    )
    parser.add_argument(
        "--max-iterations", type=int, default=10,
        help="Max iterations for the improvement loop"
    )
    parser.add_argument(
        "--project-dir", type=str, default=None,
        help="Project root directory"
    )

    args = parser.parse_args()

    if args.project_dir:
        project_dir = Path(args.project_dir).resolve()
    else:
        project_dir = Path(__file__).resolve().parent

    print("BQL Skill Research Project")
    print(f"Project directory: {project_dir}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")

    if args.loop:
        run_improvement_loop(project_dir, args.max_iterations)
        return

    if args.agent == 1:
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
