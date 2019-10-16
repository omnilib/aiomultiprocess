# Copyright 2018 John Reese
# Licensed under the MIT license

from unittest import TestCase

import aiomultiprocess as amp


class SchedulerTest(TestCase):
    def test_roundrobin_scheduler_one(self):
        scheduler = amp.RoundRobin()
        qid = scheduler.register_queue(object())
        scheduler.register_process(qid)

        for i in range(5):
            self.assertEqual(scheduler.schedule_task(i, object, tuple(), {}), qid)

    def test_roundrobin_scheduler_two(self):
        scheduler = amp.RoundRobin()
        q1 = scheduler.register_queue(object())
        q2 = scheduler.register_queue(object())
        scheduler.register_process(q1)
        scheduler.register_process(q2)

        for i in range(5):
            self.assertEqual(scheduler.schedule_task(i, object, tuple(), {}), q1)
            self.assertEqual(scheduler.schedule_task(i, object, tuple(), {}), q2)
