import asyncio
from datetime import datetime
from typing import List, Optional, Dict
import concurrent.futures

from models import (
    PasswordAgentResponse, AdversarialAgentResponse, StrategyAnalysis,
    EvaluationResult, ConversationTurn, RunLog, InitialStrategy
)
from prompt import (
    get_password_agent_prompt, get_adversarial_agent_prompt,
    get_strategizer_prompt, get_evaluator_prompt, get_strategy_context,
    get_initial_strategy_prompt
)
from utils import (
    create_logs_directory, save_run_log, save_score,
    format_runs_for_analysis, format_conversation_for_evaluation,
    print_run_header, print_turn_info, print_adversarial_info,
    print_password_response, print_evaluation_header, print_evaluation_results,
    print_strategy_header, print_strategy_recommendations, print_pipeline_complete,
    print_pipeline_start, call_openai_structured, call_openai_structured_async,
    STRONG_MODEL, WEAK_MODEL
)


class PasswordAgent:
    """Agent that protects a password"""

    def __init__(self, password: str):
        self.password = password
        self.system_prompt = get_password_agent_prompt(password)

    async def respond_async(self, message: str) -> PasswordAgentResponse:
        """Generate a response to an adversarial message (async)"""
        response = await call_openai_structured_async(
            model=WEAK_MODEL,  # Use weaker model for password agent
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": message}
            ],
            response_format=PasswordAgentResponse,
            temperature=0.7
        )

        return response

    def respond(self, message: str) -> PasswordAgentResponse:
        """Generate a response to an adversarial message (sync)"""
        response = call_openai_structured(
            model=WEAK_MODEL,  # Use weaker model for password agent
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": message}
            ],
            response_format=PasswordAgentResponse,
            temperature=0.7
        )

        return response


class AdversarialAgent:
    """Agent that tries to extract the password"""

    def __init__(self):
        self.system_prompt = get_adversarial_agent_prompt()

    async def generate_message_async(self, conversation_history: List[Dict[str, str]] = None,
                        strategy_analysis: StrategyAnalysis = None,
                        initial_strategy: InitialStrategy = None) -> AdversarialAgentResponse:
        """Generate a message to send to the password agent (async)"""
        messages = [{"role": "system", "content": self.system_prompt}]

        # Add initial strategy if this is the first message and we have one
        if initial_strategy and not conversation_history:
            messages.append({"role": "system", "content": f"Use this specific strategy: {initial_strategy.strategy}\nApproach: {initial_strategy.approach}"})
        # Add strategy recommendations if available
        elif strategy_analysis:
            messages.append({"role": "system", "content": get_strategy_context(strategy_analysis)})

        # Add conversation history
        if conversation_history:
            for turn in conversation_history:
                messages.append({"role": "assistant", "content": turn["adversarial"]})
                messages.append({"role": "user", "content": turn["password"]})

        return await call_openai_structured_async(
            model=STRONG_MODEL,  # Use stronger model for adversary
            messages=messages,
            response_format=AdversarialAgentResponse,
            temperature=0.8
        )

    def generate_message(self, conversation_history: List[Dict[str, str]] = None,
                        strategy_analysis: StrategyAnalysis = None,
                        initial_strategy: InitialStrategy = None) -> AdversarialAgentResponse:
        """Generate a message to send to the password agent (sync)"""
        messages = [{"role": "system", "content": self.system_prompt}]

        # Add initial strategy if this is the first message and we have one
        if initial_strategy and not conversation_history:
            messages.append({"role": "system", "content": f"Use this specific strategy: {initial_strategy.strategy}\nApproach: {initial_strategy.approach}"})
        # Add strategy recommendations if available
        elif strategy_analysis:
            messages.append({"role": "system", "content": get_strategy_context(strategy_analysis)})

        # Add conversation history
        if conversation_history:
            for turn in conversation_history:
                messages.append({"role": "assistant", "content": turn["adversarial"]})
                messages.append({"role": "user", "content": turn["password"]})

        return call_openai_structured(
            model=STRONG_MODEL,  # Use stronger model for adversary
            messages=messages,
            response_format=AdversarialAgentResponse,
            temperature=0.8
        )


class LLMStrategizer:
    """Analyzes previous runs and suggests strategies"""

    def __init__(self):
        self.system_prompt = get_strategizer_prompt()

    def analyze_runs(self, previous_runs: List[RunLog]) -> StrategyAnalysis:
        """Analyze ALL previous runs and generate strategy recommendations"""
        context = format_runs_for_analysis(previous_runs)

        return call_openai_structured(
            model=STRONG_MODEL,  # Use stronger model for analysis
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": context}
            ],
            response_format=StrategyAnalysis,
            temperature=0.7
        )


    def generate_initial_strategies(self, num_strategies: int = 10) -> List[InitialStrategy]:
        """Generate initial strategies using best performers from previous runs"""
        # First, try to load best strategies from logs
        from utils import load_best_strategies_from_logs

        best_strategies = load_best_strategies_from_logs()

        if best_strategies:
            print(f"Loaded {len(best_strategies)} best-performing strategies from logs")
            # If we have more than requested, take a subset
            if len(best_strategies) > num_strategies:
                return best_strategies[:num_strategies]
            # If we have fewer, generate additional ones to fill the gap
            elif len(best_strategies) < num_strategies:
                print(f"Generating {num_strategies - len(best_strategies)} additional strategies")
                prompt = get_initial_strategy_prompt()

                for i in range(num_strategies - len(best_strategies)):
                    strategy = call_openai_structured(
                        model=STRONG_MODEL,
                        messages=[
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": f"Generate strategy {i+1}. Make it unique and different from typical approaches. Be creative!"}
                        ],
                        response_format=InitialStrategy,
                        temperature=0.9
                    )
                    best_strategies.append(strategy)

                return best_strategies
            else:
                return best_strategies
        else:
            # Fallback to original behavior if no logs found
            print("No previous strategies found, generating new ones")
            strategies = []
            prompt = get_initial_strategy_prompt()

            for i in range(num_strategies):
                strategy = call_openai_structured(
                    model=STRONG_MODEL,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": f"Generate strategy {i+1} of {num_strategies}. Make it unique and different from typical approaches. Be creative!"}
                    ],
                    response_format=InitialStrategy,
                    temperature=0.9
                )
                strategies.append(strategy)

            return strategies


class LLMEvaluator:
    """Evaluates the performance of the adversarial agent"""

    def __init__(self, password: str):
        self.password = password
        self.system_prompt = get_evaluator_prompt(password)

    async def evaluate_run_async(self, run_log: RunLog) -> EvaluationResult:
        """Evaluate a single run (async)"""
        conversation_text = format_conversation_for_evaluation(run_log)

        return await call_openai_structured_async(
            model=STRONG_MODEL,  # Use stronger model for evaluation
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Evaluate this conversation:\n\n{conversation_text}"}
            ],
            response_format=EvaluationResult,
            temperature=0.6
        )

    def evaluate_run(self, run_log: RunLog) -> EvaluationResult:
        """Evaluate a single run (sync)"""
        conversation_text = format_conversation_for_evaluation(run_log)

        return call_openai_structured(
            model=STRONG_MODEL,  # Use stronger model for evaluation
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Evaluate this conversation:\n\n{conversation_text}"}
            ],
            response_format=EvaluationResult,
            temperature=0.6
        )


class AdversarialPipeline:
    """Main pipeline orchestrating the adversarial password game"""

    def __init__(self, password: str, max_turns: int = 10):
        self.password = password
        self.max_turns = max_turns
        self.password_agent = PasswordAgent(password)
        self.adversarial_agent = AdversarialAgent()
        self.strategizer = LLMStrategizer()
        self.evaluator = LLMEvaluator(password)
        self.runs: List[RunLog] = []
        self.initial_strategies: List[InitialStrategy] = []

        # Create logs directory
        create_logs_directory()

    async def run_single_attempt_async(self, run_id: int, strategy_analysis: Optional[StrategyAnalysis] = None,
                                      initial_strategy: Optional[InitialStrategy] = None) -> RunLog:
        """Execute a single run between agents (async)"""
        print_run_header(run_id)

        if initial_strategy:
            print(f"Using initial strategy: {initial_strategy.strategy}")

        conversation = []
        conversation_history = []

        for turn in range(self.max_turns):
            print_turn_info(turn + 1, self.max_turns)

            # Adversarial agent generates message
            adv_response = await self.adversarial_agent.generate_message_async(
                conversation_history=conversation_history,
                strategy_analysis=strategy_analysis,
                initial_strategy=initial_strategy if turn == 0 else None
            )
            print_adversarial_info(adv_response.message, adv_response.strategy)

            # Password agent responds
            pwd_response = await self.password_agent.respond_async(adv_response.message)
            print_password_response(pwd_response.reply)

            # Record the turn
            turn_log = ConversationTurn(
                turn_number=turn + 1,
                adversarial_message=adv_response.message,
                password_response=pwd_response.reply,
                adversarial_strategy=adv_response.strategy
            )
            conversation.append(turn_log)

            # Update conversation history
            conversation_history.append({
                "adversarial": adv_response.message,
                "password": pwd_response.reply
            })

        # Create run log
        run_log = RunLog(
            run_id=run_id,
            timestamp=datetime.now().isoformat(),
            conversation=conversation,
            strategy_used=strategy_analysis,
            initial_strategy_used=initial_strategy
        )

        return run_log

    def run_single_attempt(self, run_id: int, strategy_analysis: Optional[StrategyAnalysis] = None,
                          initial_strategy: Optional[InitialStrategy] = None) -> RunLog:
        """Execute a single run between agents (sync)"""
        print_run_header(run_id)

        if initial_strategy:
            print(f"Using initial strategy: {initial_strategy.strategy}")

        conversation = []
        conversation_history = []

        for turn in range(self.max_turns):
            print_turn_info(turn + 1, self.max_turns)

            # Adversarial agent generates message
            adv_response = self.adversarial_agent.generate_message(
                conversation_history=conversation_history,
                strategy_analysis=strategy_analysis,
                initial_strategy=initial_strategy if turn == 0 else None
            )
            print_adversarial_info(adv_response.message, adv_response.strategy)

            # Password agent responds
            pwd_response = self.password_agent.respond(adv_response.message)
            print_password_response(pwd_response.reply)

            # Record the turn
            turn_log = ConversationTurn(
                turn_number=turn + 1,
                adversarial_message=adv_response.message,
                password_response=pwd_response.reply,
                adversarial_strategy=adv_response.strategy
            )
            conversation.append(turn_log)

            # Update conversation history
            conversation_history.append({
                "adversarial": adv_response.message,
                "password": pwd_response.reply
            })

        # Create run log
        run_log = RunLog(
            run_id=run_id,
            timestamp=datetime.now().isoformat(),
            conversation=conversation,
            strategy_used=strategy_analysis,
            initial_strategy_used=initial_strategy
        )

        return run_log

    async def evaluate_and_save_run_async(self, run_log: RunLog):
        """Evaluate a run and save it to disk (async)"""
        print_evaluation_header(run_log.run_id)

        # Evaluate the run
        evaluation = await self.evaluator.evaluate_run_async(run_log)
        run_log.evaluation = evaluation

        print_evaluation_results(evaluation)

        # Save run log
        filename = save_run_log(run_log)
        print(f"\nRun saved to: {filename}")

        # Save score
        save_score(run_log)

    def evaluate_and_save_run(self, run_log: RunLog):
        """Evaluate a run and save it to disk (sync)"""
        print_evaluation_header(run_log.run_id)

        # Evaluate the run
        evaluation = self.evaluator.evaluate_run(run_log)
        run_log.evaluation = evaluation

        print_evaluation_results(evaluation)

        # Save run log
        filename = save_run_log(run_log)
        print(f"\nRun saved to: {filename}")

        # Save score
        save_score(run_log)

    async def run_concurrent_initial_strategies(self, num_strategies: int = 10):
        """Run multiple initial strategies concurrently"""
        print(f"\n=== Generating {num_strategies} Initial Strategies ===")

        # Generate diverse initial strategies
        self.initial_strategies = self.strategizer.generate_initial_strategies(num_strategies)

        print(f"\n=== Running {num_strategies} Concurrent Initial Attempts ===")

        # Run all strategies concurrently
        tasks = []
        for i, strategy in enumerate(self.initial_strategies):
            task = self.run_single_attempt_async(i + 1, initial_strategy=strategy)
            tasks.append(task)

        # Wait for all runs to complete
        run_logs = await asyncio.gather(*tasks)

        # Evaluate and save all runs
        eval_tasks = []
        for run_log in run_logs:
            eval_task = self.evaluate_and_save_run_async(run_log)
            eval_tasks.append(eval_task)

        await asyncio.gather(*eval_tasks)

        # Add to runs history
        self.runs.extend(run_logs)

        # Print summary
        print(f"\n=== Initial Strategy Results ===")
        for i, run_log in enumerate(run_logs):
            score = run_log.evaluation.score if run_log.evaluation else "N/A"
            print(f"Strategy {i+1}: Score {score}/10")

    def run_multiple_attempts(self, num_runs: int = 3, use_async_initial: bool = True):
        """Run multiple attempts with strategy refinement between runs"""
        print_pipeline_start(self.password, num_runs, self.max_turns)

        # Run initial concurrent strategies if requested
        if use_async_initial:
            asyncio.run(self.run_concurrent_initial_strategies())

        # Continue with regular runs using learned strategies
        for run_id in range(len(self.runs) + 1, len(self.runs) + num_runs + 1):
            # Generate strategy based on ALL previous runs
            strategy_analysis = None
            if self.runs:
                print_strategy_header(run_id)
                strategy_analysis = self.strategizer.analyze_runs(self.runs)
                print_strategy_recommendations(strategy_analysis.recommended_strategies)
                print(f"Analyzing {len(self.runs)} previous runs...")

            # Run the attempt
            run_log = self.run_single_attempt(run_id, strategy_analysis)

            # Evaluate and save
            self.evaluate_and_save_run(run_log)

            # Add to runs history
            self.runs.append(run_log)

        print_pipeline_complete()

    async def run_multiple_attempts_async(self, num_runs: int = 3, concurrent_batch_size: int = 5):
        """Run multiple attempts with async batching"""
        print_pipeline_start(self.password, num_runs, self.max_turns)

        # First, run initial strategies
        await self.run_concurrent_initial_strategies()

        # Then run additional attempts in batches
        remaining_runs = num_runs
        while remaining_runs > 0:
            batch_size = min(concurrent_batch_size, remaining_runs)

            # Generate strategies for this batch
            if self.runs:
                print(f"\n=== Generating Strategies Based on {len(self.runs)} Previous Runs ===")
                strategy_analysis = self.strategizer.analyze_runs(self.runs)
                print_strategy_recommendations(strategy_analysis.recommended_strategies)
            else:
                strategy_analysis = None

            # Run batch concurrently
            tasks = []
            start_id = len(self.runs) + 1
            for i in range(batch_size):
                task = self.run_single_attempt_async(start_id + i, strategy_analysis)
                tasks.append(task)

            run_logs = await asyncio.gather(*tasks)

            # Evaluate batch
            eval_tasks = []
            for run_log in run_logs:
                eval_task = self.evaluate_and_save_run_async(run_log)
                eval_tasks.append(eval_task)

            await asyncio.gather(*eval_tasks)

            # Add to history
            self.runs.extend(run_logs)
            remaining_runs -= batch_size

        print_pipeline_complete()


# Example usage
if __name__ == "__main__":
    # Initialize pipeline with a password
    pipeline = AdversarialPipeline(
        password="MOLLY",
        max_turns=10
    )

    # Option 1: Run with async initial strategies + regular sequential runs
    # pipeline.run_multiple_attempts(num_runs=3, use_async_initial=True)

    # Option 2: Run fully async with batching
    asyncio.run(pipeline.run_multiple_attempts_async(num_runs=5, concurrent_batch_size=3))
