"""
AI Health Check CLI Tool.

Command-line utility to check the health of AI providers.

Usage:
    python -m src.cli.ai_health
    python -m src.cli.ai_health --verbose
"""

import asyncio
import sys
import os
from src.core.ai.health import check_ai_health
from src.core.config.ai_settings import settings

# Fix Windows console encoding
if sys.platform == "win32":
    os.system("chcp 65001 > nul 2>&1")


def format_health_report(report, verbose: bool = False):
    """Format health report for CLI output."""
    print("\n" + "=" * 60)
    print("AI PROVIDERS HEALTH CHECK")
    print("=" * 60)
    
    # Overall status
    if report.all_ok:
        print("[OK] Overall Status: ALL OK")
    else:
        print("[!] Overall Status: SOME FAILURES")
    
    print(f"\nHealthy: {len(report.healthy_providers)}/{len(report.providers)}")
    
    # Individual provider status
    print("\n" + "-" * 60)
    print("Provider Details:")
    print("-" * 60)
    
    for name, health in report.providers.items():
        status_icon = "[OK]" if health.ok else "[!]"
        print(f"\n{status_icon} {name.upper()}")
        
        if health.ok:
            print(f"   Status: Healthy")
            if verbose and health.details:
                print(f"   Details:")
                for key, value in health.details.items():
                    print(f"      {key}: {value}")
        else:
            print(f"   Status: Unhealthy")
            print(f"   Error: {health.error}")
    
    print("\n" + "=" * 60)
    
    # Exit code based on health
    return 0 if report.all_ok else 1


async def main():
    """Main CLI entry point."""
    # Check for verbose flag
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    
    print("Checking AI providers...")
    
    try:
        report = await check_ai_health(settings)
        exit_code = format_health_report(report, verbose)
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n[ERROR] Health check failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
