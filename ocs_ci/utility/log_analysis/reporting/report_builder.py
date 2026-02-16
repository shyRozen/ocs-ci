"""
Build analysis reports in various formats (JSON, Markdown, HTML).
"""

import json
import logging
import os
from collections import defaultdict

from jinja2 import Environment, FileSystemLoader

from ocs_ci.utility.log_analysis.models import FailureAnalysis, RunAnalysis

logger = logging.getLogger(__name__)

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


class ReportBuilder:
    """Generate analysis reports from RunAnalysis objects."""

    def __init__(self):
        self.jinja_env = Environment(
            loader=FileSystemLoader(TEMPLATES_DIR),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def build(self, run_analysis: RunAnalysis, fmt: str = "markdown") -> str:
        """
        Build a report in the specified format.

        Args:
            run_analysis: The analysis results
            fmt: Output format ("json", "markdown", "html")

        Returns:
            Report as a string
        """
        if fmt == "json":
            return self.build_json(run_analysis)
        elif fmt == "markdown":
            return self.build_markdown(run_analysis)
        elif fmt == "html":
            return self.build_html(run_analysis)
        else:
            raise ValueError(f"Unknown format: {fmt}")

    def build_json(self, run_analysis: RunAnalysis) -> str:
        """Build JSON report."""
        return run_analysis.to_json(indent=2)

    def build_markdown(self, run_analysis: RunAnalysis) -> str:
        """Build Markdown report."""
        template = self.jinja_env.get_template("analysis_report.md.j2")
        context = self._build_template_context(run_analysis)
        return template.render(**context)

    def build_html(self, run_analysis: RunAnalysis) -> str:
        """Build HTML report by converting Markdown to rendered HTML."""
        md_content = self.build_markdown(run_analysis)
        return self._md_to_html(
            md_content, title="OCS-CI Log Analysis Report"
        )

    def _md_to_html(self, md_content: str, title: str = "Report") -> str:
        """
        Convert Markdown to a styled HTML page.

        Uses the markdown library if available, otherwise falls back
        to basic regex-based conversion.
        """
        try:
            import markdown

            html_body = markdown.markdown(
                md_content,
                extensions=["tables", "fenced_code", "codehilite"],
            )
        except ImportError:
            # Fallback: basic conversion for key elements
            import re

            html_body = md_content
            # Escape HTML entities
            html_body = html_body.replace("&", "&amp;")
            html_body = html_body.replace("<", "&lt;")
            html_body = html_body.replace(">", "&gt;")
            # Restore <details>/<summary> tags (used in tracebacks)
            html_body = html_body.replace("&lt;details&gt;", "<details>")
            html_body = html_body.replace("&lt;/details&gt;", "</details>")
            html_body = html_body.replace("&lt;summary&gt;", "<summary>")
            html_body = html_body.replace("&lt;/summary&gt;", "</summary>")
            # Headers
            html_body = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html_body, flags=re.MULTILINE)
            html_body = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html_body, flags=re.MULTILINE)
            html_body = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html_body, flags=re.MULTILINE)
            # Bold
            html_body = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html_body)
            # Inline code
            html_body = re.sub(r"`([^`]+)`", r"<code>\1</code>", html_body)
            # Code blocks
            html_body = re.sub(
                r"```\n(.*?)```",
                r"<pre><code>\1</code></pre>",
                html_body,
                flags=re.DOTALL,
            )
            # Horizontal rules
            html_body = re.sub(r"^---$", "<hr>", html_body, flags=re.MULTILINE)
            # Line breaks
            html_body = html_body.replace("\n", "\n<br>")
            logger.debug(
                "markdown library not installed; using basic HTML conversion. "
                "Install 'markdown' for better rendering: pip install markdown"
            )

        # Post-process: inject colored badges for categories, status, confidence
        import re as _re

        # Category badges
        category_colors = {
            "PRODUCT_BUG": ("#d73a49", "#ffeef0"),
            "TEST_BUG": ("#e36209", "#fff8e1"),
            "INFRA_ISSUE": ("#6f42c1", "#f3e8ff"),
            "FLAKY_TEST": ("#0366d6", "#e1f0ff"),
            "KNOWN_ISSUE": ("#28a745", "#e6ffed"),
            "UNKNOWN": ("#6a737d", "#f1f1f1"),
        }
        for cat, (fg, bg) in category_colors.items():
            badge = (
                f'<span style="background:{bg};color:{fg};padding:2px 8px;'
                f'border-radius:12px;font-weight:600;font-size:13px;">'
                f"{cat}</span>"
            )
            html_body = html_body.replace(f"<strong>{cat}</strong>", badge)

        # Status badges in tables
        status_map = {
            "failed": ("#d73a49", "#ffeef0"),
            "error": ("#b31d28", "#ffeef0"),
            "passed": ("#28a745", "#e6ffed"),
            "skipped": ("#6a737d", "#f1f1f1"),
        }
        for status, (fg, bg) in status_map.items():
            badge = (
                f'<span style="background:{bg};color:{fg};padding:1px 6px;'
                f'border-radius:8px;font-size:12px;">{status}</span>'
            )
            html_body = html_body.replace(
                f"<td>{status}</td>", f"<td>{badge}</td>"
            )

        # Confidence coloring: wrap percentage values
        def _color_confidence(m):
            pct = int(m.group(1))
            if pct >= 75:
                fg, bg = "#28a745", "#e6ffed"
            elif pct >= 50:
                fg, bg = "#e36209", "#fff8e1"
            else:
                fg, bg = "#d73a49", "#ffeef0"
            return (
                f'<span style="background:{bg};color:{fg};padding:1px 6px;'
                f'border-radius:8px;font-weight:600;">{pct}%</span>'
            )
        html_body = _re.sub(
            r"<td>(\d+)%</td>",
            lambda m: f"<td>{_color_confidence(m)}</td>",
            html_body,
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px; margin: 0 auto; padding: 20px;
            color: #24292e; background: #fff; line-height: 1.6;
        }}
        h1 {{
            border-bottom: 3px solid #0366d6; padding-bottom: 10px;
            color: #24292e;
        }}
        h2 {{
            border-bottom: 2px solid #e1e4e8; padding-bottom: 6px;
            margin-top: 36px; color: #0366d6;
        }}
        h3 {{
            margin-top: 28px; padding: 8px 12px;
            background: linear-gradient(90deg, #f6f8fa 0%, #fff 100%);
            border-left: 4px solid #0366d6; border-radius: 0 4px 4px 0;
        }}
        table {{
            border-collapse: collapse; width: 100%; margin: 12px 0;
            font-size: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            border-radius: 6px; overflow: hidden;
        }}
        th, td {{ border: 1px solid #d1d5da; padding: 8px 12px; text-align: left; }}
        th {{
            background: linear-gradient(180deg, #f6f8fa 0%, #eef1f5 100%);
            font-weight: 600; color: #24292e;
        }}
        tr:nth-child(even) {{ background-color: #fafbfc; }}
        tr:hover {{ background-color: #f0f7ff; }}
        code {{
            background-color: #f0f2f4; padding: 2px 6px; border-radius: 3px;
            font-family: 'SFMono-Regular', Consolas, monospace; font-size: 13px;
            color: #e36209;
        }}
        pre {{
            background-color: #282c34; color: #abb2bf; padding: 16px;
            border-radius: 6px; overflow-x: auto; font-size: 13px;
            line-height: 1.45;
        }}
        pre code {{ background: none; padding: 0; color: inherit; }}
        details {{
            margin: 8px 0; border: 1px solid #e1e4e8; border-radius: 6px;
            padding: 8px 12px; background: #fafbfc;
        }}
        details[open] {{ background: #fff; }}
        summary {{
            cursor: pointer; font-weight: 500; color: #0366d6;
        }}
        summary:hover {{ color: #0256b9; }}
        hr {{ border: none; border-top: 2px solid #e1e4e8; margin: 28px 0; }}
        ul {{ padding-left: 24px; }}
        li {{ margin: 4px 0; }}
        a {{ color: #0366d6; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
{html_body}
</body>
</html>"""

    def build_jira_comment(
        self, fa: FailureAnalysis, run_url: str = ""
    ) -> str:
        """
        Build a Jira comment from a failure analysis.

        Args:
            fa: FailureAnalysis to generate comment for
            run_url: URL of the test run

        Returns:
            Jira-formatted comment text
        """
        template = self.jinja_env.get_template("jira_comment.j2")
        return template.render(fa=fa, run_url=run_url)

    def build_trends_report(self, trend_report, fmt: str = "markdown") -> str:
        """
        Build a cross-run trend analysis report.

        Args:
            trend_report: TrendReport from PatternDetector
            fmt: Output format ("json", "markdown", or "html")

        Returns:
            Report as a string
        """
        if fmt == "json":
            return json.dumps(trend_report.to_dict(), indent=2)

        template = self.jinja_env.get_template("trends_report.md.j2")
        md_content = template.render(report=trend_report)

        if fmt == "html":
            return self._md_to_html(
                md_content, title="OCS-CI Cross-Run Trend Analysis"
            )

        return md_content

    def _build_template_context(self, run_analysis: RunAnalysis) -> dict:
        """Build the Jinja2 template context with grouped data."""
        # Group failures by category
        categories = defaultdict(list)
        for fa in run_analysis.failure_analyses:
            categories[fa.category.value].append(fa.test_result.name)

        # Group failures by squad
        squads = defaultdict(list)
        for fa in run_analysis.failure_analyses:
            squad = fa.test_result.squad or "Unknown"
            squads[squad].append(fa.test_result.name)

        return {
            "run": run_analysis,
            "categories": dict(categories),
            "squads": dict(squads),
        }
