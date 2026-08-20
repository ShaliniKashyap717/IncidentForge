"""
Basic Google ADK installation test.

Verifies that Google ADK is installed correctly
and that an Agent can be imported and instantiated.
"""

from google.adk.agents import Agent


def main() -> None:
    agent = Agent(
        name="incidentforge_test_agent",
        model="gemini-3.6-flash",
        instruction="You are a test agent for IncidentForge.",
    )

    print("Google ADK import successful.")
    print(f"Agent created successfully: {agent.name}")


if __name__ == "__main__":
    main()