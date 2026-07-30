from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import TransactionTestCase

from ..models import Attempt, DeliveryAssignment
from ..services import (
    activate_delivery,
    assign_delivery,
    create_delivery,
    start_attempt,
)
from .support import AssessmentFixtureMixin


class AssessmentConcurrencyTests(AssessmentFixtureMixin, TransactionTestCase):
    reset_sequences = True

    def test_concurrent_start_materializes_exactly_one_attempt(self) -> None:
        context = self.assessment_context(with_learning=True)
        delivery = create_delivery(
            actor=context["owner"],
            organization=context["organization"],
            assessment_version=context["assessment_version"],
            name="Entrega concurrente",
            course_release=context["release"],
        )
        delivery = activate_delivery(
            actor=context["owner"],
            delivery=delivery,
            expected_version=delivery.lock_version,
        )
        assignment = assign_delivery(
            actor=context["owner"],
            delivery=delivery,
            release_assignment=context["enrollment"].current_release_assignment,
        )
        learner_id = context["learner"].pk
        barrier = threading.Barrier(2)

        def worker() -> str:
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                attempt = start_attempt(
                    actor=get_user_model().objects.get(pk=learner_id),
                    assignment=DeliveryAssignment.objects.get(pk=assignment.pk),
                )
                return str(attempt.id)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            attempt_ids = list(executor.map(lambda _: worker(), range(2)))
        self.assertEqual(attempt_ids[0], attempt_ids[1])
        self.assertEqual(
            Attempt.objects.filter(delivery_assignment=assignment).count(), 1
        )
