from app.utils.logger import get_logger
from app.storage.models import AuditLog, SystemMetric, Feature, Dataset
from app.storage.database import AsyncSessionLocal, engine
from sqlalchemy import text
import time
import asyncio
import pytest

pytestmark = pytest.mark.performance


logger = get_logger("perf_database")


@pytest.mark.asyncio
async def test_concurrent_reads(concurrency=50):
    start = time.perf_counter()

    async def _read():
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))

    await asyncio.gather(*[_read() for _ in range(concurrency)])
    logger.info(f"Completed {concurrency} concurrent reads in {time.perf_counter() - start:.2f}s")


@pytest.mark.asyncio
async def test_concurrent_writes_and_rollbacks(concurrency=20):
    start = time.perf_counter()

    async def _write_and_rollback(i):
        async with AsyncSessionLocal() as session:
            try:
                async with session.begin():
                    metric = SystemMetric(metric_name=f"perf_test_{i}", metric_value=float(i))
                    session.add(metric)
                    await session.flush()
                    # Force rollback
                    raise ValueError("Intentional rollback")
            except ValueError:
                pass  # Expected

    await asyncio.gather(*[_write_and_rollback(i) for i in range(concurrency)])
    logger.info(f"Completed {concurrency} concurrent writes & rollbacks in {time.perf_counter() - start:.2f}s")


@pytest.mark.asyncio
async def test_bulk_inserts():
    start = time.perf_counter()
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Insert a dummy dataset first
            ds = Dataset(name=f"perf_ds_{int(time.time())}")
            session.add(ds)
            await session.flush()

            # Bulk add 100 features
            features = [
                Feature(dataset_id=ds.id, name=f"feat_{i}", dtype="float")
                for i in range(100)
            ]
            session.add_all(features)

            # Bulk add 500 audit logs
            logs = [
                AuditLog(event_name="PERF_TEST", component="perf", severity="INFO")
                for i in range(500)
            ]
            session.add_all(logs)
    logger.info(f"Completed bulk insert of 1 Dataset, 100 Features, 500 AuditLogs in {time.perf_counter() - start:.2f}s")


async def run_all_perf_tests():
    from app.storage.database import init_db
    logger.info("Initializing DB tables...")
    await init_db()

    logger.info("Starting PostgreSQL Phase 3 Performance Hardening Tests...")
    try:
        await test_concurrent_reads(100)
        await test_concurrent_writes_and_rollbacks(50)
        await test_bulk_inserts()

        pool = engine.pool
        logger.info(f"Final Pool Stats - size: {pool.size()}, checkedin: {pool.checkedin()}, checkedout: {pool.checkedout()}")
        logger.info("✅ All Database Performance Tests Passed.")
    except Exception as e:
        logger.error(f"❌ Performance tests failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_all_perf_tests())
