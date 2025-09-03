"""
Pydantic models for the Learner Profile System.
Implements the exact schemas from learner-profile-mvp-spec.md
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Union, Any, Literal
from datetime import datetime
import json

# Evidence Schema - Unified format for questionnaire and interaction data
class EvidenceItem(BaseModel):
    """Single evidence item that contributes to learner profile updates"""
    source: Literal["questionnaire", "interaction", "manual"]
    ts: datetime = Field(default_factory=datetime.now)
    dimension: Literal[
        "basic_info", 
        "technical_profile", 
        "cognitive_profile", 
        "learning_style", 
        "challenges_needs", 
        "ai_strategy", 
        "career"
    ]
    field: Optional[str] = None  # If omitted, treat as whole-dimension merge
    value: Union[str, List[str], Dict[str, Any]]  # Flexible value types
    confidence: float = Field(ge=0.0, le=1.0)  # Extraction certainty 0-1
    weight: float = Field(default=1.0, ge=0.0)  # Source importance
    note: Optional[str] = None  # Additional context/explanation

class EvidenceCollection(BaseModel):
    """Collection of evidence items for profile updates"""
    evidence: List[EvidenceItem]

# Core Profile Dimensions - Only educational data, no metadata
class BasicInfo(BaseModel):
    """Student's basic academic information"""
    name: Optional[str] = None
    program: Optional[str] = None
    enrollment: Optional[Dict[str, str]] = None  # course, term, etc.

class TechnicalProfile(BaseModel):
    """Student's technical background and skills"""
    prior_education: Optional[str] = None  # CS, non-CS, etc.
    python_skill: Optional[str] = None  # beginner, intermediate, advanced
    ai_tools_used: Optional[List[str]] = Field(default_factory=list)
    programming_experience: Optional[str] = None
    technical_concepts: Optional[List[str]] = Field(default_factory=list)

class CognitiveProfile(BaseModel):
    """Student's learning and reasoning patterns"""
    comprehension: Optional[str] = None  # quick, with_guidance, needs_repetition
    execution_ability: Optional[str] = None  # high, medium, low
    learning_pace: Optional[str] = None  # fast, moderate, slow_clear_steps
    reasoning_style: Optional[str] = None  # analytical, intuitive, reflective
    problem_solving: Optional[str] = None  # systematic, exploratory, guided

class LearningStyle(BaseModel):
    """Student's preferred learning approaches"""
    preferred_formats: Optional[List[str]] = Field(default_factory=list)  # visual, text, examples, hands-on
    study_patterns: Optional[List[str]] = Field(default_factory=list)  # resource_driven, practice_focused, etc.
    motivation: Optional[str] = None  # competence, autonomy, connection, achievement
    engagement_triggers: Optional[List[str]] = Field(default_factory=list)

class ChallengesNeeds(BaseModel):
    """Student's learning gaps and support requirements"""
    concept_gaps: Optional[List[str]] = Field(default_factory=list)  # specific topics/concepts
    pain_points: Optional[List[str]] = Field(default_factory=list)  # recurring difficulties
    misconceptions: Optional[List[str]] = Field(default_factory=list)  # incorrect understanding patterns
    support_needed: Optional[List[str]] = Field(default_factory=list)  # types of help/scaffolding

class AIStrategy(BaseModel):
    """Recommended AI teaching approach for this student"""
    feedback_tone: Optional[str] = None  # encouraging, direct, adaptive
    guidance_mode: Optional[str] = None  # socratic, explanatory, hands-on
    intervention_style: Optional[str] = None  # scaffold_level_1, minimal_hints, detailed_walkthrough
    feedback_modes: Optional[List[str]] = Field(default_factory=list)  # text, visual_cues, interactive_questions

class Career(BaseModel):
    """Student's career interests and goals"""
    interests: Optional[List[str]] = Field(default_factory=list)  # Technology/IT, Research, etc.
    goals: Optional[List[str]] = Field(default_factory=list)  # applied-LLM-engineering, research, etc.
    timeline: Optional[str] = None  # short-term, long-term
    focus_areas: Optional[List[str]] = Field(default_factory=list)

# Main Learner Profile Schema
class LearnerProfile(BaseModel):
    """Complete learner profile with all six core dimensions.
    Contains ONLY educational data - no IDs, timestamps, or metadata.
    External systems attach metadata as needed.
    """
    basic_info: BasicInfo = Field(default_factory=BasicInfo)
    technical_profile: TechnicalProfile = Field(default_factory=TechnicalProfile)
    cognitive_profile: CognitiveProfile = Field(default_factory=CognitiveProfile)
    learning_style: LearningStyle = Field(default_factory=LearningStyle)
    challenges_needs: ChallengesNeeds = Field(default_factory=ChallengesNeeds)
    ai_strategy: AIStrategy = Field(default_factory=AIStrategy)
    career: Career = Field(default_factory=Career)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values and empty defaults"""
        return self.model_dump(exclude_none=True, exclude_defaults=False)
    
    def to_json(self) -> str:
        """Convert to JSON string for database storage"""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LearnerProfile":
        """Create LearnerProfile from dictionary (e.g., from database)"""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> "LearnerProfile":
        """Create LearnerProfile from JSON string"""
        return cls.from_dict(json.loads(json_str))

# Utility functions for profile operations
def create_empty_profile() -> LearnerProfile:
    """Create a new empty learner profile with default structure"""
    return LearnerProfile()

def validate_evidence(evidence_data: List[Dict]) -> EvidenceCollection:
    """Validate and parse evidence data into structured format"""
    return EvidenceCollection(evidence=evidence_data)

def merge_profiles(current: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Simple profile merge utility - deep merge dictionaries"""
    result = current.copy()
    for key, value in updates.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_profiles(result[key], value)
        else:
            result[key] = value
    return result

# Example usage and validation
if __name__ == "__main__":
    # Test profile creation
    profile = LearnerProfile()
    profile.basic_info.name = "Alex"
    profile.technical_profile.python_skill = "beginner"
    profile.cognitive_profile.learning_pace = "slow_clear_steps"
    
    print("Sample Profile JSON:")
    print(profile.to_json())
    
    # Test evidence creation
    evidence = EvidenceItem(
        source="interaction",
        dimension="technical_profile",
        field="python_skill",
        value="beginner",
        confidence=0.85,
        note="Student struggled with basic syntax"
    )
    
    print("\nSample Evidence:")
    print(evidence.model_dump_json(indent=2))