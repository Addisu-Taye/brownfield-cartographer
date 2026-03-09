#!/usr/bin/env python
"""Quick test script for jaffle_shop analysis."""

from pathlib import Path
from src.agents.surveyor import Surveyor
import json

def test_jaffle_shop():
    """Test Surveyor on jaffle_shop."""
    print("=" * 60)
    print("Testing Surveyor on jaffle_shop")
    print("=" * 60)
    
    # Path to jaffle_shop (assuming it's in the same parent directory)
    jaffle_path = Path("../jaffle_shop").resolve()
    
    if not jaffle_path.exists():
        print(f"❌ jaffle_shop not found at {jaffle_path}")
        print("Please clone it first:")
        print("  git clone https://github.com/dbt-labs/jaffle_shop.git")
        return
    
    print(f"📁 Repository: {jaffle_path}")
    
    # Initialize Surveyor
    surveyor = Surveyor(str(jaffle_path))
    
    # Run analysis
    print("\n🔍 Running Surveyor...")
    graph = surveyor.run()
    
    # Print results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    print(f"\n📊 Statistics:")
    print(f"  Files scanned: {surveyor.stats['files_scanned']}")
    print(f"  Python files: {surveyor.stats['python_files']}")
    print(f"  SQL files:    {surveyor.stats['sql_files']}")
    print(f"  YAML files:    {surveyor.stats['yaml_files']}")
    
    # Show SQL files found
    if surveyor.stats['sql_files'] > 0:
        print("\n📋 SQL Files (will be analyzed in Phase 2):")
        sql_files = []
        for file_path in jaffle_path.rglob("*.sql"):
            rel_path = file_path.relative_to(jaffle_path)
            sql_files.append(str(rel_path))
        
        for sql_file in sorted(sql_files)[:10]:  # Show first 10
            print(f"  - {sql_file}")
    
    # Show YAML files
    if surveyor.stats['yaml_files'] > 0:
        print("\n⚙️  YAML Files:")
        yaml_files = []
        for file_path in jaffle_path.rglob("*.yml"):
            rel_path = file_path.relative_to(jaffle_path)
            yaml_files.append(str(rel_path))
        
        for yaml_file in sorted(yaml_files):
            print(f"  - {yaml_file}")
    
    # Save artifacts
    print("\n💾 Saving artifacts...")
    surveyor.save_graph(jaffle_path / ".cartography" / "module_graph.json")
    
    print(f"\n✅ Test complete!")
    print(f"📁 Artifacts saved to: {jaffle_path}/.cartography/")

if __name__ == "__main__":
    test_jaffle_shop()