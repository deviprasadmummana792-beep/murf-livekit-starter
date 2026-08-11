import json
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    tokenize,
    room_io,
    function_tool,
    RunContext,
)
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel
import asyncio

# Ensure src directory is in sys.path
src_dir = Path(__file__).resolve().parent.parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import memory_db
import schemes_checker

logger = logging.getLogger("outbound_agent")

# Load environment variables
load_dotenv(src_dir.parent / ".env.local")
load_dotenv(".env.local")

OUTBOUND_INSTRUCTIONS = """You are FinVoice, a friendly, empathetic, and highly knowledgeable AI Financial Services Voice Assistant for Indian citizens.

OUTBOUND CALL CONTEXT & MISSION:
- You are making an OUTBOUND call to a user who is eligible/registered for key financial schemes (such as PM-Kisan, Atal Pension Yojana, PM Jan Dhan Yojana, or Sukanya Samriddhi Yojana).
- Your primary mission on this call is to remind them about an upcoming financial scheme deadline (e.g., the PM-Kisan bank account linking / e-KYC deadline of August 31st).

MANDATORY OUTBOUND OPENING:
- You MUST begin the conversation by clearly stating:
  1. Who is calling (FinVoice, an AI financial information assistant).
  2. Why the call is being made (to remind them about an upcoming financial scheme deadline).
  3. That the user can end or decline the call at any time if they do not wish to continue.
- Opening sentence: "Hello, this is FinVoice, an AI financial information assistant. I'm calling to remind you about an upcoming financial scheme deadline; you can end this call at any time if you don't want to continue."

STRICT FINANCIAL SAFETY & GUARDRAILS (NEVER VIOLATE):
- NEVER ask for, collect, or process confidential credentials: OTP, ATM PIN, CVV, Password, Aadhaar Number, PAN Number, or Bank Account Number.
- IF A USER SHARES SENSITIVE INFORMATION (OTP, PIN, CVV, Password, Aadhaar, Account Number): Immediately warn them never to share sensitive details with anyone and clarify that FinVoice will never ask for them.
- NEVER claim or guarantee loan approval, scheme approval, or financial investment returns.
- NEVER attempt or pretend to perform a financial transaction, money transfer, or account update.
- IF THE USER ASKS FOR AN ACCOUNT-SPECIFIC ACTION OR TRANSACTION: Politely explain that FinVoice cannot access personal bank accounts or execute transactions, and advise them to visit their official bank branch or official portals (e.g., pmkisan.gov.in).
- REFUSE ILLEGAL REQUESTS: Politely decline any illegal financial request.

OPT-OUT & END CALL HANDLING:
- If the user indicates they do not want to continue, wish to decline, say goodbye, or ask to end the call, politely say: "Thank you for your time. Have a wonderful day! Goodbye." and end the session.

VOICE OUTPUT FORMATTING (CRITICAL FOR MUTE/TTS):
- Keep responses extremely short: Maximum 2 to 3 concise sentences.
- Speak naturally and warmly.
- ABSOLUTELY NO bullet lists, NO numbered lists, NO markdown symbols, NO emojis.
"""


class OutboundAssistant(Agent):
    def __init__(self, instructions: str, user_id: str) -> None:
        super().__init__(instructions=instructions)
        self._user_id = user_id

    @function_tool
    async def lookup_user(
        self,
        context: RunContext,
        user_id: str,
    ):
        """Look up a caller's profile from the database."""
        logger.info("[MEMORY] lookup_user called for user_id=%s", user_id)
        profile = memory_db.lookup_user(user_id)
        if profile is None:
            return "No saved profile found."
        return {
            "status": "profile_found",
            "user_id": profile["user_id"],
            "name": profile["name"],
            "language_preference": profile["language_preference"],
            "facts": profile["facts"],
            "last_interaction": profile["last_interaction"],
        }

    @function_tool
    async def save_user_memory(
        self,
        context: RunContext,
        user_id: str,
        name: str | None = None,
        language_preference: str | None = None,
        facts_to_add: str | None = None,
    ):
        """Save non-sensitive information with explicit consent."""
        logger.info(
            "[MEMORY] save_user_memory called: user_id=%s, name=%s", user_id, name
        )
        facts_dict = None
        if facts_to_add:
            try:
                facts_dict = json.loads(facts_to_add)
            except json.JSONDecodeError:
                facts_dict = {"note": facts_to_add}

        success, reason = memory_db.save_user_memory(
            user_id=user_id,
            name=name,
            language_preference=language_preference,
            facts_to_add=facts_dict,
        )

        if not success:
            if "sensitive" in reason:
                return (
                    "I cannot store sensitive information such as OTPs, PINs, or credentials. "
                    "FinVoice never stores sensitive authentication details."
                )
            return f"Memory save failed: {reason}"

        return "Information saved successfully."

    @function_tool
    async def check_scheme_eligibility(
        self,
        context: RunContext,
        scheme_name: str,
        age: int | None = None,
        occupation: str | None = None,
        income_range: str | None = None,
        purpose: str | None = None,
        is_farmer: bool | None = None,
        has_girl_child: bool | None = None,
        girl_child_age: int | None = None,
    ):
        """Check potential eligibility for government financial schemes."""
        res = schemes_checker.check_eligibility(
            scheme_name=scheme_name,
            age=age,
            occupation=occupation,
            income_range=income_range,
            purpose=purpose,
            is_farmer=is_farmer,
            has_girl_child=has_girl_child,
            girl_child_age=girl_child_age,
        )
        return json.dumps(res)

    @function_tool
    async def evaluate_fraud_risk(
        self,
        context: RunContext,
        incident_description: str,
    ):
        """Evaluate if a request or scenario sounds like financial fraud."""
        desc_lower = incident_description.lower()
        suspicious_keywords = [
            "otp",
            "pin",
            "cvv",
            "password",
            "remote access",
            "anydesk",
            "teamviewer",
            "lottery",
            "urgent block",
            "kyc update",
            "click link",
            "refund",
            "aadhaar",
        ]
        if any(kw in desc_lower for kw in suspicious_keywords):
            return "HIGH FRAUD RISK ALERT: Genuine banks and government bodies NEVER request OTPs, PINs, CVVs, passwords, or remote access. Immediately block contact and report to helpline 1930."
        return "POTENTIAL FINANCIAL RISK: Exercise caution. Never share confidential banking details over phone."


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()
    memory_db.init_db()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="my-agent")
async def outbound_agent_session(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}

    logger.info("[OUTBOUND] Agent connecting to room=%s", ctx.room.name)
    await ctx.connect()
    logger.info("[OUTBOUND] Agent connected to room=%s", ctx.room.name)

    logger.info("[OUTBOUND] Waiting for SIP participant to join...")
    participant = await ctx.wait_for_participant()
    user_id = (
        participant.identity if participant and participant.identity else ctx.room.name
    )

    logger.info(
        "[OUTBOUND] SIP participant joined: room=%s, identity=%s, kind=%s",
        ctx.room.name,
        user_id,
        participant.kind,
    )

    greeting = (
        "Hello, this is FinVoice, an AI financial information assistant. "
        "I'm calling to remind you about an upcoming financial scheme deadline; "
        "you can end this call at any time if you don't want to continue."
    )

    instructions = OUTBOUND_INSTRUCTIONS + f"\n\nSESSION USER ID: {user_id}\n"

    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(model="gemini-3.5-flash-lite"),
        tts=murf.TTS(
            voice="en-IN-anusha",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=20),
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=False,
    )

    logger.info("[OUTBOUND] Starting agent session for participant=%s", user_id)
    await session.start(
        agent=OutboundAssistant(instructions=instructions, user_id=user_id),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: (
                    noise_cancellation.BVCTelephony()
                    if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                    else noise_cancellation.BVC()
                ),
            ),
        ),
    )
    logger.info("[OUTBOUND] Agent session started. Inspecting room + waiting for call to be ACTIVE...")

    # ------------------------------------------------------------------
    # Log full room state for diagnosis (participants, tracks, attributes)
    # ------------------------------------------------------------------
    for pid, rp in ctx.room.remote_participants.items():
        attrs = dict(rp.attributes) if rp.attributes else {}
        tracks_info = [(t.sid, t.kind.name) for t in rp.track_publications.values()]
        logger.info(
            "[OUTBOUND] Remote participant: identity=%s kind=%s attrs=%s tracks=%s",
            pid, rp.kind, attrs, tracks_info,
        )

    # ------------------------------------------------------------------
    # Wait for sip.callStatus == "active"
    #
    # WHY SHORT (12s): with wait_until_answered=True in dial.py, the
    # create_sip_participant API already waited for the call to be
    # answered. By the time the agent reaches here, the participant
    # should be active. If the attribute never appears (common for
    # Linphone SIP-URI accounts vs PSTN), we proceed after 12s anyway.
    # A 90s wait causes the user to hear silence for 90s and hang up.
    # ------------------------------------------------------------------
    deadline = asyncio.get_event_loop().time() + 12.0
    answered = False
    while asyncio.get_event_loop().time() < deadline:
        sip_participant = ctx.room.remote_participants.get(participant.identity)
        if sip_participant:
            attrs = dict(sip_participant.attributes) if sip_participant.attributes else {}
            sip_call_status = attrs.get("sip.callStatus", "<not-set>")
            logger.info(
                "[OUTBOUND] sip.callStatus=%s  all_attrs=%s",
                sip_call_status, attrs,
            )
            if sip_call_status == "active":
                logger.info("[OUTBOUND] ✅ sip.callStatus=active — call answered, RTP live.")
                answered = True
                break
            elif sip_call_status in ("disconnected", "hangup", "error"):
                logger.warning("[OUTBOUND] ❌ Call ended before agent spoke (status=%s).", sip_call_status)
                return
        await asyncio.sleep(0.5)

    if not answered:
        logger.warning(
            "[OUTBOUND] sip.callStatus never became 'active' within 12s "
            "(this is normal for Linphone SIP-URI accounts). Proceeding immediately."
        )

    # 1 second to let the SIP bridge's RTP send path fully initialise
    await asyncio.sleep(1.0)

    # ------------------------------------------------------------------
    # Log published tracks at the moment we're about to speak
    # ------------------------------------------------------------------
    for pid, rp in ctx.room.remote_participants.items():
        tracks_info = [(t.sid, t.kind.name, t.subscribed) for t in rp.track_publications.values()]
        logger.info("[OUTBOUND] Tracks at greeting time — %s: %s", pid, tracks_info)
    local_tracks = [(t.sid, t.kind.name) for t in ctx.room.local_participant.track_publications.values()]
    logger.info("[OUTBOUND] Local (agent) published tracks: %s", local_tracks)

    # ------------------------------------------------------------------
    # Deliver greeting — RTP path should now be ready
    # ------------------------------------------------------------------
    logger.info("[OUTBOUND] 🎤 Calling session.say() with Murf TTS...")
    try:
        await session.say(greeting)
        logger.info("[OUTBOUND] ✅ session.say() returned — audio sent to room.")
    except Exception as e:
        logger.error("[OUTBOUND] ❌ session.say() raised: %s", e, exc_info=True)


if __name__ == "__main__":
    cli.run_app(server)

