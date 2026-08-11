import argparse
import asyncio
import os
import sys
import uuid
from pathlib import Path
from dotenv import load_dotenv
from livekit import api

# Ensure src directory is in sys.path
src_dir = Path(__file__).resolve().parent.parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

load_dotenv(src_dir.parent / ".env.local")
load_dotenv(".env.local")


async def place_outbound_call(to_address: str):
    livekit_url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")

    # Check for trunk ID (expecting LIVEKIT_SIP_OUTBOUND_TRUNK_ID or LIVEKIT_SIP_TRUNK_ID)
    trunk_id = os.getenv("LIVEKIT_SIP_OUTBOUND_TRUNK_ID") or os.getenv(
        "LIVEKIT_SIP_TRUNK_ID"
    )
    outbound_host = os.getenv("SIP_OUTBOUND_HOST", "sip.linphone.org")

    # Validate mandatory configuration
    missing_vars = []
    if not livekit_url:
        missing_vars.append("LIVEKIT_URL")
    if not api_key:
        missing_vars.append("LIVEKIT_API_KEY")
    if not api_secret:
        missing_vars.append("LIVEKIT_API_SECRET")
    if not trunk_id:
        missing_vars.append(
            "LIVEKIT_SIP_OUTBOUND_TRUNK_ID (or LIVEKIT_SIP_TRUNK_ID)"
        )

    if missing_vars:
        print(
            "\n[ERROR] Missing required configuration for outbound calling:",
            file=sys.stderr,
        )
        for mv in missing_vars:
            print(f"  - {mv}", file=sys.stderr)
        print(
            "\nPlease update backend/.env.local with valid LiveKit SIP configuration before dialing.\n",
            file=sys.stderr,
        )
        sys.exit(1)

    # Format destination for LiveKit SIP API
    # sip_call_to must be a full SIP URI (sip:user@domain) so LiveKit sends INVITE to the correct server.
    # Using just the username causes LiveKit to not resolve the domain correctly.
    clean_target = to_address.removeprefix("sip:")
    sip_user_or_number = clean_target.split("@")[0]
    sip_uri = f"sip:{sip_user_or_number}@{outbound_host}"  # full URI used as sip_call_to

    room_name = f"outbound-call-{uuid.uuid4().hex[:8]}"
    participant_identity = f"sip_{uuid.uuid4().hex[:6]}"

    print("=" * 60)
    print("FINVOICE OUTBOUND SIP CALL INITIATOR")
    print("=" * 60)
    print(f"Target Destination: {sip_uri} (User: {sip_user_or_number})")
    print(f"SIP Trunk ID:       {trunk_id}")
    print(f"LiveKit Room Name:  {room_name}")
    print("Initiating outbound SIP call via LiveKit Cloud...")
    print("-" * 60)

    try:
        async with api.LiveKitAPI(
            url=livekit_url, api_key=api_key, api_secret=api_secret
        ) as lk:
            req = api.CreateSIPParticipantRequest(
                sip_trunk_id=trunk_id,
                sip_call_to=sip_user_or_number,  # bare username — trunk address provides the domain
                room_name=room_name,
                participant_identity=participant_identity,
                participant_name="Linphone Outbound Caller",
                play_ringtone=True,
                wait_until_answered=True,     # FIXED: wait for call to be answered before returning
            )
            participant_info = await lk.sip.create_sip_participant(req)
            print("[SUCCESS] Outbound SIP call initiated successfully!")
            print(f"Participant ID:       {participant_info.participant_id}")
            print(f"Participant Identity: {participant_info.participant_identity}")
            print(f"Room Name:            {room_name}")
            print("\nWaiting for Linphone client to ring and connect...")
            print(
                "Make sure 'uv run python src/telephony/outbound/agent.py dev' is running to handle the call!"
            )
            print("=" * 60)
    except Exception as e:
        print("\n[FAILED] Outbound call creation failed:", file=sys.stderr)
        print(f"Details: {str(e)}", file=sys.stderr)
        print("\nTroubleshooting tips:", file=sys.stderr)
        print(
            "1. Verify SIP Trunk ID in LiveKit Dashboard (SIP -> Outbound Trunks).",
            file=sys.stderr,
        )
        print(
            "2. Ensure Linphone client is logged in and active at sip.linphone.org.",
            file=sys.stderr,
        )
        print(
            "3. Check network connection and LiveKit credentials in backend/.env.local.",
            file=sys.stderr,
        )
        print("=" * 60, file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="FinVoice Outbound SIP Call Initiator")
    parser.add_argument(
        "--to",
        type=str,
        default=os.getenv("LINPHONE_SIP_URI", "mummanadeviprasad456"),
        help="SIP address or username to call (e.g. mummanadeviprasad456 or sip:mummanadeviprasad456@sip.linphone.org)",
    )
    args = parser.parse_args()
    asyncio.run(place_outbound_call(args.to))


if __name__ == "__main__":
    main()
