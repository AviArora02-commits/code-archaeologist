"""Integration test: ingest fixture repo and query (requires LLM API key)."""

import os
from pathlib import Path

import pytest
from git import Repo

from app.db import Database
from app.services import cognee_service
from app.services.git_service import (
  enrich_entity_history,
  extract_entities_from_file,
  walk_code_files,
)
from app.services.query_service import QueryService

FIXTURE_REPO = Path(__file__).parent.parent / "fixtures" / "sample_repo"
DATASET = "test_sample_repo_integration"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ingest_and_query_fixture_repo() -> None:
  """Real Cognee round-trip on a tiny local fixture (skipped without API key)."""
  if not os.getenv("OPENAI_API_KEY") and not os.getenv("LLM_API_KEY"):
      pytest.skip("OPENAI_API_KEY or LLM_API_KEY required for integration test")

  await cognee_service.init_cognee()
  try:
      await cognee_service.forget_dataset(DATASET)
  except Exception:
      pass

  files = walk_code_files(FIXTURE_REPO)
  git_repo = Repo(FIXTURE_REPO)
  for f in files:
      entities = extract_entities_from_file(FIXTURE_REPO / f.path, f.path, f.language)
      entities = enrich_entity_history(git_repo, entities, "test", "sample")
      for entity in entities:
          doc = cognee_service.entity_to_document(entity, [], [], "test", "sample")
          await cognee_service.remember_entity(doc, DATASET, run_in_background=False)

  qs = QueryService(Database(":memory:"))
  # Monkeypatch repo lookup
  qs.db.get_repo = lambda _id: {  # type: ignore[method-assign]
      "dataset_name": DATASET,
      "owner": "test",
      "name": "sample",
  }
  result = await qs.ask_why("fake-id", "Why does the add function exist?")
  assert result.answer
  assert len(result.answer) > 0

  await cognee_service.forget_dataset(DATASET)
