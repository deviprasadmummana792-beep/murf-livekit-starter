import logging

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

logger = logging.getLogger("agent")

load_dotenv(".env.local")

# Change this prompt to change what your voice agent does.
# See README.md for example prompts (customer support, language tutor, receptionist).
SYSTEM_PROMPT = """You are FinSathi, a friendly, empathetic, and highly knowledgeable AI Financial Services Voice Assistant for Indian citizens.

IDENTITY & MISSION:
- Name: FinSathi.
- Role: Friendly AI Financial Services Voice Assistant.
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

STRICT LANGUAGE DETECTION & MIRRORING RULES (CRITICAL):
- DETECT LANGUAGE FIRST: Before responding, analyze the user's spoken language carefully.
- TELUGU & TELUGU-ENGLISH (TELUGISH) RULES:
  - If user speaks Telugu -> Reply ONLY in Telugu.
  - If user speaks Telugu + English (Telugish) -> Reply ONLY in Telugu + English (Telugish).
  - ABSOLUTE PROHIBITION: NEVER convert Telugu or Telugu-English into Hindi or Hinglish. NEVER assume Telugu is Hindi.
- HINDI & HINDI-ENGLISH (HINGLISH) RULES:
  - Reply in Hindi ONLY if the user speaks Hindi.
  - Reply in Hindi + English (Hinglish) ONLY if the user speaks Hindi + English.
- ENGLISH RULES:
  - Reply in English ONLY if the user speaks English.
- UNCERTAIN LANGUAGE RULE:
  - If the user's detected language is uncertain or ambiguous, politely ask: "Would you like me to continue in Telugu, Hindi, or English?"
- Tone: Be warm, encouraging, respectful, and human-like. Never sound robotic.

STRICT GUARDRAILS & SECURITY (NEVER VIOLATE):
- NEVER ask for, collect, or process confidential credentials: OTP, ATM PIN, CVV, Password, Aadhaar Number, or Full Bank Account Number.
- IF A USER SHARES AN OTP, PIN, CVV, PASSWORD, AADHAAR, OR ACCOUNT NUMBER: Immediately warn them never to share sensitive details with anyone and explain that FinSathi will never ask for them.
- NEVER promise or guarantee loan approvals, scheme approvals, or financial investment returns.
- NEVER pretend to be a bank employee, bank official, or government authority.
- REFUSE ILLEGAL REQUESTS: If a user asks for illegal financial help (money laundering, hacking accounts, creating fake cards/documents, bypassing KYC), politely refuse.

FRAUD ESCALATION PROTOCOL:
- If a user reports money loss, an ongoing scam, unauthorized transaction, or fraud:
  1. Tell them to contact their bank immediately to block cards and freeze accounts.
  2. Tell them to report the fraud on the National Cyber Crime Portal at 1930 or visit cybercrime.gov.in.
  3. Direct them to official customer support.
  4. Explicitly state that FinSathi cannot perform account-level actions or resolve individual bank account disputes.

VOICE OUTPUT FORMATTING (CRITICAL FOR TEXT-TO-SPEECH):
- Keep responses extremely short: Maximum 2 to 3 short sentences.
- Use natural, spoken conversational phrases.
- ABSOLUTELY NO bullet lists, numbered lists, markdown symbols (like asterisks, hashtags, underscores), or emojis.

SILENCE & INACTIVITY:
- If user is silent: "Are you still there? How may I help you today?"
- If silence continues: "No problem. Feel free to come back anytime. Have a wonderful day."

INITIAL GREETING:
"Hello! I'm FinSathi, your AI Financial Services Voice Assistant. I can help you understand banking services, government schemes and stay safe from financial frauds. How may I help you today?"
"""


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)

    @function_tool
    async def check_scheme_eligibility(
        self,
        context: RunContext,
        scheme_name: str,
        age: int | None = None,
        is_farmer: bool | None = None,
        has_girl_child: bool | None = None,
    ):
        """Check eligibility criteria for key government financial schemes.

        Args:
            scheme_name: The name of the government scheme (e.g. Sukanya Samriddhi, Atal Pension Yojana, PM Jan Dhan, PM-KISAN, PM Mudra Loan, PMJJBY, PMSBY)
            age: The age of the applicant or beneficiary in years
            is_farmer: Whether the user or family is a land-holding farmer
            has_girl_child: Whether the user is opening an account for a girl child below 10 years
        """
        logger.info(f"Checking eligibility for scheme: {scheme_name}, age: {age}")
        scheme_lower = scheme_name.lower()

        if "mudra" in scheme_lower:
            return "PM Mudra Loan provides loans up to 10 lakh rupees for non-farm micro and small enterprises under Shishu, Kishor, and Tarun categories. Applications should be submitted at official bank branches or udyamimitra portal."

        if "jan dhan" in scheme_lower or "pmjdy" in scheme_lower:
            return "PM Jan Dhan Yojana is available for any Indian citizen above 10 years without a basic bank account. It provides zero balance savings account, free RuPay debit card, and 2 lakh rupees accident insurance."

        if "sukanya" in scheme_lower:
            if has_girl_child or (age is not None and age <= 10):
                return "Eligible for Sukanya Samriddhi Yojana. Account can be opened for a girl child below 10 years with high interest rates and tax benefits under Section 80C."
            return "Sukanya Samriddhi Yojana requires a girl child below 10 years of age."

        if "atal" in scheme_lower or "apy" in scheme_lower:
            if age is not None:
                if 18 <= age <= 40:
                    return f"Eligible for Atal Pension Yojana. At age {age}, a monthly pension of 1000 to 5000 rupees is guaranteed after age 60."
                return f"Atal Pension Yojana is for individuals aged 18 to 40. Age {age} is outside this range."
            return "Atal Pension Yojana is available for Indian citizens between 18 and 40 years of age."

        if "kisan" in scheme_lower or "pm-kisan" in scheme_lower:
            if is_farmer:
                return "Eligible for PM-KISAN. Direct income support of 6000 rupees per year is provided in three installments to farmer families."
            return "PM-KISAN is specifically for landholding farmer families."

        if "pmjjby" in scheme_lower or "jeevan jyoti" in scheme_lower:
            if age is not None and 18 <= age <= 50:
                return "Eligible for PM Jeevan Jyoti Bima Yojana. Offers 2 lakh rupees life insurance cover for 436 rupees annually."
            return "PMJJBY is for bank account holders aged 18 to 50 years."

        if "pmsby" in scheme_lower or "suraksha bima" in scheme_lower:
            if age is not None and 18 <= age <= 70:
                return "Eligible for PM Suraksha Bima Yojana. Offers 2 lakh rupees accidental insurance cover for 20 rupees annually."
            return "PMSBY is for bank account holders aged 18 to 70 years."

        return f"Scheme {scheme_name} provides social security and banking benefits. Always verify exact terms on official government or bank portals."

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


server.setup_fnc = prewarm


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(
            model="gemini-3.5-flash-lite",
        ),
        tts=murf.TTS(
            voice="en-IN-anusha",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    await session.start(
        agent=Assistant(),
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

    await ctx.connect()

    # Deliver initial greeting upon connecting to the room
    await session.say(
        "Hello! I'm FinSathi, your AI Financial Services Voice Assistant. I can help you understand banking services, government schemes and stay safe from financial frauds. How may I help you today?"
    )


if __name__ == "__main__":
    cli.run_app(server)
