import pytest
from agent.agents.placement_agent import PlacementAgent

def test_placement_modules_generation():
    agent = PlacementAgent()
    modules = agent.get_placement_modules("data_scientist")
    
    assert len(modules) == 4
    mod_types = [m.module_type for m in modules]
    assert "dsa" in mod_types
    assert "aptitude" in mod_types
    assert "interview_qa" in mod_types
    assert "resume_checklist" in mod_types

def test_interview_qa_content():
    agent = PlacementAgent()
    modules = agent.get_placement_modules("data_scientist")
    qa_mod = next(m for m in modules if m.module_type == "interview_qa")
    
    assert len(qa_mod.items) >= 4
    # Contains both technical and STAR-method behavioral questions
    types = [q["type"] for q in qa_mod.items]
    assert "technical" in types
    assert "behavioral_hr" in types
