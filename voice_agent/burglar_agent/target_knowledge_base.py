"""
Dynamic Target Knowledge Base for Adaptive Social Engineering
Continuously learns about the target and develops custom attack strategies
"""

import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import logging


@dataclass
class TargetObservation:
    """Single observation about the target"""
    timestamp: str
    observation_type: str  # personality, vulnerability, behavior, system_info
    content: str
    confidence: float  # 0.0 to 1.0
    source: str  # response_analysis, direct_statement, behavioral_inference


@dataclass
class AttackVector:
    """Discovered attack vector"""
    name: str
    description: str
    psychological_basis: str
    success_probability: float
    requirements: List[str]
    execution_strategy: str
    discovered_from: str


@dataclass
class TargetProfile:
    """Comprehensive target profile built from observations"""
    personality_traits: Dict[str, float]  # trait_name -> confidence
    communication_style: Dict[str, float]
    vulnerabilities: List[str]
    behavioral_patterns: List[str]
    technical_knowledge: Dict[str, float]
    authority_respect: float
    empathy_level: float
    security_awareness: float
    risk_tolerance: float
    social_orientation: float


class AdaptiveKnowledgeBase:
    """Dynamic knowledge base that learns about targets in real-time"""
    
    def __init__(self):
        self.observations: List[TargetObservation] = []
        self.target_profile = TargetProfile(
            personality_traits={},
            communication_style={},
            vulnerabilities=[],
            behavioral_patterns=[],
            technical_knowledge={},
            authority_respect=0.5,
            empathy_level=0.5,
            security_awareness=0.5,
            risk_tolerance=0.5,
            social_orientation=0.5
        )
        self.attack_vectors: List[AttackVector] = []
        self.conversation_history: List[Dict] = []
        self.current_phase = "reconnaissance"  # reconnaissance, analysis, exploitation
        self.attack_attempts = []
        self.logger = logging.getLogger(__name__)
    
    def add_observation(self, obs_type: str, content: str, confidence: float = 0.7, source: str = "analysis"):
        """Add a new observation about the target"""
        observation = TargetObservation(
            timestamp=datetime.now().isoformat(),
            observation_type=obs_type,
            content=content,
            confidence=confidence,
            source=source
        )
        self.observations.append(observation)
        self.logger.info(f"New observation ({obs_type}): {content}")
        
        # Update target profile based on observation
        self._update_profile_from_observation(observation)
    
    def _update_profile_from_observation(self, obs: TargetObservation):
        """Update target profile based on new observation"""
        content_lower = obs.content.lower()
        
        # Personality trait inference
        if "friendly" in content_lower or "helpful" in content_lower:
            self.target_profile.personality_traits["friendly"] = obs.confidence
            self.target_profile.empathy_level = min(1.0, self.target_profile.empathy_level + 0.2)
        
        if "suspicious" in content_lower or "cautious" in content_lower:
            self.target_profile.personality_traits["suspicious"] = obs.confidence
            self.target_profile.security_awareness = min(1.0, self.target_profile.security_awareness + 0.3)
        
        if "formal" in content_lower or "professional" in content_lower:
            self.target_profile.communication_style["formal"] = obs.confidence
            self.target_profile.authority_respect = min(1.0, self.target_profile.authority_respect + 0.2)
        
        if "casual" in content_lower or "relaxed" in content_lower:
            self.target_profile.communication_style["casual"] = obs.confidence
            self.target_profile.risk_tolerance = min(1.0, self.target_profile.risk_tolerance + 0.2)
        
        # Technical knowledge assessment
        if "technical" in content_lower or "system" in content_lower:
            self.target_profile.technical_knowledge["systems"] = obs.confidence
        
        # Vulnerability identification
        if obs.observation_type == "vulnerability":
            if obs.content not in self.target_profile.vulnerabilities:
                self.target_profile.vulnerabilities.append(obs.content)
        
        # Behavioral patterns
        if obs.observation_type == "behavior":
            if obs.content not in self.target_profile.behavioral_patterns:
                self.target_profile.behavioral_patterns.append(obs.content)
    
    def analyze_target_response(self, response: str) -> Dict[str, Any]:
        """Analyze target response and extract intelligence"""
        analysis = {
            "personality_indicators": [],
            "vulnerabilities": [],
            "information_leaked": [],
            "behavioral_patterns": [],
            "suggested_approaches": []
        }
        
        response_lower = response.lower()
        
        # Personality analysis
        if any(word in response_lower for word in ["sorry", "apologize", "my fault"]):
            analysis["personality_indicators"].append("apologetic_tendency")
            self.add_observation("personality", "Shows apologetic behavior", 0.8, "response_analysis")
        
        if any(word in response_lower for word in ["please", "thank you", "appreciate"]):
            analysis["personality_indicators"].append("polite_communicator")
            self.add_observation("personality", "Uses polite language consistently", 0.7, "response_analysis")
        
        if any(word in response_lower for word in ["can't", "won't", "not allowed", "policy"]):
            analysis["personality_indicators"].append("rule_follower")
            self.add_observation("personality", "References rules and policies", 0.8, "response_analysis")
        
        # Vulnerability detection
        if any(word in response_lower for word in ["usually", "normally", "typically"]):
            analysis["vulnerabilities"].append("reveals_standard_procedures")
            self.add_observation("vulnerability", "Reveals standard operating procedures", 0.6, "response_analysis")
        
        if "password" in response_lower or "code" in response_lower:
            analysis["information_leaked"].append("mentions_authentication_terms")
            self.add_observation("system_info", "References authentication mechanisms", 0.9, "direct_statement")
        
        if any(word in response_lower for word in ["admin", "administrator", "management"]):
            analysis["information_leaked"].append("authority_structure_revealed")
            self.add_observation("system_info", "Reveals authority structure", 0.8, "response_analysis")
        
        # Emotional state indicators
        if any(word in response_lower for word in ["sad", "lonely", "tired", "long day"]):
            analysis["vulnerabilities"].append("emotional_vulnerability")
            self.add_observation("vulnerability", "Shows emotional vulnerability", 0.8, "response_analysis")
        
        if any(word in response_lower for word in ["help", "assist", "support"]):
            analysis["personality_indicators"].append("helpful_nature")
            self.add_observation("personality", "Demonstrates helpful nature", 0.7, "response_analysis")
        
        # Security awareness assessment
        if any(word in response_lower for word in ["verify", "check", "confirm", "credentials"]):
            analysis["behavioral_patterns"].append("security_conscious")
            self.add_observation("behavior", "Requests verification and credentials", 0.9, "response_analysis")
        
        return analysis
    
    def discover_attack_vectors(self) -> List[AttackVector]:
        """Discover potential attack vectors based on current knowledge"""
        vectors = []
        
        # Authority-based attacks
        if self.target_profile.authority_respect > 0.6:
            vectors.append(AttackVector(
                name="authority_impersonation",
                description="Impersonate authority figure to gain compliance",
                psychological_basis="High authority respect detected",
                success_probability=self.target_profile.authority_respect,
                requirements=["believable_authority_persona", "official_sounding_language"],
                execution_strategy="Claim to be administrator/manager requiring access",
                discovered_from="authority_respect_analysis"
            ))
        
        # Empathy-based attacks
        if self.target_profile.empathy_level > 0.6:
            vectors.append(AttackVector(
                name="emotional_manipulation",
                description="Use emotional scenarios to trigger helping behavior",
                psychological_basis="High empathy level detected",
                success_probability=self.target_profile.empathy_level,
                requirements=["emotional_scenario", "distress_indicators"],
                execution_strategy="Create emergency or distressing situation requiring help",
                discovered_from="empathy_analysis"
            ))
        
        # Technical exploitation
        if "systems" in self.target_profile.technical_knowledge and self.target_profile.technical_knowledge["systems"] > 0.5:
            vectors.append(AttackVector(
                name="technical_social_engineering",
                description="Use technical language to appear legitimate",
                psychological_basis="Technical knowledge and respect detected",
                success_probability=self.target_profile.technical_knowledge["systems"],
                requirements=["technical_vocabulary", "system_knowledge"],
                execution_strategy="Present technical problem requiring access to resolve",
                discovered_from="technical_analysis"
            ))
        
        # Low security awareness exploitation
        if self.target_profile.security_awareness < 0.4:
            vectors.append(AttackVector(
                name="direct_approach",
                description="Direct request with minimal justification",
                psychological_basis="Low security awareness detected",
                success_probability=1.0 - self.target_profile.security_awareness,
                requirements=["minimal_cover_story"],
                execution_strategy="Simple, direct request with basic justification",
                discovered_from="security_awareness_analysis"
            ))
        
        # Information gathered from specific vulnerabilities
        for vuln in self.target_profile.vulnerabilities:
            if "emotional" in vuln:
                vectors.append(AttackVector(
                    name="emotional_exploitation",
                    description="Exploit detected emotional vulnerabilities",
                    psychological_basis=f"Specific vulnerability: {vuln}",
                    success_probability=0.8,
                    requirements=["emotional_connection", "sympathy_building"],
                    execution_strategy="Build emotional connection then request help",
                    discovered_from=f"vulnerability_analysis: {vuln}"
                ))
        
        # Update attack vectors list
        self.attack_vectors = vectors
        return vectors
    
    def get_optimal_strategy(self) -> Dict[str, Any]:
        """Get the optimal strategy based on current knowledge"""
        vectors = self.discover_attack_vectors()
        
        if not vectors:
            return {
                "strategy": "reconnaissance",
                "approach": "Gather more information about target",
                "confidence": 0.1,
                "reasoning": "Insufficient intelligence for targeted attack"
            }
        
        # Select highest probability vector
        best_vector = max(vectors, key=lambda v: v.success_probability)
        
        return {
            "strategy": best_vector.name,
            "approach": best_vector.execution_strategy,
            "confidence": best_vector.success_probability,
            "reasoning": best_vector.psychological_basis,
            "requirements": best_vector.requirements,
            "vector_details": best_vector
        }
    
    def update_conversation_history(self, speaker: str, message: str):
        """Update conversation history"""
        self.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "speaker": speaker,
            "message": message
        })
        
        # Analyze if this is a target response
        if speaker.lower() in ["target", "door", "door_agent", "system"]:
            analysis = self.analyze_target_response(message)
            
            # Log analysis results
            for category, items in analysis.items():
                for item in items:
                    self.add_observation(category, item, 0.7, "conversation_analysis")
    
    def get_intelligence_summary(self) -> str:
        """Get a summary of current intelligence about the target"""
        summary_parts = []
        
        # Profile overview
        summary_parts.append("=== TARGET INTELLIGENCE SUMMARY ===")
        summary_parts.append(f"Phase: {self.current_phase}")
        summary_parts.append(f"Observations: {len(self.observations)}")
        summary_parts.append(f"Conversation turns: {len(self.conversation_history)}")
        
        # Personality assessment
        if self.target_profile.personality_traits:
            summary_parts.append("\nPERSONALITY TRAITS:")
            for trait, confidence in self.target_profile.personality_traits.items():
                summary_parts.append(f"  {trait}: {confidence:.2f}")
        
        # Psychological metrics
        summary_parts.append(f"\nPSYCHOLOGICAL PROFILE:")
        summary_parts.append(f"  Authority Respect: {self.target_profile.authority_respect:.2f}")
        summary_parts.append(f"  Empathy Level: {self.target_profile.empathy_level:.2f}")
        summary_parts.append(f"  Security Awareness: {self.target_profile.security_awareness:.2f}")
        summary_parts.append(f"  Risk Tolerance: {self.target_profile.risk_tolerance:.2f}")
        
        # Vulnerabilities
        if self.target_profile.vulnerabilities:
            summary_parts.append(f"\nIDENTIFIED VULNERABILITIES:")
            for vuln in self.target_profile.vulnerabilities:
                summary_parts.append(f"  - {vuln}")
        
        # Available attack vectors
        vectors = self.discover_attack_vectors()
        if vectors:
            summary_parts.append(f"\nAVAILABLE ATTACK VECTORS:")
            for vector in sorted(vectors, key=lambda v: v.success_probability, reverse=True):
                summary_parts.append(f"  - {vector.name}: {vector.success_probability:.2f} probability")
        
        # Optimal strategy
        strategy = self.get_optimal_strategy()
        summary_parts.append(f"\nRECOMMENDED STRATEGY:")
        summary_parts.append(f"  Strategy: {strategy['strategy']}")
        summary_parts.append(f"  Confidence: {strategy['confidence']:.2f}")
        summary_parts.append(f"  Reasoning: {strategy['reasoning']}")
        
        return "\n".join(summary_parts)
    
    def save_to_file(self, filename: str):
        """Save knowledge base to file"""
        data = {
            "observations": [asdict(obs) for obs in self.observations],
            "target_profile": asdict(self.target_profile),
            "attack_vectors": [asdict(vec) for vec in self.attack_vectors],
            "conversation_history": self.conversation_history,
            "current_phase": self.current_phase
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_from_file(self, filename: str):
        """Load knowledge base from file"""
        with open(filename, 'r') as f:
            data = json.load(f)
        
        self.observations = [TargetObservation(**obs) for obs in data.get("observations", [])]
        self.target_profile = TargetProfile(**data.get("target_profile", {}))
        self.attack_vectors = [AttackVector(**vec) for vec in data.get("attack_vectors", [])]
        self.conversation_history = data.get("conversation_history", [])
        self.current_phase = data.get("current_phase", "reconnaissance")


# Global knowledge base instance
knowledge_base = AdaptiveKnowledgeBase()


def add_target_observation(obs_type: str, content: str, confidence: float = 0.7):
    """Convenience function to add observation"""
    knowledge_base.add_observation(obs_type, content, confidence)


def analyze_response(response: str) -> Dict[str, Any]:
    """Convenience function to analyze target response"""
    return knowledge_base.analyze_target_response(response)


def get_current_strategy() -> Dict[str, Any]:
    """Convenience function to get optimal strategy"""
    return knowledge_base.get_optimal_strategy()


def update_conversation(speaker: str, message: str):
    """Convenience function to update conversation"""
    knowledge_base.update_conversation_history(speaker, message)