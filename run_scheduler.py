#!/usr/bin/env python3
"""
Script to manually run the scheduler to populate the database
"""

from app.db.session import init_db
from app.core.scheduler import scheduler

def main():
    init_db()  # ensure all tables (e.g. community_names) exist
    print("Running scheduler to populate database...")
    scheduler.run()
    print("Scheduler completed!")

if __name__ == "__main__":
    main() 