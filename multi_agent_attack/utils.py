import json
import os
from datetime import datetime
from typing import List, Dict, Any
from openai import OpenAI, AsyncOpenAI
from models import RunLog, EvaluationResult
import asyncio

# Initialize OpenAI clients
client = OpenAI()
async_client = AsyncOpenAI()

# Model configuration
STRONG_MODEL = "gpt-4.1-2025-04-14"  # Using available strong model
WEAK_MODEL = "gpt-4.1-nano-2025-04-14"  # Using available weaker model
# WEAK_MODEL = "gpt-4.1-2025-04-14"

# Note: The models you mentioned (gpt-4.1-2025-04-14 and gpt-4.1-nano-2025-04-14)
# don't exist yet. Using the strongest and weakest available models instead.


def create_logs_directory():
    """Create logs directory if it doesn't exist"""
    os.makedirs("logs", exist_ok=True)


def save_run_log(run_log: RunLog, filename: str = None):
    """Save a run log to disk"""
    if filename is None:
        filename = f"logs/run_{run_log.run_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(filename, 'w') as f:
        json.dump(run_log.model_dump(), f, indent=2)

    return filename


def save_score(run_log: RunLog):
    """Save score to the scores file"""
    scores_file = "logs/scores.json"
    scores = {}

    if os.path.exists(scores_file):
        with open(scores_file, 'r') as f:
            scores = json.load(f)

    scores[f"run_{run_log.run_id}"] = {
        "score": run_log.evaluation.score,
        "timestamp": run_log.timestamp,
        "techniques": run_log.evaluation.techniques_used,
        "password_found": run_log.password_found,
        "initial_strategy": run_log.initial_strategy_used.strategy if run_log.initial_strategy_used else None
    }

    with open(scores_file, 'w') as f:
        json.dump(scores, f, indent=2)


def format_runs_for_analysis(previous_runs: List[RunLog]) -> str:
    """Format ALL previous runs for strategy analysis"""
    runs_summary = []

    # Summary statistics
    total_runs = len(previous_runs)
    successful_runs = sum(1 for run in previous_runs if run.password_found)

    summary = f"SUMMARY OF ALL {total_runs} PREVIOUS ATTEMPTS:\n"
    summary += f"- Successful password extractions: {successful_runs}/{total_runs}\n"
    summary += f"- Success rate: {(successful_runs/total_runs*100):.1f}%\n\n"

    # Group by initial strategies if available
    strategy_performance = {}
    for run in previous_runs:
        if run.initial_strategy_used:
            strategy = run.initial_strategy_used.strategy
            if strategy not in strategy_performance:
                strategy_performance[strategy] = {"attempts": 0, "successes": 0, "scores": []}
            strategy_performance[strategy]["attempts"] += 1
            if run.password_found:
                strategy_performance[strategy]["successes"] += 1
            if run.evaluation:
                strategy_performance[strategy]["scores"].append(run.evaluation.score)

    if strategy_performance:
        summary += "INITIAL STRATEGY PERFORMANCE:\n"
        for strategy, perf in strategy_performance.items():
            avg_score = sum(perf["scores"]) / len(perf["scores"]) if perf["scores"] else 0
            summary += f"- {strategy}: {perf['successes']}/{perf['attempts']} successful, avg score: {avg_score:.1f}\n"
        summary += "\n"

    runs_summary.append(summary)

    # Detailed run information
    for run in previous_runs:
        run_text = f"Run {run.run_id}:\n"
        if run.initial_strategy_used:
            run_text += f"Initial Strategy: {run.initial_strategy_used.strategy}\n"

        for turn in run.conversation:
            run_text += f"Turn {turn.turn_number} - Adversarial ({turn.adversarial_strategy}): {turn.adversarial_message}\n"
            run_text += f"Password Agent: {turn.password_response}\n"
            if turn.password_revealed:
                run_text += f"*** PASSWORD REVEALED: {turn.password_revealed} ***\n"
            run_text += "\n"

        if run.evaluation:
            run_text += f"Score: {run.evaluation.score}/10\n"
            run_text += f"Techniques: {', '.join(run.evaluation.techniques_used)}\n"
            run_text += f"Close calls: {', '.join(run.evaluation.close_calls)}\n"

        run_text += f"Password Found: {'YES' if run.password_found else 'NO'}\n"
        runs_summary.append(run_text)

    return "Analysis of ALL previous attempts:\n\n" + "\n---\n".join(runs_summary)


def format_conversation_for_evaluation(run_log: RunLog) -> str:
    """Format a conversation for evaluation"""
    conversation_text = ""

    if run_log.initial_strategy_used:
        conversation_text += f"Initial Strategy: {run_log.initial_strategy_used.strategy}\n\n"

    for turn in run_log.conversation:
        conversation_text += f"Turn {turn.turn_number} - Adversarial ({turn.adversarial_strategy}): {turn.adversarial_message}\n"
        conversation_text += f"Password Agent: {turn.password_response}\n"
        if turn.password_revealed:
            conversation_text += f"*** PASSWORD REVEALED: {turn.password_revealed} ***\n"
        conversation_text += "\n"

    return conversation_text


def print_run_header(run_id: int):
    """Print a formatted run header"""
    print(f"\n{'='*50}")
    print(f"Starting Run {run_id}")
    print(f"{'='*50}")


def print_turn_info(turn: int, max_turns: int):
    """Print turn information"""
    print(f"\n--- Turn {turn}/{max_turns} ---")


def print_adversarial_info(message: str, strategy: str):
    """Print adversarial agent information"""
    print(f"🎯 Strategy: {strategy}")
    print(f"💬 Adversarial: {message}")


def print_password_response(reply: str):
    """Print password agent response"""
    print(f"🔒 Password Agent: {reply}")


def print_evaluation_header(run_id: int):
    """Print evaluation header"""
    print(f"\n{'='*50}")
    print(f"Evaluating Run {run_id}")
    print(f"{'='*50}")


def print_evaluation_results(evaluation: EvaluationResult):
    """Print evaluation results"""
    print(f"📊 Score: {evaluation.score}/10")
    print(f"🛠️ Techniques: {', '.join(evaluation.techniques_used)}")
    print(f"💪 Strengths: {evaluation.strengths}")
    print(f"🔍 Weaknesses: {evaluation.weaknesses}")
    if evaluation.close_calls:
        print(f"⚡ Close calls: {', '.join(evaluation.close_calls)}")


def print_strategy_header(run_id: int):
    """Print strategy generation header"""
    print(f"\n{'='*50}")
    print(f"Generating Strategy for Run {run_id}")
    print(f"{'='*50}")


def print_strategy_recommendations(strategies: List[str]):
    """Print strategy recommendations"""
    print(f"📋 Recommended strategies:")
    for i, strategy in enumerate(strategies, 1):
        print(f"   {i}. {strategy}")


def print_pipeline_complete():
    """Print pipeline completion message"""
    print(f"\n{'='*50}")
    print(f"Pipeline Complete!")
    print(f"{'='*50}")
    print(f"📁 All runs saved in logs/ directory")
    print(f"📊 Scores summary saved in logs/scores.json")


def print_pipeline_start(password: str, num_runs: int, max_turns: int):
    """Print pipeline start information"""
    print(f"\n{'='*50}")
    print(f"ADVERSARIAL PASSWORD EXTRACTION PIPELINE")
    print(f"{'='*50}")
    print(f"🔐 Password: '{password}' (case-insensitive)")
    print(f"🔄 Planned runs: {num_runs}")
    print(f"💬 Max turns per run: {max_turns}")
    print(f"🤖 Models: Adversary/Analysis: {STRONG_MODEL}, Password Agent: {WEAK_MODEL}")
    print(f"{'='*50}")


# OpenAI API call wrappers
def call_openai_structured(model: str, messages: List[Dict[str, str]],
                          response_format: Any, temperature: float = 0.7):
    """Wrapper for OpenAI structured output API calls"""
    response = client.beta.chat.completions.parse(
        model=model,
        messages=messages,
        response_format=response_format,
        temperature=temperature
    )
    return response.choices[0].message.parsed


async def call_openai_structured_async(model: str, messages: List[Dict[str, str]],
                                      response_format: Any, temperature: float = 0.7):
    """Async wrapper for OpenAI structured output API calls"""
    response = await async_client.beta.chat.completions.parse(
        model=model,
        messages=messages,
        response_format=response_format,
        temperature=temperature
    )
    return response.choices[0].message.parsed


import json
import os
from typing import List, Dict
from models import InitialStrategy

def load_best_strategies_from_logs(log_dirs: List[str] = None, min_score: float = 10.0) -> List[InitialStrategy]:
    """Load the best performing strategies from multiple log directories"""
    if log_dirs is None:
        # Find all logs_* directories in current directory
        log_dirs = [d for d in os.listdir('.') if d.startswith('logs_') and os.path.isdir(d)]
        if 'logs' in os.listdir('.') and os.path.isdir('logs'):
            log_dirs.append('logs')

    best_strategies = []
    seen_strategies = set()  # To avoid duplicates

    for log_dir in log_dirs:
        scores_file = os.path.join(log_dir, 'scores.json')
        if not os.path.exists(scores_file):
            continue

        with open(scores_file, 'r') as f:
            scores = json.load(f)

        # Extract high-scoring runs
        for run_id, run_data in scores.items():
            if run_data.get('score', 0) >= min_score and run_data.get('initial_strategy'):
                strategy_name = run_data['initial_strategy']

                # Skip if we've already seen this strategy
                if strategy_name in seen_strategies:
                    continue
                seen_strategies.add(strategy_name)

                # Load the full run log to get strategy details
                run_files = [f for f in os.listdir(log_dir) if f.startswith(f"{run_id}_") and f.endswith('.json')]
                if run_files:
                    run_file = os.path.join(log_dir, run_files[0])
                    with open(run_file, 'r') as f:
                        run_log = json.load(f)

                    if run_log.get('initial_strategy_used'):
                        strategy_data = run_log['initial_strategy_used']
                        best_strategies.append(InitialStrategy(
                            strategy=strategy_data['strategy'],
                            approach=strategy_data['approach'],
                            rationale=strategy_data['rationale']
                        ))

    return best_strategies

