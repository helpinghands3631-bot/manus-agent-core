"""Basic usage example for Manus Agent Core.

Demonstrates:
- Creating a BaseAgent with Grok LLM
- Registering custom tools
- Running ReAct loop for autonomous task execution
- Using memory and event system
"""

import asyncio
import os
from agent.core import BaseAgent
from llm.groq import GroqLLM
from tools.base import BaseTool
from config import Config


class CalculatorTool(BaseTool):
    """Example custom tool for mathematical calculations."""
    
    name = "calculator"
    description = "Performs basic mathematical calculations. Input: math expression as string."
    
    async def execute(self, expression: str) -> dict:
        """Execute a mathematical expression."""
        try:
            result = eval(expression)  # In production, use safer alternatives
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}


class WeatherTool(BaseTool):
    """Example tool to fetch weather information (mocked)."""
    
    name = "weather"
    description = "Get current weather for a location. Input: city name."
    
    async def execute(self, city: str) -> dict:
        """Fetch weather for a city (mocked example)."""
        # In production, integrate with real weather API
        mock_data = {
            "temperature": "22°C",
            "condition": "Sunny",
            "humidity": "60%"
        }
        return {
            "success": True,
            "city": city,
            "weather": mock_data
        }


async def main():
    """Run the agent with example tasks."""
    
    # Initialize configuration
    config = Config()
    
    # Create Grok LLM instance
    llm = GroqLLM(
        api_key=config.groq_api_key,
        model=config.llm_model,
        temperature=0.7
    )
    
    # Create agent
    agent = BaseAgent(
        llm=llm,
        max_steps=config.agent_max_steps,
        memory_window=config.agent_memory_window
    )
    
    # Register custom tools
    agent.register_tool(CalculatorTool())
    agent.register_tool(WeatherTool())
    
    print("🤖 Manus Agent Core - Basic Usage Example")
    print("="*50)
    print(f"Available tools: {list(agent.registry.tools.keys())}")
    print("="*50)
    print()
    
    # Example 1: Mathematical task
    print("📊 Task 1: Solve a math problem")
    task1 = "Calculate the result of (15 * 8) + (100 / 4) and tell me the answer"
    result1 = await agent.run(task1)
    print(f"Result: {result1}")
    print()
    
    # Example 2: Information retrieval task
    print("🌤️ Task 2: Get weather information")
    task2 = "What's the weather like in Sydney?"
    result2 = await agent.run(task2)
    print(f"Result: {result2}")
    print()
    
    # Example 3: Multi-step reasoning
    print("🧠 Task 3: Multi-step reasoning")
    task3 = "Calculate 25 * 4, then check the weather in Melbourne, and summarize both results"
    result3 = await agent.run(task3)
    print(f"Result: {result3}")
    print()
    
    # Display agent statistics
    print("="*50)
    print("📊 Agent Statistics:")
    print(f"Total steps taken: {agent.current_step}")
    print(f"Memory size: {len(agent.memory.messages)}")
    print("="*50)


if __name__ == "__main__":
    # Ensure GROQ_API_KEY is set
    if not os.getenv("GROQ_API_KEY"):
        print("❌ Error: GROQ_API_KEY environment variable not set")
        print("Please set it in your .env file or export it:")
        print("  export GROQ_API_KEY='your_api_key_here'")
        exit(1)
    
    # Run the async main function
    asyncio.run(main())
