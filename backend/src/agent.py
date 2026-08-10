import json
import logging
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
    inference,
    tokenize,
    room_io,
    function_tool,
    RunContext,
)
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel
try:
    from . import memory_db  # works when loaded as a package
except ImportError:
    import memory_db  # works when run directly: python src/agent.py

try:
    from . import schemes_checker
except ImportError:
    import schemes_checker

logger = logging.getLogger("agent")

load_dotenv(".env.local")

LANGUAGE_CONFIG = {
    "English": {
        "instruction": "Respond ONLY in clear, natural conversational English. Write all text using standard Latin/English script.",
        "greeting_new": "Hello! I'm FinVoice, your AI Financial Support Assistant. I can help you understand banking services, government schemes and stay safe from financial frauds. How may I help you today?",
        "greeting_returning": "Welcome back, {name}! Good to speak with you again. I'm FinVoice, your AI Financial Support Assistant. How can I help you today?",
    },
    "Hindi": {
        "instruction": "Respond ONLY in clear, conversational Hindi using Roman/Latin script (Hinglish / Romanized Hindi). Example: 'Namaste! Main FinVoice hoon, aapka AI financial support assistant.' ABSOLUTELY DO NOT write in Devanagari script (हिंदी) because the text-to-speech engine requires Latin script to pronounce words cleanly.",
        "greeting_new": "Namaste! Main FinVoice hoon, aapka AI financial support assistant. Main aapko banking services aur govt schemes samajhne me help kar sakta hoon. Aaj main aapki kya help kar sakta hoon?",
        "greeting_returning": "Welcome back, {name}! Main FinVoice hoon. Aaj main aapki kya help kar sakta hoon?",
    },
    "Telugu": {
        "instruction": "Respond ONLY in clear, conversational Telugu using Roman/Latin script (Romanized Telugu / Tenglish). Example: 'Namaskaram! Nenu FinVoice, mee AI financial support assistant.' ABSOLUTELY DO NOT write in Telugu script (తెలుగు) because the text-to-speech engine requires Latin script to pronounce words cleanly.",
        "greeting_new": "Namaskaram! Nenu FinVoice, mee AI financial support assistant. Nenu meeku banking services mariyu govt schemes artham cheskovadaniki help cheyagalanu. Eeroju nenu meeku ela help cheyagalanu?",
        "greeting_returning": "Welcome back, {name}! Nenu FinVoice. Eeroju nenu meeku ela help cheyagalanu?",
    },
    "Hinglish": {
        "instruction": "Respond naturally in Hinglish, mixing Hindi and English conversationally using Roman/Latin script.",
        "greeting_new": "Hello! Main FinVoice hoon, aapka AI financial support assistant. Main aapko banking services aur govt schemes samajhne me help kar sakta hoon. Aaj main aapki kya help kar sakta hoon?",
        "greeting_returning": "Welcome back, {name}! Main FinVoice hoon. Aaj main aapki kya help kar sakta hoon?",
    },
}


def build_instructions(language: str) -> str:
    cfg = LANGUAGE_CONFIG.get(language, LANGUAGE_CONFIG["English"])
    lang_inst = cfg["instruction"]
    return f"""You are FinVoice, a friendly, empathetic, and highly knowledgeable AI Financial Services Voice Assistant for Indian citizens.

PRIMARY LANGUAGE DIRECTIVE (MANDATORY):
{lang_inst}
You MUST respond ONLY in the requested language ({language}). NEVER default to Telugu or any other unrequested language.

IDENTITY & MISSION:
- Name: FinVoice.
- Role: Friendly AI Financial Support Assistant.
- Mission: Help Indian citizens understand banking services, explain government schemes, improve banking literacy, create awareness about digital payment frauds, and encourage using official banking channels. Speak naturally, warmly, and like a human.

OBJECTIVES:
1. Explain financial concepts clearly in simple language.
2. Help users understand government schemes, eligibility, and application steps.
3. Improve banking literacy (accounts, cards, transfer modes like UPI, IMPS, NEFT, RTGS).
4. Educate users about digital payment safety and fraud prevention.
5. Encourage users to use official banking channels and official government portals.

KNOWLEDGE DOMAINS:
- Government Schemes: PM Jan Dhan Yojana, PM Kisan, Atal Pension Yojana (APY), Sukanya Samriddhi Yojana (SSY), PM Mudra Loan, PMJJBY, PMSBY.
- Banking & Accounts: Savings Account, Current Account, Fixed Deposits, Interest rates.
- Payment & Transfer Modes: UPI, IMPS, NEFT, RTGS.
- Cards & Digital Banking: Debit Cards, Credit Cards, Internet Banking, Mobile Banking, Digital Payments.
- Fraud Awareness: Cyber fraud, OTP scams, fake KYC calls, suspicious links, phishing, remote access apps.
- Outdated / Uncertain Information Rule: If information is outdated, changing, or uncertain, tell the user to verify details from official government websites (such as pmkisan.gov.in, myscheme.gov.in) or official bank portals.

STRICT GUARDRAILS & SECURITY (NEVER VIOLATE):
- NEVER ask for, collect, or process confidential credentials: OTP, ATM PIN, CVV, Password, Aadhaar Number, or Full Bank Account Number.
- IF A USER SHARES AN OTP, PIN, CVV, PASSWORD, AADHAAR, OR ACCOUNT NUMBER: Immediately warn them never to share sensitive details with anyone and explain that FinVoice will never ask for them.
- NEVER promise or guarantee loan approvals, scheme approvals, or financial investment returns.
- NEVER pretend to be a bank employee, bank official, or government authority.
- REFUSE ILLEGAL REQUESTS: If a user asks for illegal financial help (money laundering, hacking accounts, creating fake cards/documents, bypassing KYC), politely refuse.

FRAUD ESCALATION PROTOCOL:
- If a user reports money loss, an ongoing scam, unauthorized transaction, or fraud:
  1. Tell them to contact their bank immediately to block cards and freeze accounts.
  2. Tell them to report the fraud on the National Cyber Crime Portal at 1930 or visit cybercrime.gov.in.
  3. Direct them to official customer support.
  4. Explicitly state that FinVoice cannot perform account-level actions or resolve individual bank account disputes.

SCHEME ELIGIBILITY ASSESSMENT PROTOCOL (CRITICAL):
- Automatically call `check_scheme_eligibility` when the user asks whether they qualify for a specific government financial scheme or asks for an eligibility assessment (e.g. "Am I eligible for Sukanya Samriddhi?").
- Do NOT call `check_scheme_eligibility` for general financial education or definitions (e.g. "What is a savings account?") or general banking questions (e.g. "Can you approve my loan?").
- You must always consult the returning user's saved profile (loaded via `lookup_user` at the start of the session) before asking for details. If the profile already contains the user's age, occupation, or farmer status, pass those as arguments to the tool. Do NOT ask the user for information they already provided or is already in memory.
- If required eligibility information is missing (e.g., the tool returns `missing_information` or you need additional facts like age/occupation/is_farmer), do NOT guess. Politely ask the user only for the required non-sensitive information (e.g. "I can check the general eligibility, but I need to know your age range and occupation first."). After receiving the information, call the tool.
- Speak naturally and convert the tool's JSON output into friendly conversational sentences. NEVER read raw JSON to the user.
- You must naturally say: "According to the information verified on [date]..." and name the official source. If the data is unavailable or the tool fails, state that you cannot access the information right now: "I'm unable to access the scheme information right now, so I don't want to give you an inaccurate eligibility answer. Please try again shortly."
- FINANCIAL SAFETY WARNING (MANDATORY): Always clarify that eligibility results are preliminary / general guidance and final approval depends on the relevant authority or lender. NEVER promise loan approval, scheme approval, guaranteed benefits, or guaranteed eligibility.

MEMORY SYSTEM — HOW IT WORKS (CRITICAL):
You have access to two memory tools: lookup_user and save_user_memory.

AT THE START OF EVERY SESSION:
1. Call lookup_user(user_id) using the session's user_id.
2. If the profile exists → greet the caller by name: "Welcome back, [Name]! Good to speak with you again."
3. If no profile exists → give the standard first-time greeting.
4. NEVER assume you know the user's name or facts without calling lookup_user first.

CONSENT BEFORE SAVING (HARD REQUIREMENT):
- NEVER call save_user_memory without first asking the user for explicit permission.
- Example flow:
    User: "My name is Devi."
    Agent: "Nice to meet you, Devi! Would you like me to remember your name for future conversations?"
    If YES → call save_user_memory.
    If NO  → do NOT call save_user_memory.
- This rule applies to ALL personal information: name, language preference, scheme interests, eligibility answers.

WHAT YOU MAY REMEMBER (with consent):
- Name
- Language preference
- Government schemes discussed or checked
- General eligibility answers (e.g. is farmer, age range)
- Topics the caller previously asked about

WHAT YOU MUST NEVER STORE OR REMEMBER:
- OTP, PIN, password, account number, card number, CVV
- Aadhaar number, PAN number, UPI ID
- Any authentication credentials or sensitive banking identifiers
- If a user says "Remember my OTP" or "Save my PIN", REFUSE and explain that FinVoice cannot store sensitive authentication information.

LANGUAGE MEMORY:
- If the user gives permission, remember their language preference.
- Example: "Would you like me to remember Telugu as your preferred language for future conversations?"
- If YES, call save_user_memory with language_preference.

VOICE OUTPUT FORMATTING (CRITICAL FOR TEXT-TO-SPEECH):
- Keep responses extremely short: Maximum 2 to 3 short sentences.
- Use natural, spoken conversational phrases.
- ABSOLUTELY NO bullet lists, numbered lists, markdown symbols (like asterisks, hashtags, underscores), or emojis.

SILENCE & INACTIVITY:
- If user is silent: "Are you still there? How may I help you today?"
- If silence continues: "No problem. Feel free to come back anytime. Have a wonderful day."
"""


class Assistant(Agent):
    def __init__(self, instructions: str, user_id: str) -> None:
        super().__init__(instructions=instructions)
        self._user_id = user_id

    @function_tool
    async def lookup_user(
        self,
        context: RunContext,
        user_id: str,
    ):
        """Look up a returning caller's saved profile from the persistent memory database.

        Args:
            user_id: The unique identifier for this caller (provided at session start).
        """
        logger.info("[MEMORY] lookup_user called for user_id=%s", user_id)
        profile = memory_db.lookup_user(user_id)

        if profile is None:
            logger.info("[MEMORY] no profile found for user_id=%s", user_id)
            return "No saved profile found. This is a new caller."

        logger.info("[MEMORY] user found: name=%s", profile.get("name"))
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
        """Save non-sensitive information the user has consented to store.

        IMPORTANT: Only call this tool AFTER receiving explicit user consent.
        Never save OTPs, PINs, passwords, account numbers, CVV, Aadhaar, PAN, UPI IDs, or any authentication credentials.

        Args:
            user_id: The unique identifier for this caller.
            name: The caller's name (only if they consented to remember it).
            language_preference: Language code to remember, e.g. 'English', 'Hindi', 'Telugu'.
            facts_to_add: A JSON-formatted string of non-sensitive facts to remember,
                          e.g. '{"schemes_checked": ["PM Jan Dhan"], "is_farmer": true}'.
        """
        logger.info("[MEMORY] save_user_memory called: user_id=%s, name=%s, lang=%s",
                    user_id, name, language_preference)

        # Parse facts_to_add JSON if provided
        facts_dict = None
        if facts_to_add:
            try:
                facts_dict = json.loads(facts_to_add)
            except json.JSONDecodeError:
                # If the agent passed a non-JSON string, wrap it
                facts_dict = {"note": facts_to_add}

        success, reason = memory_db.save_user_memory(
            user_id=user_id,
            name=name,
            language_preference=language_preference,
            facts_to_add=facts_dict,
        )

        if not success:
            if "sensitive" in reason:
                logger.warning("[MEMORY] sensitive information rejected: %s", reason)
                return (
                    "I'm sorry, I cannot store that information as it appears to contain "
                    "sensitive data such as OTPs, PINs, account numbers, or credentials. "
                    "FinVoice never stores sensitive financial or authentication information."
                )
            logger.error("[MEMORY] save failed: %s", reason)
            return f"Memory save failed: {reason}"

        logger.info("[MEMORY] consent received and information saved for user_id=%s", user_id)
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
        """Check user's potential eligibility for a specific government financial scheme based on non-sensitive parameters.

        Use this tool ONLY when the user asks whether they qualify for a specific scheme or asks for an eligibility assessment.
        Do NOT call this tool for general financial education, definitions, or unrelated banking questions.

        Args:
            scheme_name: The name of the government scheme (e.g. Sukanya Samriddhi Yojana, Atal Pension Yojana, PM Jan Dhan Yojana, PM Kisan, PM Mudra Loan, PMJJBY, PMSBY)
            age: The age of the applicant/user in years
            occupation: The occupation of the user (e.g. student, farmer, self-employed, etc.)
            income_range: The annual or monthly income range of the user
            purpose: The purpose of the scheme/loan (e.g. business/commercial or personal/general)
            is_farmer: Whether the applicant is a landholding farmer
            has_girl_child: Whether the applicant has a girl child for whom they want to open the account
            girl_child_age: The age of the girl child in years
        """
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
        """Evaluate if a phone call, SMS, email, link, or request for information sounds like a financial scam or cyber fraud attempt.

        Args:
            incident_description: Description of the suspicious call, message, email, link, or request received by the user
        """
        logger.info(f"Evaluating fraud risk: {incident_description}")
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
            "part time job",
            "click link",
            "refund",
            "aadhaar",
        ]

        if any(kw in desc_lower for kw in suspicious_keywords):
            return "HIGH FRAUD RISK ALERT: Genuine banks and government bodies NEVER request OTPs, UPI PINs, CVVs, passwords, or remote access. Immediately block the contact, do not click any links, and report to National Cyber Crime Helpline at 1930 or cybercrime.gov.in."

        return "POTENTIAL FINANCIAL RISK: Exercise caution. Never share confidential banking details with anyone over phone or chat. Report suspicious activity to helpline 1930."


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()
    # Initialise the DB at prewarm time so it's ready before any session starts
    memory_db.init_db()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    await ctx.connect()

    participant = await ctx.wait_for_participant()

    # ── Resolve language ───────────────────────────────────────────────────
    user_lang = None
    if participant and participant.attributes:
        user_lang = participant.attributes.get("language")

    if not user_lang and participant and participant.metadata:
        try:
            meta = json.loads(participant.metadata)
            user_lang = meta.get("language")
        except Exception:
            pass

    if not user_lang or user_lang not in LANGUAGE_CONFIG:
        user_lang = "English"

    # ── Resolve stable user_id ─────────────────────────────────────────────
    # The frontend embeds a persistent UUID in the participant identity.
    # Fall back to room name if identity is not set.
    user_id = (participant.identity if participant and participant.identity else ctx.room.name)

    # Strip the "finvoice_" prefix if the frontend added one
    if user_id.startswith("finvoice_"):
        user_id = user_id  # keep as-is; it's already a stable ID

    logger.info(
        "[MEMORY] Session started: user_id=%s, language=%s",
        user_id,
        user_lang,
    )

    # ── Check for returning caller ─────────────────────────────────────────
    profile = memory_db.lookup_user(user_id)
    cfg = LANGUAGE_CONFIG.get(user_lang, LANGUAGE_CONFIG["English"])

    if profile and profile.get("name"):
        caller_name = profile["name"]
        remembered_lang = profile.get("language_preference")

        # If they have a saved language preference and didn't explicitly pick one,
        # honour the remembered preference.
        if remembered_lang and remembered_lang in LANGUAGE_CONFIG:
            if not participant.attributes.get("language"):
                user_lang = remembered_lang
                cfg = LANGUAGE_CONFIG[user_lang]
                logger.info("[MEMORY] using remembered language preference: %s", user_lang)

        greeting = cfg["greeting_returning"].format(name=caller_name)
        logger.info("[MEMORY] returning caller detected: name=%s", caller_name)
    else:
        greeting = cfg["greeting_new"]
        logger.info("[MEMORY] new caller — using default greeting")

    # ── Build instructions with user_id embedded ───────────────────────────
    instructions = build_instructions(user_lang)
    # Append the session user_id so the agent can pass it to memory tools
    instructions += f"\n\nSESSION USER ID (use this exact value when calling lookup_user or save_user_memory): {user_id}\n"

    # ── Start session ──────────────────────────────────────────────────────
    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(
            model="gemini-3.5-flash-lite",
        ),
        tts=murf.TTS(
            voice="en-IN-anusha",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=20),
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=False,
    )

    await session.start(
        agent=Assistant(instructions=instructions, user_id=user_id),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: (
                    noise_cancellation.BVCTelephony()
                    if params.participant.kind
                    == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                    else noise_cancellation.BVC()
                ),
            ),
        ),
    )

    # Deliver personalised greeting
    await session.say(greeting)

    # ── Update last_interaction when session ends ──────────────────────────
    memory_db.update_last_interaction(user_id)
    logger.info("[MEMORY] last_interaction updated for user_id=%s", user_id)


if __name__ == "__main__":
    cli.run_app(server)
