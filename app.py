"""
Pakistan Law AI Assistant - Terminal Chat Interface
===================================================
A clean, classroom-friendly terminal chat demonstrating:
  User -> Terminal Chat (app.py)
       -> Law Agent (agents/law_agent.py)
       -> MCP Client
       -> Pakistan Law MCP Server (mcp/server.py)
       -> External / Legal Sources

Run with:
  python app.py
"""

import os
import sys

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import asyncio
from dotenv import load_dotenv
from agents.law_agent import LawAgent


# Load environment configuration from .env
load_dotenv()


def print_banner():
    banner = """
========================================
      Pakistan Law AI Assistant
========================================

Ask a question about Pakistani law.
Type 'exit' to quit.
"""
    print(banner.strip())
    print()


async def prompt_user_async(prompt_text: str = "You: ") -> str:
    """Read user input asynchronously without blocking the event loop."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, input, prompt_text)


async def main():
    # 1. Check for API key configuration
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    serper_key = os.getenv("SERPER_API_KEY", "").strip()

    if not groq_key and not openai_key:
        print("\n[Notice] Neither GROQ_API_KEY nor OPENAI_API_KEY is configured in .env.")
        print("To enable AI responses, edit your .env file with your API key:\n")


    if not serper_key:
        print("[Notice] 'SERPER_API_KEY' is not set. The assistant will utilize verified")
        print("statutory law repositories. Add SERPER_API_KEY to enable live web searches.\n")

    # 2. Initialize Agent and Connect to MCP Server
    agent = LawAgent()
    try:
        connected = await agent.connect()
        if not connected:
            print("[Error] Could not establish connection to the Pakistan Law MCP Server.")
            return
    except Exception as err:
        print(f"[Fatal Error] Failed to start MCP Server: {err}")
        return

    # 3. Display banner and discovered tools for classroom transparency
    print_banner()
    agent.print_available_tools()

    # 4. Interactive Chat Loop
    try:
        while True:
            try:
                user_input = await prompt_user_async("You: ")
            except (KeyboardInterrupt, EOFError):
                print("\n\nSession terminated by user.")
                break

            cleaned = user_input.strip()
            if not cleaned:
                continue

            if cleaned.lower() in ("exit", "quit", "q"):
                print("\nExiting Pakistan Law AI Assistant. Goodbye!")
                break

            # Send question to Agent (which uses MCP tools via MCP protocol)
            try:
                response = await agent.chat(cleaned)
                print(f"\nAgent:\n{response}\n")
            except Exception as e:
                print(f"\n[Error] Unable to process request: {e}\n")

    finally:
        # Gracefully shutdown MCP connection
        await agent.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProcess interrupted. Goodbye!")
