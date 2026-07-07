import os
import sys

# Ensure backend folder is in Python import path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import Base, engine, SessionLocal
from app.models import PromptTemplate
from app.services.ai_orchestrator import AIOrchestrator

def test_backend_setup():
    print(">>> Initializing database schema...")
    # This creates the tables (e.g. SQLite if locally tested, PostgreSQL if in docker)
    Base.metadata.create_all(bind=engine)
    
    print(">>> Seeding prompt templates...")
    from app.main import seed_templates
    seed_templates()
    
    db = SessionLocal()
    try:
        count = db.query(PromptTemplate).count()
        print(f">>> Seeded prompt templates count: {count}")
        assert count == 3, f"Expected 3 prompt templates, got {count}"
        
        # Test cleaning logic
        print(">>> Testing AIOrchestrator cleaning logic...")
        orch = AIOrchestrator()
        cleaned = orch._preprocess({
            "name": "   Super  Widget  1000 ",
            "category": "Tools",
            "description": "A very   powerful widget",
            "detailed_description": "First line. \n\n Second line."
        })
        
        print(f"Cleaned output: {cleaned}")
        assert cleaned["name"] == "Super Widget 1000"
        assert cleaned["description"] == "A very powerful widget"
        
        # Test mock processing path (triggered when OpenAI API key is missing or dummy)
        print(">>> Testing AIOrchestrator mock run...")
        result = orch.process_product_row({
            "name": "Test Product",
            "category": "Test Category",
            "description": "Test Description",
            "detailed_description": "Test Detailed Description"
        })
        print(f"Orchestration Result Status: {result['status']}")
        print(f"Short description: '{result['short_description']}'")
        print(f"Detailed description:\n{result['detailed_description']}")
        
        assert result["status"] == "SUCCESS"
        assert len(result["short_description"]) > 0
        assert "## Product Overview" in result["detailed_description"]
        print(">>> ALL UNIT VERIFICATIONS COMPLETED SUCCESSFULLY!")
    except Exception as e:
        print(f"Test failed with error: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    test_backend_setup()
