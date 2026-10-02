"""Progress of a survey's summaries, read from the `summaries` queue.

`Summary.http_status` is both the state of the queue and the result: 0 is
pending, 200 is done, anything else is an error. This module is the only place
that knows it; callers get counts and an estimated time left.

The queue is shared by every survey and served by one daemon, so the estimate
counts every pending job of the queue, not only the survey's own.
"""

from dataclasses import dataclass
from typing import Optional

from sqlmodel import Session, func, select

from oceens.models import Summary

# Typical duration of one job (Design Document, assumption B).
SECONDS_PER_JOB = 20

STATUS_PENDING = 0
STATUS_DONE = 200


@dataclass(frozen=True)
class SurveyProgress:
    done: int
    pending: int
    errors: int
    estimated_seconds_left: Optional[int]


def survey_progress(session: Session, survey_id: int) -> SurveyProgress:
    """Return the progress of one survey's summaries, with an estimate.

    The estimate is absent when the survey has nothing pending. It reads no
    clock: it is the pending jobs of the whole queue times SECONDS_PER_JOB.
    """
    rows = session.exec(
        select(Summary.http_status, func.count(Summary.summary_id)).where(
            Summary.survey_id == survey_id
        ).group_by(Summary.http_status)
    ).all()

    pending = sum(count for status, count in rows if status == STATUS_PENDING)
    done = sum(count for status, count in rows if status == STATUS_DONE)
    errors = sum(
        count for status, count in rows if status not in (STATUS_PENDING, STATUS_DONE)
    )

    estimated_seconds_left = None
    if pending:
        queue_pending = session.exec(
            select(func.count(Summary.summary_id)).where(
                Summary.http_status == STATUS_PENDING
            )
        ).one()
        estimated_seconds_left = queue_pending * SECONDS_PER_JOB

    return SurveyProgress(done, pending, errors, estimated_seconds_left)
