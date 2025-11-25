"""HTML report generation."""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from zotwatch.core.models import RankedWork

logger = logging.getLogger(__name__)

# Fallback template when no external template is available
_FALLBACK_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ZotWatch Report - {{ generated_at.strftime('%Y-%m-%d') }}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    .summary-expand { transition: max-height 0.3s ease-out; overflow: hidden; }
    .summary-expand.collapsed { max-height: 0; }
    .summary-expand.expanded { max-height: 2000px; }
  </style>
</head>
<body class="bg-gray-50 min-h-screen">
  <header class="bg-white shadow-sm border-b">
    <div class="max-w-6xl mx-auto px-4 py-6">
      <h1 class="text-2xl font-bold text-gray-900">ZotWatch Recommendations</h1>
      <p class="text-sm text-gray-500 mt-1">{{ works|length }} papers | Generated {{ generated_at.strftime('%B %d, %Y at %H:%M UTC') }}</p>
    </div>
  </header>

  <main class="max-w-6xl mx-auto px-4 py-8">
    <div class="mb-6 flex items-center justify-end gap-2">
      <button onclick="expandAll()" class="px-3 py-1 text-sm text-blue-600 hover:text-blue-800 border border-blue-200 rounded">Expand All</button>
      <button onclick="collapseAll()" class="px-3 py-1 text-sm text-blue-600 hover:text-blue-800 border border-blue-200 rounded">Collapse All</button>
    </div>

    <div class="grid gap-6">
      {% for work in works %}
      <article class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div class="p-6">
          <div class="flex items-start justify-between mb-3">
            <div class="flex-1">
              <div class="flex items-center gap-2 mb-2">
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                  {% if work.label == 'must_read' %}bg-green-100 text-green-800
                  {% elif work.label == 'consider' %}bg-yellow-100 text-yellow-800
                  {% else %}bg-gray-100 text-gray-800{% endif %}">
                  {{ work.label | replace('_', ' ') | title }}
                </span>
                <span class="text-xs text-gray-500">Score: {{ '%.3f'|format(work.score) }}</span>
                <span class="text-xs text-gray-400">|</span>
                <span class="text-xs text-gray-500">{{ work.source }}</span>
              </div>
              <h2 class="text-lg font-semibold text-gray-900 leading-tight">
                <a href="{{ work.url or '#' }}" target="_blank" class="hover:text-blue-600">
                  {{ work.title }}
                </a>
              </h2>
            </div>
            <div class="ml-4 text-right text-sm text-gray-500">
              <div>{{ work.published.strftime('%Y-%m-%d') if work.published else 'Unknown' }}</div>
              <div class="text-xs">{{ work.venue or 'Unknown venue' }}</div>
            </div>
          </div>

          <p class="text-sm text-gray-600 mb-3">
            {{ work.authors[:5] | join(', ') }}{% if work.authors|length > 5 %} et al.{% endif %}
          </p>

          {% if work.summary %}
          <div class="bg-blue-50 rounded-lg p-4 mb-3">
            <h3 class="text-sm font-medium text-blue-900 mb-2 flex items-center">
              <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
              </svg>
              AI Summary
            </h3>
            <ul class="text-sm text-blue-800 space-y-1 list-disc list-inside">
              <li><strong>Question:</strong> {{ work.summary.bullets.research_question }}</li>
              <li><strong>Method:</strong> {{ work.summary.bullets.methodology }}</li>
              <li><strong>Findings:</strong> {{ work.summary.bullets.key_findings }}</li>
              <li><strong>Innovation:</strong> {{ work.summary.bullets.innovation }}</li>
              {% if work.summary.bullets.relevance_note %}
              <li><strong>Relevance:</strong> {{ work.summary.bullets.relevance_note }}</li>
              {% endif %}
            </ul>

            <div class="mt-3">
              <button id="btn-{{ loop.index }}" onclick="toggleSummary({{ loop.index }})"
                      class="text-xs text-blue-600 hover:text-blue-800 font-medium">
                Show Details
              </button>
              <div id="summary-{{ loop.index }}" class="summary-expand collapsed mt-2">
                <div class="bg-white rounded p-3 text-sm text-gray-700 space-y-2">
                  <p><strong>Background:</strong> {{ work.summary.detailed.background }}</p>
                  <p><strong>Methodology:</strong> {{ work.summary.detailed.methodology_details }}</p>
                  <p><strong>Results:</strong> {{ work.summary.detailed.results }}</p>
                  <p><strong>Limitations:</strong> {{ work.summary.detailed.limitations }}</p>
                  {% if work.summary.detailed.future_directions %}
                  <p><strong>Future Directions:</strong> {{ work.summary.detailed.future_directions }}</p>
                  {% endif %}
                  <p class="text-blue-700"><strong>Why Relevant:</strong> {{ work.summary.detailed.relevance_to_interests }}</p>
                </div>
              </div>
            </div>
          </div>
          {% elif work.abstract %}
          <p class="text-sm text-gray-700 mb-3 line-clamp-4">{{ work.abstract }}</p>
          {% endif %}

          <div class="mt-4 pt-4 border-t border-gray-100">
            <div class="flex flex-wrap gap-4 text-xs text-gray-500">
              <span>Similarity: {{ '%.2f'|format(work.similarity) }}</span>
              <span>Recency: {{ '%.2f'|format(work.recency_score) }}</span>
              {% if work.journal_sjr %}
              <span>SJR: {{ '%.2f'|format(work.journal_sjr) }}</span>
              {% endif %}
              {% if work.author_bonus > 0 %}
              <span class="text-green-600">Author Match</span>
              {% endif %}
              {% if work.venue_bonus > 0 %}
              <span class="text-green-600">Venue Match</span>
              {% endif %}
            </div>
          </div>
        </div>
      </article>
      {% endfor %}
    </div>
  </main>

  <footer class="bg-white border-t mt-12">
    <div class="max-w-6xl mx-auto px-4 py-4 text-center text-sm text-gray-500">
      Generated by <a href="https://github.com/zotwatch/zotwatch" class="text-blue-600 hover:underline">ZotWatch</a>
    </div>
  </footer>

  <script>
    function toggleSummary(id) {
      const el = document.getElementById('summary-' + id);
      const btn = document.getElementById('btn-' + id);
      if (el.classList.contains('collapsed')) {
        el.classList.remove('collapsed');
        el.classList.add('expanded');
        btn.textContent = 'Hide Details';
      } else {
        el.classList.remove('expanded');
        el.classList.add('collapsed');
        btn.textContent = 'Show Details';
      }
    }
    function expandAll() {
      document.querySelectorAll('.summary-expand').forEach(el => {
        el.classList.remove('collapsed');
        el.classList.add('expanded');
      });
      document.querySelectorAll('[id^="btn-"]').forEach(btn => btn.textContent = 'Hide Details');
    }
    function collapseAll() {
      document.querySelectorAll('.summary-expand').forEach(el => {
        el.classList.remove('expanded');
        el.classList.add('collapsed');
      });
      document.querySelectorAll('[id^="btn-"]').forEach(btn => btn.textContent = 'Show Details');
    }
  </script>
</body>
</html>"""


def render_html(
    works: List[RankedWork],
    output_path: Path | str,
    *,
    template_dir: Optional[Path] = None,
    template_name: str = "report.html",
) -> Path:
    """Render HTML report from ranked works.

    Args:
        works: Ranked works to include
        output_path: Path to write HTML file
        template_dir: Directory containing templates
        template_name: Name of template file

    Returns:
        Path to written HTML file
    """
    generated_at = datetime.utcnow()

    # Try to load external template
    if template_dir and (template_dir / template_name).exists():
        env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )
        template = env.get_template(template_name)
    else:
        # Use fallback template
        env = Environment(autoescape=select_autoescape(["html", "xml"]))
        template = env.from_string(_FALLBACK_TEMPLATE)

    rendered = template.render(
        works=works,
        generated_at=generated_at,
    )

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")
    logger.info("Wrote HTML report with %d items to %s", len(works), path)
    return path


__all__ = ["render_html"]
