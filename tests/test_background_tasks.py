import os
import sys
import threading
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.utils.background_tasks import BackgroundTaskRunner


class BackgroundTaskRunnerTests(unittest.TestCase):
    def setUp(self):
        self.errors = []
        self.runner = BackgroundTaskRunner(
            name="test-background-tasks",
            on_error=lambda name, error: self.errors.append((name, error)),
        )

    def tearDown(self):
        self.runner.wait_for_all(timeout=5)

    def test_task_runs_off_the_calling_thread(self):
        threads = []
        self.runner.submit("probe", lambda: threads.append(threading.current_thread()))

        self.assertTrue(self.runner.wait_for_all(timeout=5))
        self.assertEqual(len(threads), 1)
        self.assertIsNot(threads[0], threading.current_thread())
        self.assertEqual(threads[0].name, "test-background-tasks")

    def test_tasks_run_in_submission_order(self):
        order = []
        for index in range(20):
            self.runner.submit(f"task-{index}", lambda index=index: order.append(index))

        self.assertTrue(self.runner.wait_for_all(timeout=5))
        self.assertEqual(order, list(range(20)))

    def test_failing_task_does_not_stop_the_runner(self):
        order = []

        def fail():
            order.append("fail")
            raise RuntimeError("boom")

        self.runner.submit("failing", fail)
        self.runner.submit("after", lambda: order.append("after"))

        self.assertTrue(self.runner.wait_for_all(timeout=5))
        self.assertEqual(order, ["fail", "after"])
        self.assertEqual(len(self.errors), 1)
        self.assertEqual(self.errors[0][0], "failing")
        self.assertIsInstance(self.errors[0][1], RuntimeError)

    def test_wait_for_all_reports_timeout(self):
        release = threading.Event()
        finished = threading.Event()

        def slow():
            release.wait(timeout=5)
            finished.set()

        self.runner.submit("slow", slow)

        self.assertFalse(self.runner.wait_for_all(timeout=0.05))
        self.assertEqual(self.runner.pending, 1)

        release.set()
        self.assertTrue(self.runner.wait_for_all(timeout=5))
        self.assertTrue(finished.is_set())
        self.assertEqual(self.runner.pending, 0)

    def test_wait_for_all_with_empty_queue_returns_true(self):
        self.assertTrue(self.runner.wait_for_all(timeout=0.01))
        self.assertEqual(self.runner.pending, 0)


if __name__ == "__main__":
    unittest.main()
