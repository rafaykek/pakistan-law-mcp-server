"""
Law Agent Implementation
========================
Connects to the Pakistan Law MCP Server via standard input/output (stdio)
as an MCP client, discovers exposed tools dynamically, and orchestrates
the AI model's tool calls and conversation context.

Educational Architecture:
  User -> Terminal Chat (app.py)
       -> Law Agent (agents/law_agent.py)
       -> MCP Client Session
       -> Pakistan Law MCP Server (mcp/server.py)
       -> Tools -> External / Official Legal Sources
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

import json
import asyncio
from contextlib import AsyncExitStack

from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Ensure project root is in sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.abspath(os.path.join(_current_dir, ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Load environment variables
load_dotenv()

# Safely import the installed MCP SDK from site-packages
_orig_path = list(sys.path)
_mcp_local_dir = os.path.join(_project_root, "mcp")
sys.path = [p for p in sys.path if os.path.abspath(p or ".") not in (_mcp_local_dir, _project_root)]
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
finally:
    sys.path = _orig_path

# Import OpenAI client
try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None


SYSTEM_PROMPT = """You are the Pakistan Law AI Assistant, an educational legal intelligence agent.
Your primary role is to assist students and researchers in exploring Pakistani law, statutes, and judicial precedents.

You have access to tools exposed through a Model Context Protocol (MCP) server:
1. `get_law_section`: Retrieve verified text and details for a specific section (e.g. Section 489-F of PPC, Section 20 of PECA).
2. `search_law`: Search for Pakistani statutes, acts, ordinances, or legal concepts (e.g. cyber harassment, bail laws, offences against women).
3. `search_judgments`: Search for Pakistani court cases, Supreme Court / High Court decisions, and case law precedents.
4. `search_google`: Perform broad web searches for recent developments, current year news, or general web inquiries.

CRITICAL INSTRUCTIONS & BEHAVIOR:
- DO NOT blindly invoke all four tools. Intelligently select only the relevant tool(s) based on the user's specific request.
  * If the user asks about a specific section (e.g. "What is Section 489-F?"), use `get_law_section`.
  * If the user asks what Pakistani law says about a topic, use `search_law`.
  * If the user asks about court cases, judgments, or precedents, use `search_judgments`.
  * If the user asks for recent developments or general web search, use `search_google`.
- EFFICIENCY & SYNTHESIS: Call only the directly relevant tool(s). Once you receive the tool output, immediately synthesize and deliver your final, well-structured answer. Do not make repetitive or redundant tool calls.
- NEVER fabricate legal sections, court cases, citations, or legal text. If a section or case cannot be verified, state this clearly.
- Provide source URLs for citations whenever available from tool results.
- Distinguish clearly between verified statutory law and general web information.
- ALWAYS include this mandatory educational disclaimer at the end of substantive legal answers:
  "Note: This is general legal information for educational purposes and is not legal advice. Verify the cited law or consult a qualified Pakistani lawyer for advice about a specific situation."
"""



class LawAgent:
    """AI Law Agent communicating with the Pakistan Law MCP Server."""

    def __init__(self, model_name: Optional[str] = None):
        llm_provider = os.getenv("LLM_PROVIDER", "").strip().lower()
        groq_key = os.getenv("GROQ_API_KEY", "").strip()
        openai_key = os.getenv("OPENAI_API_KEY", "").strip()

        if llm_provider == "groq" or (groq_key and not openai_key):
            self.provider = "groq"
            self.api_key = groq_key
            self.model = model_name or os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()
            self.client = AsyncOpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=self.api_key
            ) if (self.api_key and AsyncOpenAI) else None
        else:
            self.provider = "openai"
            self.api_key = openai_key
            self.model = model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
            self.client = AsyncOpenAI(
                api_key=self.api_key
            ) if (self.api_key and AsyncOpenAI) else None
        
        self.exit_stack = AsyncExitStack()
        self.session: Optional[ClientSession] = None
        self.openai_tools: List[Dict[str, Any]] = []
        self.discovered_tools: List[Dict[str, Any]] = []
        
        # In-memory session conversation history
        self.messages: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]


    async def connect(self, server_path: Optional[str] = None) -> bool:
        """Connect to the Pakistan Law MCP Server via stdio and discover tools."""
        if not server_path:
            server_path = os.path.abspath(os.path.join(_project_root, "mcp", "server.py"))

        if not os.path.exists(server_path):
            raise FileNotFoundError(f"MCP server script not found at: {server_path}")

        server_params = StdioServerParameters(
            command=sys.executable,
            args=[server_path],
            env=os.environ.copy()
        )

        try:
            # Establish stdio client connection to the MCP server
            read_stream, write_stream = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await self.session.initialize()

            # Dynamically discover tools from the MCP server
            tools_response = await self.session.list_tools()
            self.discovered_tools = []
            self.openai_tools = []

            for t in tools_response.tools:
                schema = getattr(t, "input_schema", getattr(t, "inputSchema", {}))
                if hasattr(schema, "model_dump"):
                    schema = schema.model_dump()
                
                tool_info = {
                    "name": t.name,
                    "description": t.description or ""
                }
                self.discovered_tools.append(tool_info)

                # Format tool definition for OpenAI function calling
                self.openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": schema or {"type": "object", "properties": {}}
                    }
                })

            return True

        except Exception as exc:
            print(f"[Error] Failed to connect to MCP server: {exc}")
            return False

    def print_available_tools(self) -> None:
        """Display discovered MCP tools for teaching transparency."""
        print("Connected to MCP server.\n", flush=True)
        print("Available tools:", flush=True)
        for t in self.discovered_tools:
            print(f"- {t['name']}", flush=True)
        print(flush=True)


    async def chat(self, user_query: str) -> str:
        """
        Process a user question through the Agent -> MCP -> LLM loop.
        Maintains conversation history within the current session.
        """
        if not self.api_key:
            return (
                "[Configuration Notice] Neither GROQ_API_KEY nor OPENAI_API_KEY is configured.\n"
                "Please configure GROQ_API_KEY (or OPENAI_API_KEY) in your .env file.\n\n"
                "Note: The MCP server is connected and its tools (search_law, search_google, "
                "get_law_section, search_judgments) are ready to be used once an API key is provided."
            )

        if not self.session:
            return "[Error] Agent is not connected to the MCP server. Call connect() first."

        # Append user message to conversation memory
        self.messages.append({"role": "user", "content": user_query})

        # Agentic Tool-calling Loop
        max_turns = 3
        turn = 0

        while turn < max_turns:
            turn += 1
            # If we've already done tool execution turns, disable further tools to force final synthesis
            allow_tools = (turn < max_turns) and bool(self.openai_tools)

            call_kwargs = {
                "model": self.model,
                "messages": self.messages,
            }
            if allow_tools and self.openai_tools:
                call_kwargs["tools"] = self.openai_tools
                call_kwargs["tool_choice"] = "auto"

            try:
                response = await self.client.chat.completions.create(**call_kwargs)


            except Exception as e:
                error_msg = f"LLM Error: {str(e)}"
                return error_msg

            choice = response.choices[0]
            message = choice.message

            # Check if LLM requested one or more tool calls
            if message.tool_calls and allow_tools:
                # Add assistant message with tool calls to history
                tool_calls_data = []
                for tc in message.tool_calls:
                    tool_calls_data.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    })

                self.messages.append({
                    "role": "assistant",
                    "content": message.content or None,
                    "tool_calls": tool_calls_data
                })

                for tc in message.tool_calls:
                    func_name = tc.function.name
                    raw_args = tc.function.arguments or "{}"
                    try:
                        args = json.loads(raw_args)
                    except json.JSONDecodeError:
                        args = {}

                    # Subtle teaching terminal feedback as requested
                    print(f"\n[Agent -> MCP] {func_name}", flush=True)

                    # Execute tool call over MCP protocol
                    try:
                        mcp_result = await self.session.call_tool(func_name, args)
                        print(f"[MCP -> Agent] Tool result received", flush=True)

                        # Extract text from MCP tool result
                        text_parts = []
                        if hasattr(mcp_result, "content") and mcp_result.content:
                            for item in mcp_result.content:
                                if hasattr(item, "text"):
                                    text_parts.append(item.text)
                        
                        tool_output = "\n".join(text_parts) if text_parts else str(mcp_result)
                    except Exception as tool_err:
                        print(f"[MCP -> Agent] Tool execution error: {tool_err}", flush=True)
                        tool_output = f"Error calling tool {func_name}: {str(tool_err)}"

                    # Add tool response back to conversation context
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": tool_output
                    })
            else:
                # No further tool calls: LLM returned final synthesized answer
                final_answer = message.content or ""
                self.messages.append({"role": "assistant", "content": final_answer})
                return final_answer

        return "Agent completed tool retrieval."


    async def close(self) -> None:
        """Gracefully disconnect from the MCP server."""
        if self.exit_stack:
            await self.exit_stack.aclose()
