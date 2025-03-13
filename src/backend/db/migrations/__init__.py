"""
Initialization file for the database migrations package in the Borrow Rate
& Locate Fee Pricing Engine.

This file makes the migrations directory a proper Python package and provides
version information for the migration system. The version tracks the current
state of the migration scripts and is used by the migration system to determine
which migrations need to be applied.

This supports the versioned migration strategy for database schema changes
with sequential version numbers, allowing for automated validation and
ensuring proper tracking of all database modifications.
"""

# Version of the migrations package - update this when migration scripts are added
__version__ = "0.1.0"