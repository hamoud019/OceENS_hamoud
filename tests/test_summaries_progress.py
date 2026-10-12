"""Progression des synthèses d'un sondage, lue par l'interface du module.

La file `summaries` est partagée par tous les sondages : l'estimation compte
chaque synthèse en attente, quel que soit son sondage.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from oceens.models import Summary
from oceens.services.summaries_progress import survey_progress


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def add_pending(session, survey_id, count):
    for _ in range(count):
        session.add(Summary(survey_id=survey_id, http_status=0))
    session.commit()


def test_estimate_counts_every_pending_job_of_the_queue(session):
    for survey_id in range(1, 11):
        add_pending(session, survey_id, 45)

    progress = survey_progress(session, survey_id=1)

    assert progress.pending == 45
    assert progress.estimated_seconds_left == 9000
