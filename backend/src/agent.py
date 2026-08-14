import asyncio
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

HANDOFF TO SPECIALIST AGENT PROTOCOL (DAY 9 MANDATORY):
- You are the MAIN FINVOICE AGENT for general financial queries.
- CRITICAL HANDOFF RULE: Whenever the user asks ANY question about Indian government schemes (such as Sukanya Samriddhi Yojana, PM Kisan, Atal Pension Yojana, PM Jan Dhan Yojana, PM Mudra Loan, PMJJBY, PMSBY, government welfare schemes, or scheme eligibility/documents/benefits):
  - You MUST IMMEDIATELY call the `transfer_to_government_scheme_specialist` tool.
  - Do NOT attempt to answer government scheme questions yourself, and do NOT call `check_scheme_eligibility` yourself — hand off to the Government Scheme Specialist immediately using `transfer_to_government_scheme_specialist`.
  - BEFORE calling the handoff tool, announce to the user: "I'll connect you to our Government Scheme Specialist so they can help you with that."
- NORMAL FINANCIAL QUESTIONS MUST REMAIN WITH THE MAIN AGENT:
  - Do NOT call `transfer_to_government_scheme_specialist` for normal financial questions (such as credit score, personal loans, EMI, compound interest, savings accounts, digital payments, or general banking definitions). Answer normal financial questions yourself without handoff.

HUMAN HELP / ESCALATION PROTOCOL (DAY 7):
- You must identify when to offer human assistance for financial issues.
- Implement TWO human-escalation scenarios:
  1. POSSIBLE FRAUD: If the user reports suspicious activity, possible fraud, unauthorized activity, or a potentially fraudulent transaction.
  2. FINANCIAL DECISION OUTSIDE AGENT SCOPE: If the user asks for a financial decision, approval, or advice that you are not authorized or capable of making (e.g. loan/credit approvals, credit limit increases, investment advice, account closures, reversing charges).
- CONSENT BEFORE ESCALATION (HARD REQUIREMENT):
  - You MUST NOT call `create_escalation` immediately.
  - First, you must ask the user: "This issue may need help from a human financial specialist. I can share a short summary of your issue with them. Would you like me to do that?" (or equivalent in Hindi/Telugu if speaking in those languages).
  - Only if the user clearly says YES / agrees: call `create_escalation`.
  - If the user says NO: do NOT call `create_escalation`, respect their decision, and continue/end the conversation naturally.
- AFTER CREATION:
  - If the tool succeeds and returns a reference ID (e.g. FIN-2026-0001), you must say naturally: "Your request has been shared with our support team. Your reference ID is FIN-XXXX. A human specialist can follow up using your preferred method. I can't promise an immediate response." (Replace FIN-XXXX with the actual generated reference ID).
  - If the tool fails (returns error/failure), say: "I'm sorry, I couldn't create the support request right now. Please try again later."
- PRIVACY & SAFETY:
  - Never store or send OTP, PIN, password, CVV, bank account number, card number, authentication credentials, or unnecessary private conversation details to the escalation tool. Sanitise summaries.
  - Urgency can be: low, normal, or high. Language is the current language being spoken.
- NORMAL FINANCIAL QUESTIONS MUST NOT ESCALATE:
  - Do NOT escalate general educational questions, concept explanations, or scheme eligibility queries (e.g. "What is a financial scheme deadline?", "Am I eligible for PM Kisan?"). Only escalate possible fraud or out-of-scope decisions.

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


def build_specialist_instructions(language: str, initial_context: str = "") -> str:
    cfg = LANGUAGE_CONFIG.get(language, LANGUAGE_CONFIG["English"])
    lang_inst = cfg["instruction"]
    return f"""You are FinVoice's Government Scheme Specialist, a dedicated expert in Indian government welfare and savings schemes.

PRIMARY LANGUAGE DIRECTIVE (MANDATORY):
{lang_inst}
You MUST respond ONLY in the requested language ({language}).

ROLE & RESPONSIBILITIES:
- Role: FinVoice's Government Scheme Specialist.
- Responsibilities: Your job is to help users understand Indian government welfare and savings schemes, explain eligibility requirements, required documents, general benefits, and guide users through scheme-related questions.
- Knowledge Scope: Indian government welfare and savings schemes (PM Jan Dhan Yojana, PM Kisan, Atal Pension Yojana, Sukanya Samriddhi Yojana, PM Mudra Loan, PMJJBY, PMSBY, myscheme.gov.in, etc.).

STRICT GUARDRAILS & SAFETY (NEVER VIOLATE):
- Provide clear and cautious information.
- Avoid inventing scheme rules or benefits.
- Clearly state when information may need official verification from official government portals (such as pmkisan.gov.in, myscheme.gov.in) or official bank portals.
- NEVER ask for, collect, or process confidential credentials: OTP, ATM PIN, CVV, Password, Aadhaar Number, PAN Number, or full Bank/Card Account Numbers.
- IF A USER SHARES SENSITIVE DETAILS: Immediately warn them never to share sensitive details with anyone and explain that FinVoice will never ask for them.
- NEVER pretend to be a government employee, bank official, or government authority.
- NEVER make guaranteed financial decisions, guaranteed loan approvals, or promised scheme approvals.

LIMITATIONS & HANDBACK PROTOCOL:
- Focus ONLY on government schemes. You must NOT try to handle unrelated financial questions.
- If the user asks something outside government schemes (e.g. general credit scores, personal loans, EMI calculations, credit cards, or general banking definitions):
  - Politely explain that the request is outside your government scheme specialist role.
  - Call the `transfer_back_to_main_agent` tool to return the user to the main FinVoice agent.

VOICE OUTPUT FORMATTING (CRITICAL FOR TTS):
- Keep responses short: Maximum 2 to 3 short sentences.
- Speak naturally and warmly.
- ABSOLUTELY NO bullet lists, numbered lists, markdown symbols, or emojis.

INITIAL CONTEXT FROM MAIN AGENT:
{initial_context}
"""


class Assistant(Agent):
    def __init__(self, instructions: str, user_id: str, user_lang: str = "English") -> None:
        super().__init__(instructions=instructions)
        self._user_id = user_id
        self._user_lang = user_lang

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

    @function_tool
    async def create_escalation(
        self,
        context: RunContext,
        user_name: str | None = None,
        issue_summary: str = "",
        what_agent_checked: str = "",
        urgency: str = "normal",
        language: str = "English",
        preferred_follow_up_method: str = "email",
    ):
        """Create a human support ticket for potential fraud or out-of-scope decisions.

        IMPORTANT: Only call this tool AFTER receiving explicit user consent.
        Do NOT store or send OTPs, PINs, passwords, CVVs, bank account numbers, or card numbers.

        Args:
            user_name: The name of the user (e.g. name, or anonymous if unknown)
            issue_summary: Brief, non-sensitive summary of the issue
            what_agent_checked: Description of what was checked (e.g. potential fraud detected, out-of-scope decision request)
            urgency: Urgency of the request: 'low', 'normal', 'high'
            language: Preferred language: 'English', 'Hindi', 'Telugu', 'Hinglish'
            preferred_follow_up_method: Preferred contact method: 'email', 'phone'
        """
        logger.info("[MEMORY] create_escalation tool called for name=%s, issue=%s", user_name, issue_summary)
        success, ref_id, err = memory_db.create_escalation_record(
            user_name=user_name,
            issue_summary=issue_summary,
            what_agent_checked=what_agent_checked,
            urgency=urgency,
            language=language,
            preferred_follow_up_method=preferred_follow_up_method,
        )

        if not success:
            logger.error("[MEMORY] create_escalation tool failure: %s", err)
            return json.dumps({"status": "error", "message": err or "Database failure"})

        logger.info("[MEMORY] create_escalation tool success: %s", ref_id)
        return json.dumps({"status": "success", "reference_id": ref_id})

    @function_tool
    async def transfer_to_government_scheme_specialist(
        self,
        context: RunContext,
        user_request: str,
        scheme_name: str | None = None,
    ):
        """Transfer the conversation to the Government Scheme Specialist when the user asks for detailed information, eligibility, benefits, required documents, application guidance, or other questions specifically about Indian government schemes. Do not use this tool for normal financial questions that the main FinVoice agent can answer.

        Args:
            user_request: The specific question or topic requested by the user about government schemes.
            scheme_name: The name of the government scheme if mentioned (e.g. Sukanya Samriddhi Yojana, PM Kisan).
        """
        logger.info("[HANDOFF] Main agent received specialist request")
        logger.info("[HANDOFF] User request: %s", user_request)
        logger.info("[HANDOFF] Transferring to Government Scheme Specialist")

        try:
            # Announcement BEFORE handoff
            announcement = "I'll connect you to our Government Scheme Specialist so they can help you with that."
            await context.session.say(announcement)

            ctx_desc = f"User Request: {user_request}"
            if scheme_name:
                ctx_desc += f"\nScheme Name: {scheme_name}"

            specialist_instructions = build_specialist_instructions(
                self._user_lang, initial_context=ctx_desc
            )
            specialist_instructions += f"\n\nSESSION USER ID: {self._user_id}\n"

            specialist_agent = GovernmentSchemeSpecialist(
                instructions=specialist_instructions,
                user_id=self._user_id,
                user_lang=self._user_lang,
                main_agent=self,
            )

            # Update room participant attributes if possible
            try:
                room = getattr(context.session, 'room', None) or getattr(context.session, '_room', None)
                if room and getattr(room, 'local_participant', None):
                    await room.local_participant.set_attributes(
                        {"agent_name": "Government Scheme Specialist"}
                    )
            except Exception as attr_err:
                logger.warning("[HANDOFF] Failed to update participant attributes: %s", attr_err)

            context.session.update_agent(specialist_agent)

            logger.info("[HANDOFF] Specialist started")
            logger.info("[HANDOFF] Context transferred successfully")

            # Specialist Introduction
            topic_mention = f" {scheme_name}" if scheme_name else ""
            intro = f"Hi, I'm FinVoice's Government Scheme Specialist. I can help you with government scheme eligibility, benefits, and required documents. I understand you're asking about{topic_mention} {user_request}. How can I help you further?"
            await context.session.say(intro)

            return "Transferred successfully to Government Scheme Specialist."

        except Exception as exc:
            logger.error("[HANDOFF] Error during specialist transfer: %s", exc, exc_info=True)
            fallback_msg = "I'm unable to connect you to the specialist right now, but I can still try to help you."
            await context.session.say(fallback_msg)
            return f"Handoff failed: {exc}"


class GovernmentSchemeSpecialist(Agent):
    def __init__(
        self,
        instructions: str,
        user_id: str,
        user_lang: str = "English",
        main_agent: Agent | None = None,
    ) -> None:
        super().__init__(instructions=instructions)
        self._user_id = user_id
        self._user_lang = user_lang
        self._main_agent = main_agent

    @function_tool
    async def lookup_user(
        self,
        context: RunContext,
        user_id: str,
    ):
        """Look up a returning caller's saved profile from persistent memory database.

        Args:
            user_id: The unique identifier for this caller.
        """
        logger.info("[MEMORY] lookup_user called by Specialist for user_id=%s", user_id)
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
        """Save non-sensitive information the user has consented to store.

        Args:
            user_id: The unique identifier for this caller.
            name: Caller's name.
            language_preference: Language preference.
            facts_to_add: Facts JSON.
        """
        logger.info("[MEMORY] save_user_memory called by Specialist: user_id=%s, name=%s", user_id, name)
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
                    "FinVoice never stores sensitive details."
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
        """Check potential eligibility for government financial schemes.

        Args:
            scheme_name: Name of the scheme.
            age: Age of applicant.
            occupation: Occupation.
            income_range: Income range.
            purpose: Loan/scheme purpose.
            is_farmer: Landholding farmer status.
            has_girl_child: Girl child status.
            girl_child_age: Age of girl child.
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
        """Evaluate if a request sounds like financial fraud."""
        logger.info("[SPECIALIST] Evaluating fraud risk: %s", incident_description)
        desc_lower = incident_description.lower()
        suspicious_keywords = [
            "otp", "pin", "cvv", "password", "remote access", "anydesk",
            "teamviewer", "lottery", "urgent block", "kyc update", "click link", "refund", "aadhaar",
        ]
        if any(kw in desc_lower for kw in suspicious_keywords):
            return "HIGH FRAUD RISK ALERT: Genuine banks and government bodies NEVER request OTPs, PINs, CVVs, passwords, or remote access. Immediately block contact and report to helpline 1930."
        return "POTENTIAL FINANCIAL RISK: Exercise caution. Never share confidential banking details over phone."

    @function_tool
    async def create_escalation(
        self,
        context: RunContext,
        user_name: str | None = None,
        issue_summary: str = "",
        what_agent_checked: str = "",
        urgency: str = "normal",
        language: str = "English",
        preferred_follow_up_method: str = "email",
    ):
        """Create a human support ticket for potential fraud or out-of-scope decisions after explicit user consent."""
        logger.info("[SPECIALIST] create_escalation called for name=%s, issue=%s", user_name, issue_summary)
        success, ref_id, err = memory_db.create_escalation_record(
            user_name=user_name,
            issue_summary=issue_summary,
            what_agent_checked=what_agent_checked,
            urgency=urgency,
            language=language,
            preferred_follow_up_method=preferred_follow_up_method,
        )
        if not success:
            return json.dumps({"status": "error", "message": err or "Database failure"})
        return json.dumps({"status": "success", "reference_id": ref_id})

    @function_tool
    async def transfer_back_to_main_agent(
        self,
        context: RunContext,
        reason: str = "",
    ):
        """Transfer the conversation back to the main FinVoice agent when the user asks general financial or banking questions outside government schemes (such as credit score, personal loans, EMI calculations, or general banking help).

        Args:
            reason: Explanation of why the conversation is being transferred back.
        """
        logger.info("[HANDOFF] Specialist handing back to main agent. Reason: %s", reason)
        try:
            announcement = "I'll connect you back to our main FinVoice assistant for general financial help."
            await context.session.say(announcement)

            target_agent = self._main_agent
            if target_agent is None:
                instructions = build_instructions(self._user_lang)
                instructions += f"\n\nSESSION USER ID: {self._user_id}\n"
                target_agent = Assistant(
                    instructions=instructions,
                    user_id=self._user_id,
                    user_lang=self._user_lang,
                )

            try:
                room = getattr(context.session, 'room', None) or getattr(context.session, '_room', None)
                if room and getattr(room, 'local_participant', None):
                    await room.local_participant.set_attributes(
                        {"agent_name": "FinVoice"}
                    )
            except Exception as attr_err:
                logger.warning("[HANDOFF] Attribute update warning: %s", attr_err)

            context.session.update_agent(target_agent)
            logger.info("[HANDOFF] Handed back to Main agent successfully")
            await context.session.say("Hi again! I'm back. How can I help you with your general financial questions?")
            return "Transferred back to main FinVoice agent."

        except Exception as exc:
            logger.error("[HANDOFF] Handback failed: %s", exc, exc_info=True)
            return f"Handback error: {exc}"


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
    user_id = (participant.identity if participant and participant.identity else ctx.room.name)

    if user_id.startswith("finvoice_"):
        user_id = user_id

    logger.info(
        "[MEMORY] Session started: user_id=%s, language=%s",
        user_id,
        user_lang,
    )

    # Set initial agent_name attribute on local participant
    try:
        if ctx.room and ctx.room.local_participant:
            await ctx.room.local_participant.set_attributes({"agent_name": "FinVoice"})
    except Exception as e:
        logger.warning("[AGENT] Could not set initial agent_name attribute: %s", e)

    # ── Check for returning caller ─────────────────────────────────────────
    profile = memory_db.lookup_user(user_id)
    cfg = LANGUAGE_CONFIG.get(user_lang, LANGUAGE_CONFIG["English"])

    if profile and profile.get("name"):
        caller_name = profile["name"]
        remembered_lang = profile.get("language_preference")

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
        agent=Assistant(instructions=instructions, user_id=user_id, user_lang=user_lang),
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

    # ── Keep session alive until room disconnects or shuts down ───────────
    done_event = asyncio.Event()

    def _on_room_disconnected(*_):
        logger.info("[AGENT] Room disconnected event received for user_id=%s", user_id)
        if not done_event.is_set():
            done_event.set()

    ctx.room.on("disconnected", _on_room_disconnected)
    ctx.add_shutdown_callback(lambda: done_event.set() if not done_event.is_set() else None)

    await done_event.wait()

    # ── Update last_interaction when session ends ──────────────────────────
    memory_db.update_last_interaction(user_id)
    logger.info("[MEMORY] last_interaction updated for user_id=%s", user_id)


if __name__ == "__main__":
    cli.run_app(server)

