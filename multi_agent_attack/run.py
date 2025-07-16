# Example usage to run with best strategies from logs

import asyncio
from main import AdversarialPipeline

# Initialize pipeline
pipeline = AdversarialPipeline(
    password="MOLLY",
    max_turns=10
)

# This will automatically load and use the best strategies from your log folders
# The modified generate_initial_strategies() will:
# 1. Look for all logs_* folders and the logs folder
# 2. Extract strategies that scored 10.0
# 3. Use those as initial strategies

# Run with async initial strategies using best performers
asyncio.run(pipeline.run_multiple_attempts_async(num_runs=5, concurrent_batch_size=3))
