#!/usr/bin/env python3
"""
DB 마이그레이션 스크립트
현재 DB → Vercel Postgres/Neon

사용법:
  python scripts/migrate-db-to-vercel.py --source-url postgresql://... --target-url postgresql://...
  
또는 환경 변수:
  SOURCE_DATABASE_URL=postgresql://... TARGET_DATABASE_URL=postgresql://... python scripts/migrate-db-to-vercel.py
"""
import argparse
import asyncio
import os
import sys
from datetime import datetime

import asyncpg


async def get_table_count(conn, table_name: str) -> int:
    """테이블 행 수 조회"""
    result = await conn.fetchval(f'SELECT COUNT(*) FROM "{table_name}"')
    return result


async def get_all_tables(conn) -> list:
    """모든 테이블 목록 조회 (Alembic 테이블 제외)"""
    query = """
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename != 'alembic_version'
        ORDER BY tablename
    """
    rows = await conn.fetch(query)
    return [row["tablename"] for row in rows]


async def migrate_table(source_conn, target_conn, table_name: str) -> dict:
    """단일 테이블 마이그레이션"""
    print(f"  - {table_name}...", end=" ", flush=True)
    
    # Source에서 데이터 조회
    rows = await source_conn.fetch(f'SELECT * FROM "{table_name}"')
    source_count = len(rows)
    
    if source_count == 0:
        print(f"Empty (0 rows)")
        return {"table": table_name, "rows": 0, "status": "empty"}
    
    # Target에 데이터 삽입 (기존 데이터 삭제)
    await target_conn.execute(f'TRUNCATE TABLE "{table_name}" CASCADE')
    
    # 컬럼명 추출
    if rows:
        columns = list(rows[0].keys())
        columns_str = ", ".join([f'"{col}"' for col in columns])
        placeholders = ", ".join([f"${i+1}" for i in range(len(columns))])
        
        insert_query = f'INSERT INTO "{table_name}" ({columns_str}) VALUES ({placeholders})'
        
        # 배치 삽입
        await target_conn.executemany(
            insert_query,
            [tuple(row[col] for col in columns) for row in rows]
        )
    
    # 검증
    target_count = await get_table_count(target_conn, table_name)
    
    if source_count == target_count:
        print(f"✅ {source_count} rows")
        return {"table": table_name, "rows": source_count, "status": "success"}
    else:
        print(f"❌ Mismatch! Source: {source_count}, Target: {target_count}")
        return {"table": table_name, "rows": source_count, "status": "error"}


async def migrate_database(source_url: str, target_url: str):
    """전체 DB 마이그레이션"""
    print(f"\n🚀 Starting DB Migration")
    print(f"{'='*60}")
    print(f"Source: {source_url.split('@')[1] if '@' in source_url else source_url}")
    print(f"Target: {target_url.split('@')[1] if '@' in target_url else target_url}")
    print(f"{'='*60}\n")
    
    # 연결
    print("📡 Connecting to databases...")
    source_conn = await asyncpg.connect(source_url)
    target_conn = await asyncpg.connect(target_url)
    
    try:
        # 테이블 목록 조회
        print("📋 Fetching table list...")
        tables = await get_all_tables(source_conn)
        print(f"Found {len(tables)} tables\n")
        
        # 마이그레이션 실행
        print("🔄 Migrating tables:")
        results = []
        for table in tables:
            result = await migrate_table(source_conn, target_conn, table)
            results.append(result)
        
        # 결과 요약
        print(f"\n{'='*60}")
        print("📊 Migration Summary:")
        print(f"{'='*60}")
        
        total_rows = sum(r["rows"] for r in results)
        success_count = sum(1 for r in results if r["status"] == "success")
        empty_count = sum(1 for r in results if r["status"] == "empty")
        error_count = sum(1 for r in results if r["status"] == "error")
        
        print(f"Total Tables: {len(tables)}")
        print(f"  ✅ Success: {success_count}")
        print(f"  ⚪ Empty: {empty_count}")
        print(f"  ❌ Errors: {error_count}")
        print(f"Total Rows Migrated: {total_rows:,}")
        
        if error_count > 0:
            print(f"\n❌ Migration completed with {error_count} errors!")
            sys.exit(1)
        else:
            print(f"\n✅ Migration completed successfully!")
    
    finally:
        await source_conn.close()
        await target_conn.close()


def main():
    parser = argparse.ArgumentParser(description="Migrate database to Vercel Postgres/Neon")
    parser.add_argument(
        "--source-url",
        default=os.getenv("SOURCE_DATABASE_URL"),
        help="Source database URL (or set SOURCE_DATABASE_URL env var)"
    )
    parser.add_argument(
        "--target-url",
        default=os.getenv("TARGET_DATABASE_URL"),
        help="Target database URL (or set TARGET_DATABASE_URL env var)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only count rows, do not migrate"
    )
    
    args = parser.parse_args()
    
    if not args.source_url:
        print("❌ Error: Source database URL not provided")
        print("Use --source-url or set SOURCE_DATABASE_URL environment variable")
        sys.exit(1)
    
    if not args.target_url:
        print("❌ Error: Target database URL not provided")
        print("Use --target-url or set TARGET_DATABASE_URL environment variable")
        sys.exit(1)
    
    # 실행
    asyncio.run(migrate_database(args.source_url, args.target_url))


if __name__ == "__main__":
    main()
