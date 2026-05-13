"""Runs a Skill against a PageLike and records a Trace.

The deterministic recipe runs first. If it fails and a VisionAdapter
is configured and the budget allows, a single vision call may rescue
the run. When the skill opts into success criteria evaluation, the
parsed criteria are checked against the post-recipe page state.
"""
from __future__ import annotations

import time
from typing import Any

from browser_skills import config
from browser_skills.criteria import evaluate_criterion
from browser_skills.primitives import REGISTRY, PageLike, StepFailed
from browser_skills.skill import Skill, SkillResult, Step
from browser_skills.trace import Trace


class Runner:
    """Execute skills. Stateless across calls; safe to reuse."""
    async def execute(
        self,
        skill: Skill,
        page: PageLike,
        vars: dict[str, Any] | None = None,
        vision_budget: int | None = None,
    ) -> SkillResult:
        # Snapshot the caller's vars so we can return a clean
        # `extracted` map (only primitive-bound keys) alongside
        # `vars_in` (echo of caller input).
        caller_vars = dict(vars or {})
        vars = dict(caller_vars)
        trace = Trace(
            skill_name=skill.name,
            skill_version=skill.version,
            url=getattr(page, "url", None),
            sensitive=bool(skill.metadata.get("sensitive", False)),
        )
        trace.record_event("recipe_start", step_count=len(skill.recipe.steps))

        deterministic = True
        model_calls = 0
        tokens = 0
        steps_executed = 0
        warnings: list[str] = []
        budget = (
            vision_budget if vision_budget is not None else skill.max_vision_calls
        )

        t_start = time.perf_counter()
        failure_reason: str | None = None

        for index, step in enumerate(skill.recipe.steps, start=1):
            step_t = time.perf_counter()
            outcome, detail = await self._run_step(
                step, page, vars
            )
            step_ms = int((time.perf_counter() - step_t) * 1000)
            trace.record_step(index, step.verb, step.args, outcome, step_ms, detail)
            steps_executed += 1
            if outcome != "ok":
                failure_reason = detail.get("error") if detail else "step_failed"
                break

        # Initial pass/fail from whether the recipe completed. The
        # success-criteria block below can still downgrade a completed
        # run to "failed" if a decidable criterion is violated.
        criteria_pass = failure_reason is None

        if not criteria_pass and budget > 0 and config.vision_adapter is not None:
            trace.record_event("vision_fallback_attempt", budget=budget)
            v_result = await self._invoke_vision(page, skill, vars, trace)
            if v_result["used"]:
                deterministic = False
                model_calls += 1
                tokens += int(v_result.get("tokens", 0))
                # Vision rescued the recipe. The criteria loop below
                # still runs for opt-in skills, so vision can't mask a
                # criterion violation.
                criteria_pass = True
                failure_reason = None
        elif not criteria_pass and budget > 0 and config.vision_adapter is None:
            warnings.append("no_vision_adapter_configured")

        # If the skill opts in, check parsed success criteria against
        # the post-recipe page. A decidable-False turns the run failed
        # even if every step succeeded. Unknown predicates soft-pass.
        if criteria_pass and skill.evaluate_success_criteria and skill.success_criteria:
            for criterion in skill.success_criteria:
                eval_errors: list[str] = []
                result = await evaluate_criterion(
                    page, vars, criterion, error_sink=eval_errors
                )
                trace.record_event(
                    "criterion_evaluated",
                    text=criterion.raw_text,
                    result=result,
                    errors=eval_errors,
                )
                # Surface eval errors as warnings so authors can debug
                # broken predicates without reading the trace.
                for err in eval_errors:
                    warnings.append(f"criterion eval error: {err}")
                if result is False:
                    criteria_pass = False
                    failure_reason = f"success criterion violated: {criterion.raw_text}"
                    break
                if result is None and not eval_errors:
                    warnings.append(
                        f"criterion soft-passed (unknown predicate): {criterion.raw_text}"
                    )

        total_ms = int((time.perf_counter() - t_start) * 1000)
        trace.record_event(
            "recipe_end",
            status="success" if criteria_pass else "failed",
            deterministic_path=deterministic,
        )

        # `extracted`: keys the primitives added or changed.
        # `vars_in`: unmodified caller input.
        extracted = {
            k: v
            for k, v in vars.items()
            if k not in caller_vars or caller_vars[k] != v
        }
        return SkillResult(
            skill=skill.name,
            version=skill.version,
            status="success" if criteria_pass else "failed",
            deterministic_path=deterministic,
            duration_ms=total_ms,
            model_calls=model_calls,
            tokens_used=tokens,
            trace_id=trace.trace_id,
            extracted=extracted,
            vars_in=caller_vars,
            steps_executed=steps_executed,
            failure_reason=failure_reason,
            warnings=warnings,
        )

    async def _run_step(
        self,
        step: Step,
        page: PageLike,
        vars: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        fn = REGISTRY.get(step.verb)
        if fn is None:
            return ("fail", {"error": f"unknown verb: {step.verb}"})
        kwargs = dict(step.args)
        # `vars` is threaded into primitives that bind variables (extract_*).
        kwargs.setdefault("vars", vars)
        try:
            detail = await fn(page, **kwargs)
            return ("ok", detail)
        except StepFailed as e:
            return ("fail", {"error": str(e)})
        except Exception as e:  # noqa: BLE001
            return ("fail", {"error": f"{type(e).__name__}: {e}"})

    async def _invoke_vision(
        self,
        page: PageLike,
        skill: Skill,
        vars: dict[str, Any],
        trace: Trace,
    ) -> dict[str, Any]:
        vision_fn = REGISTRY["vision"]
        try:
            detail = await vision_fn(
                page,
                intent=skill.description,
                allowed_actions=skill.allowed_tools,
                vars=vars,
            )
            trace.record_event("vision_fallback_action_proposed", **detail)
            proposed = detail.get("action_proposed", {})
            verb = proposed.get("verb")
            args = proposed.get("args", {})
            fn = REGISTRY.get(verb) if verb else None
            if fn is None:
                trace.record_event("vision_fallback_action_invalid", verb=verb)
                return {"used": False}
            try:
                await fn(page, **args, vars=vars)
            except StepFailed as e:
                trace.record_event("vision_fallback_action_failed", error=str(e))
                return {"used": False}
            return {
                "used": True,
                "tokens": detail.get("tokens_in", 0) + detail.get("tokens_out", 0),
            }
        except StepFailed as e:
            trace.record_event("vision_fallback_unavailable", error=str(e))
            return {"used": False}
