"""CLI entry point: python -m sbfoundation.maintenance"""
from sbfoundation.maintenance.maintenance_service import MaintenanceService

if __name__ == "__main__":
    MaintenanceService().run()
