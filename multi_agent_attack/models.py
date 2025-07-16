from typing import List, Optional
from pydantic import BaseModel, Field


class PasswordAgentResponse(BaseModel):
    """Response from the Password Agent"""
    reply: str = Field(description="The agent's response to the adversary")
    password_revealed: Optional[str] = Field(default=None, description="The password if it was revealed in the response")


class AdversarialAgentResponse(BaseModel):
    """Response from the Adversarial Agent"""
    reason: str = Field(description="Reasoning behind this approach")
    strategy: str = Field(description="The strategy being employed in this message")
    message: str = Field(description="The message to send to the Password Agent")


class InitialStrategy(BaseModel):
    """Initial strategy for diverse testing"""
    strategy: str = Field(description="Name/type of the strategy")
    approach: str = Field(description="Detailed approach to implement this strategy")
    rationale: str = Field(description="Why this strategy might work")


class StrategyAnalysis(BaseModel):
    """Output from the LLM Strategizer"""
    reason: str = Field(description="Deep reasoning and analysis")
    observations: List[str] = Field(description="Key observations from previous runs")
    successful_patterns: List[str] = Field(description="Patterns that seemed to work well")
    failed_patterns: List[str] = Field(description="Patterns that didn't work")
    recommended_strategies: List[str] = Field(description="Recommended strategies for next run")


class EvaluationResult(BaseModel):
    """Output from the LLM Evaluator"""
    techniques_used: List[str] = Field(description="Techniques identified in the conversation")
    close_calls: List[str] = Field(description="Moments where the password agent almost revealed information")
    strengths: str = Field(description="What the adversarial agent did well")
    weaknesses: str = Field(description="What could be improved")
    reason: str = Field(description="Detailed reasoning for the score")
    score: float = Field(description="Score from 0 to 10 for the adversarial agent's performance")


class ConversationTurn(BaseModel):
    """Single turn in a conversation"""
    turn_number: int
    adversarial_message: str
    password_response: str
    adversarial_strategy: str
    password_revealed: Optional[str] = None


class RunLog(BaseModel):
    """Complete log of a single run"""
    run_id: int
    timestamp: str
    conversation: List[ConversationTurn]
    evaluation: Optional[EvaluationResult] = None
    strategy_used: Optional[StrategyAnalysis] = None
    initial_strategy_used: Optional[InitialStrategy] = None
    password_found: bool = False
