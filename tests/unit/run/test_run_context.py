from datetime import timedelta
import threading

from tests.unit.helpers import make_run_context, make_bronze_result


def test_run_context_bronze_counters_and_status() -> None:
    ctx = make_run_context()
    result = make_bronze_result()
    ctx.result_bronze_pass(result)
    ctx.result_bronze_error(result, e="FAILED")
    ctx.silver_dto_count = 1
    assert ctx.bronze_files_passed == 1
    assert ctx.bronze_files_failed == 1
    assert ctx.resolve_status() == "partial"


def test_run_context_resolve_status_success() -> None:
    ctx = make_run_context()
    ctx.silver_dto_count = 2
    assert ctx.resolve_status() == "success"


def test_run_context_formatted_elapsed_time_multiple_units() -> None:
    ctx = make_run_context()
    ctx.finished_at = ctx.started_at + timedelta(minutes=1, seconds=30)
    assert ctx.formatted_elapsed_time == "1m 30s"


def test_run_context_thread_safe_counter_updates() -> None:
    """Test that RunContext counter updates are thread-safe under concurrent access."""
    ctx = make_run_context()
    num_threads = 10
    iterations_per_thread = 100

    def worker_pass():
        """Worker that increments bronze_files_passed counter."""
        for _ in range(iterations_per_thread):
            result = make_bronze_result()
            ctx.result_bronze_pass(result)

    def worker_error():
        """Worker that increments bronze_files_failed counter."""
        for _ in range(iterations_per_thread):
            result = make_bronze_result()
            ctx.result_bronze_error(result, e="TEST ERROR")

    # Create and start threads
    threads = []
    for _ in range(num_threads // 2):
        threads.append(threading.Thread(target=worker_pass))
        threads.append(threading.Thread(target=worker_error))

    for thread in threads:
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Verify counters (should be exactly num_threads/2 * iterations_per_thread each)
    expected_count = (num_threads // 2) * iterations_per_thread
    assert ctx.bronze_files_passed == expected_count, f"Expected {expected_count}, got {ctx.bronze_files_passed}"
    assert ctx.bronze_files_failed == expected_count, f"Expected {expected_count}, got {ctx.bronze_files_failed}"
    # Also verify list lengths match (thread-safe append)
    assert len(ctx.bronze_injest_items) == num_threads * iterations_per_thread
