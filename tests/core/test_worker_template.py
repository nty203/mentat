from __future__ import annotations

import os

import pytest

from mentat.core.worker_template import WorkerTemplateStore


@pytest.fixture
def templates_dir(tmp_path: str) -> str:
    d = str(tmp_path)
    with open(os.path.join(d, "research.md"), "w") as f:
        f.write("---\ndescription: Research template\n---\n\nDo research.")
    return d


def test_list(templates_dir: str) -> None:
    store = WorkerTemplateStore(templates_dir)
    assert "research" in store.list()


def test_load_parses_frontmatter(templates_dir: str) -> None:
    store = WorkerTemplateStore(templates_dir)
    tmpl = store.load("research")
    assert tmpl.description == "Research template"
    assert "Do research." in tmpl.body


def test_list_empty_dir(tmp_path: str) -> None:
    store = WorkerTemplateStore(str(tmp_path))
    assert store.list() == []
