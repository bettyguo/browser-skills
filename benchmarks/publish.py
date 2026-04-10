"""Convert a benchmarks/results.json into a GitHub-Pages-ready static page.

Outputs benchmarks/_site/index.html (committed to gh-pages by CI) with:
  - aggregate banner (matcher recall, success rate, when it ran)
  - per-site table: matcher picks + per-skill status & timing
  - per-skill summary table: success rate, deterministic rate, p50 wall-time

Honest numbers only. If a row failed, it shows red — we don't hide it.
"""

from __future__ import annotations

import argparse
import html
import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _format_aggregate(report: dict[str, Any]) -> str:
    agg = report.get("aggregate", {})
    ran_at = datetime.fromtimestamp(report.get("ran_at", 0), tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC"
    )
    mode = report.get("mode", "?")
    fields = [
        ("mode", mode),
        ("ran_at", ran_at),
        ("python", report.get("python_version", "?")),
        ("sites", report.get("n_sites", 0)),
        ("skills", report.get("n_skills", 0)),
    ]
    fields.extend(agg.items())
    cells = "".join(
        f"<dt>{html.escape(str(k))}</dt><dd>{html.escape(str(v))}</dd>" for k, v in fields
    )
    return f"<dl class='agg'>{cells}</dl>"


def _format_per_site(report: dict[str, Any]) -> str:
    rows: list[str] = []
    for site in report.get("sites", []):
        site_id = html.escape(site.get("site_id", ""))
        url = html.escape(site.get("url", ""))
        matcher_top = ", ".join(html.escape(n) for n in site.get("matcher_top", [])) or "—"
        skill_results = site.get("skill_results", {})
        per_skill = []
        for sname, sresult in skill_results.items():
            status = sresult.get("status", "?")
            det = "det" if sresult.get("deterministic") else "vis"
            ms = sresult.get("duration_ms", 0)
            cls = "ok" if status == "success" else "fail"
            per_skill.append(
                f"<span class='pill {cls}' title='{html.escape(sname)}'>"
                f"{html.escape(sname)} · {status} · {det} · {ms}ms</span>"
            )
        error = site.get("error")
        if error:
            per_skill.append(
                f"<span class='pill err'>error: {html.escape(error)[:120]}</span>"
            )
        rows.append(
            f"<tr><td><code>{site_id}</code></td>"
            f"<td><a href='{url}'>{url}</a></td>"
            f"<td>{matcher_top}</td>"
            f"<td>{''.join(per_skill) if per_skill else '—'}</td></tr>"
        )
    return (
        "<table class='sites'><thead><tr>"
        "<th>site</th><th>url</th><th>matcher top</th><th>skill results</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _format_per_skill(report: dict[str, Any]) -> str:
    """Aggregate per-skill across all sites."""
    stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"runs": 0, "ok": 0, "det": 0, "ms": []}
    )
    for site in report.get("sites", []):
        for sname, sresult in site.get("skill_results", {}).items():
            stats[sname]["runs"] += 1
            if sresult.get("status") == "success":
                stats[sname]["ok"] += 1
                if sresult.get("deterministic"):
                    stats[sname]["det"] += 1
            ms = sresult.get("duration_ms")
            if isinstance(ms, (int, float)):
                stats[sname]["ms"].append(ms)

    rows: list[str] = []
    for sname in sorted(stats):
        s = stats[sname]
        runs = s["runs"]
        ok = s["ok"]
        det = s["det"]
        ms_list = s["ms"]
        success_pct = (100.0 * ok / runs) if runs else 0.0
        det_pct = (100.0 * det / ok) if ok else 0.0
        p50 = int(statistics.median(ms_list)) if ms_list else 0
        p99 = max(ms_list) if ms_list else 0
        rows.append(
            f"<tr><td><code>{html.escape(sname)}</code></td>"
            f"<td>{runs}</td>"
            f"<td>{success_pct:.0f}%</td>"
            f"<td>{det_pct:.0f}%</td>"
            f"<td>{p50}ms</td>"
            f"<td>{p99}ms</td></tr>"
        )
    return (
        "<table class='skills'><thead><tr>"
        "<th>skill</th><th>runs</th><th>success</th><th>deterministic</th>"
        "<th>p50</th><th>p99</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


_STYLE = """\
body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 1100px;
       margin: 2rem auto; padding: 0 1rem; color: #222; }
h1 { margin-bottom: 0.2em; }
small { color: #555; }
dl.agg { display: grid; grid-template-columns: max-content 1fr;
         gap: 0.2rem 1rem; background: #f6f6f6; padding: 0.8rem 1rem;
         border-radius: 6px; }
dl.agg dt { font-weight: 600; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
th, td { border-bottom: 1px solid #eee; padding: 0.4rem 0.6rem; text-align: left;
         vertical-align: top; }
th { background: #fafafa; }
.pill { display: inline-block; padding: 0.15rem 0.5rem; margin: 0.1rem 0.2rem 0.1rem 0;
        border-radius: 999px; font-size: 0.8rem; }
.pill.ok { background: #e6f5ea; color: #1d6b30; }
.pill.fail { background: #fbe7e7; color: #a01717; }
.pill.err { background: #ffefcc; color: #7a4d00; }
code { font-family: ui-monospace, Menlo, Consolas, monospace; }
"""


def render(report: dict[str, Any]) -> str:
    return f"""\
<!DOCTYPE html>
<html lang='en'><head>
<meta charset='utf-8'>
<title>browser-skills benchmark</title>
<style>{_STYLE}</style>
</head><body>
<h1>browser-skills benchmark</h1>
<small>Auto-generated from <code>benchmarks/results.json</code>.
Honest numbers, including failures. See
<a href='https://github.com/browser-skills/browser-skills'>repo</a> and
<a href='https://github.com/browser-skills/browser-skills/blob/main/docs/benchmarks.md'>methodology</a>.</small>
<h2>aggregate</h2>
{_format_aggregate(report)}
<h2>per skill</h2>
{_format_per_skill(report)}
<h2>per site</h2>
{_format_per_site(report)}
</body></html>
"""


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Render benchmark results to HTML")
    p.add_argument("--input", default="benchmarks/results.json")
    p.add_argument("--output", default="benchmarks/_site/index.html")
    args = p.parse_args(argv)

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"missing {in_path}; run `python benchmarks/run.py` first")
        return 1

    report = _read(in_path)
    html_out = render(report)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_out, encoding="utf-8")
    print(f"wrote {out_path} ({len(html_out)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
