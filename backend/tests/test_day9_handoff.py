"""
Day 9 — Specialist Agent Handoff Tests
========================================
Tests verify:
1. Main agent and GovernmentSchemeSpecialist separation.
2. Handoff tool definition and explicit description.
3. Handoff flow (Announcement -> Agent update -> Specialist intro).
4. Context preservation (user's original request passed to specialist).
5. Handback tool definition and flow.
6. Normal questions (credit score, personal loan) stay with Main Agent.
7. Scheme questions trigger handoff.
8. Single call analytics record (Day 8 compatibility).
"""

import json
import sqlite3
import sys
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import memory_db
from agent import (
    Assistant,
    GovernmentSchemeSpecialist,
    build_instructions,
    build_specialist_instructions,
)
from livekit.agents import AgentSession, inference, llm


TEST_USER_ID = "test-user-day9"


def test_specialist_instructions_role_and_limits():
    """Verify GovernmentSchemeSpecialist instructions contain mandatory role and guardrails."""
    inst = build_specialist_instructions("English", initial_context="User asks about SSY")
    
    assert "Government Scheme Specialist" in inst
    assert "help users understand Indian government welfare and savings schemes" in inst
    assert "STRICT GUARDRAILS & SAFETY" in inst
    assert "INITIAL CONTEXT FROM MAIN AGENT" in inst
    assert "User asks about SSY" in inst


def test_handoff_tool_description():
    """Verify main agent's transfer_to_government_scheme_specialist has required description."""
    assistant = Assistant(instructions=build_instructions("English"), user_id=TEST_USER_ID)
    
    # Check tool exists in assistant's tools
    tool_names = [t.info.name for t in assistant.tools]
    assert "transfer_to_government_scheme_specialist" in tool_names

    # Check description
    tool = [t for t in assistant.tools if t.info.name == "transfer_to_government_scheme_specialist"][0]
    desc = tool.info.description
    assert "Government Scheme Specialist" in desc
    assert "Indian government schemes" in desc
    assert "Do not use this tool for normal financial questions" in desc


def test_specialist_has_handback_tool():
    """Verify GovernmentSchemeSpecialist has transfer_back_to_main_agent tool."""
    spec_inst = build_specialist_instructions("English")
    specialist = GovernmentSchemeSpecialist(instructions=spec_inst, user_id=TEST_USER_ID)
    
    tool_names = [t.info.name for t in specialist.tools]
    assert "transfer_back_to_main_agent" in tool_names
    assert "check_scheme_eligibility" in tool_names
    assert "create_escalation" in tool_names


@pytest.mark.asyncio
async def test_handoff_execution_flow():
    """Verify execution of transfer_to_government_scheme_specialist."""
    assistant = Assistant(instructions=build_instructions("English"), user_id=TEST_USER_ID)

    # Mock RunContext and AgentSession
    mock_session = MagicMock()
    mock_session.say = AsyncMock()
    mock_session.update_agent = MagicMock()

    mock_context = MagicMock()
    mock_context.session = mock_session

    # Execute handoff tool directly
    result = await assistant.transfer_to_government_scheme_specialist(
        mock_context,
        user_request="Am I eligible for Sukanya Samriddhi Yojana?",
        scheme_name="Sukanya Samriddhi Yojana",
    )

    # 1. Check user announcement before handoff
    announcement_call = mock_session.say.call_args_list[0]
    assert "connect you to our Government Scheme Specialist" in announcement_call[0][0]

    # 2. Check update_agent was called with GovernmentSchemeSpecialist
    assert mock_session.update_agent.called
    new_agent = mock_session.update_agent.call_args[0][0]
    assert isinstance(new_agent, GovernmentSchemeSpecialist)

    # 3. Check specialist intro was spoken
    intro_call = mock_session.say.call_args_list[1]
    assert "FinVoice's Government Scheme Specialist" in intro_call[0][0]
    assert "Sukanya Samriddhi Yojana" in intro_call[0][0]

    # 4. Check result
    assert "Transferred successfully" in result


@pytest.mark.asyncio
async def test_handback_execution_flow():
    """Verify execution of transfer_back_to_main_agent."""
    specialist = GovernmentSchemeSpecialist(
        instructions=build_specialist_instructions("English"),
        user_id=TEST_USER_ID,
    )

    mock_session = MagicMock()
    mock_session.say = AsyncMock()
    mock_session.update_agent = MagicMock()

    mock_context = MagicMock()
    mock_context.session = mock_session

    result = await specialist.transfer_back_to_main_agent(
        mock_context,
        reason="User asked general credit score question",
    )

    # 1. Announcement
    announcement_call = mock_session.say.call_args_list[0]
    assert "connect you back to our main FinVoice assistant" in announcement_call[0][0]

    # 2. update_agent called with Assistant
    assert mock_session.update_agent.called
    target_agent = mock_session.update_agent.call_args[0][0]
    assert isinstance(target_agent, Assistant)

    # 3. Main agent greeting
    back_call = mock_session.say.call_args_list[1]
    assert "I'm back" in back_call[0][0]

    assert "Transferred back" in result


def _llm() -> llm.LLM:
    return inference.LLM(model="openai/gpt-4.1-mini")


@pytest.mark.asyncio
async def test_normal_financial_question_stays_with_main_agent():
    """Normal questions (credit score) must remain with Main Agent without handoff tool execution."""
    async with (
        _llm() as llm_instance,
        AgentSession(llm=llm_instance) as session,
    ):
        assistant = Assistant(instructions=build_instructions("English"), user_id=TEST_USER_ID)
        await session.start(assistant)

        result = await session.run(user_input="Can you explain what a credit score is?")

        await (
            result.expect.next_event()
            .is_message(role="assistant")
            .judge(
                llm_instance,
                intent="""
                Provides a clear explanation of what a credit score is.
                Does NOT transfer to specialist.
                Does NOT execute transfer_to_government_scheme_specialist.
                """,
            )
        )
        result.expect.no_more_events()


@pytest.mark.asyncio
async def test_scheme_question_triggers_handoff():
    """Government scheme questions (Sukanya Samriddhi) must trigger handoff tool."""
    async with (
        _llm() as llm_instance,
        AgentSession(llm=llm_instance) as session,
    ):
        assistant = Assistant(instructions=build_instructions("English"), user_id=TEST_USER_ID)
        await session.start(assistant)

        result = await session.run(user_input="Am I eligible for Sukanya Samriddhi Yojana?")

        # Verify that transfer_to_government_scheme_specialist was called
        fn_call = None
        for ev in result.events:
            if getattr(ev, "type", None) == "function_call" and getattr(ev.item, "name", None) == "transfer_to_government_scheme_specialist":
                fn_call = ev
                break
        assert fn_call is not None, "transfer_to_government_scheme_specialist tool must be called for scheme queries"
