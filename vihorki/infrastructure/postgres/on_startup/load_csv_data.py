"""
Script to load data from CSV files into database tables.
Drops existing tables, recreates them, and fills with fresh data from CSV.
"""

import csv
import logging
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from vihorki.infrastructure.postgres.on_startup.init_tables import VisitTable, HitTable, Base

logger = logging.getLogger(__name__)

# Path to CSV data files
DATA_DIR = Path(__file__).parent.parent / "data"
HITS_CSV = DATA_DIR / "hits.csv"
VISITS_CSV = DATA_DIR / "visit.csv"


def parse_datetime(dt_str: str) -> datetime | None:
    """Parse datetime string from CSV."""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace(' ', 'T'))
    except ValueError:
        try:
            return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None


def parse_bool(val: str) -> bool:
    """Parse boolean value from CSV."""
    return val in ('1', 'True', 'true', 'TRUE')


def parse_int(val: str) -> int | None:
    """Parse integer value from CSV."""
    if not val:
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


async def drop_and_recreate_tables(engine):
    """Drop all tables and recreate them."""
    logger.info("Dropping existing tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        logger.info("Tables dropped successfully")
        
        logger.info("Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Tables created successfully")


async def load_hits_from_csv(session: AsyncSession) -> int:
    """Load hits data from CSV file."""
    if not HITS_CSV.exists():
        logger.warning(f"Hits CSV file not found: {HITS_CSV}")
        return 0
    
    logger.info(f"Loading hits from {HITS_CSV}")
    count = 0
    batch = []
    batch_size = 1000
    
    with open(HITS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            watch_id = row.get('watchID', '')
            if not watch_id:
                continue
            
            hit = HitTable(
                watch_id=str(watch_id),
                client_id=str(row.get('clientID', '')),
                url=row.get('URL', ''),
                datetime_hit=parse_datetime(row.get('dateTime', '')),
                title=row.get('title', '')
            )
            batch.append(hit)
            count += 1
            
            if len(batch) >= batch_size:
                session.add_all(batch)
                await session.flush()
                batch = []
    
    if batch:
        session.add_all(batch)
        await session.flush()
    
    logger.info(f"Loaded {count} hits")
    return count


async def load_visits_from_csv(session: AsyncSession) -> int:
    """
    Load visits data from CSV file.
    Aggregates multiple rows with same visitID into single visit with watchIDs list.
    """
    if not VISITS_CSV.exists():
        logger.warning(f"Visits CSV file not found: {VISITS_CSV}")
        return 0
    
    logger.info(f"Loading visits from {VISITS_CSV}")
    
    # First pass: aggregate watchIDs for each visitID
    visits_data = defaultdict(lambda: {
        'watch_ids': [],
        'row': None
    })
    
    with open(VISITS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            visit_id = row.get('visitID', '')
            if not visit_id:
                continue
            
            watch_id = row.get('watchID', '')
            if watch_id:
                visits_data[visit_id]['watch_ids'].append(str(watch_id))
            
            # Keep the first row data for this visitID
            if visits_data[visit_id]['row'] is None:
                visits_data[visit_id]['row'] = row
    
    # Second pass: create Visit objects
    count = 0
    batch = []
    batch_size = 500
    
    for visit_id, data in visits_data.items():
        row = data['row']
        if not row:
            continue
        
        # Format watchIDs as comma-separated string
        watch_ids_str = ','.join(data['watch_ids'])
        
        visit = VisitTable(
            visit_id=parse_int(visit_id),
            watch_ids=watch_ids_str,
            date_time=parse_datetime(row.get('dateTime', '')),
            is_new_user=parse_bool(row.get('isNewUser', '')),
            start_url=row.get('startURL', ''),
            end_url=row.get('endURL', ''),
            page_views=parse_int(row.get('pageViews', '')),
            visit_duration=parse_int(row.get('visitDuration', '')),
            region_city=row.get('regionCity', ''),
            client_id=str(row.get('clientID', '')),
            last_search_engine_root=row.get('lastsignSearchEngineRoot', ''),
            device_category=parse_int(row.get('deviceCategory', '')),
            mobile_phone=row.get('mobilePhone', ''),
            mobile_phone_model=row.get('mobilePhoneModel', ''),
            operating_system=row.get('operatingSystem', ''),
            browser=row.get('browser', ''),
            screen_format=row.get('screenFormat', ''),
            screen_orientation_name=row.get('screenOrientationName', '')
        )
        batch.append(visit)
        count += 1
        
        if len(batch) >= batch_size:
            session.add_all(batch)
            await session.flush()
            batch = []
    
    if batch:
        session.add_all(batch)
        await session.flush()
    
    logger.info(f"Loaded {count} visits")
    return count


async def load_all_data(engine):
    """
    Main function to drop tables, recreate them, and load data from CSV files.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker
    
    # Drop and recreate tables
    await drop_and_recreate_tables(engine)
    
    # Load data
    Session = async_sessionmaker(engine)
    async with Session() as session:
        async with session.begin():
            hits_count = await load_hits_from_csv(session)
            visits_count = await load_visits_from_csv(session)
            
            logger.info(f"Data loading complete: {visits_count} visits, {hits_count} hits")
            
    return {'visits': visits_count, 'hits': hits_count}

