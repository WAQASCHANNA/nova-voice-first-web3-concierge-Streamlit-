# nova_streamlit.py
import os, time, json, asyncio, tempfile
from pathlib import Path
import requests
import streamlit as st
from dotenv import load_dotenv
from typing import List, Dict, Any

# WebRTC recorder
from streamlit_webrtc import webrtc_streamer, WebRtcMode
import av

# MCP client (async)
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

load_dotenv()

# Config (env)
CORAL_MCP_URL = os.getenv("CORAL_SERVER_URL", "http://localhost:8000/mcp")
MCP_ACCESS_TOKEN = os.getenv("CORAL_SERVER_TOKEN", "")
AIMLAPI_KEY = os.getenv("AIMLAPI_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE = os.getenv("ELEVENLABS_VOICE", "voice_id_here")
CROSSMINT_SERVER_URL = os.getenv("CROSSMINT_SERVER_URL", "http://localhost:9000")  # your local server endpoint for mint
CROSSMINT_CLIENT_KEY = os.getenv("CROSSMINT_CLIENT_KEY")
CROSSMINT_SERVER_KEY = os.getenv("CROSSMINT_SERVER_KEY")

st.set_page_config(page_title="Nova — Voice Web3 Concierge", layout="wide")
st.title("Nova — Voice-First Web3 Concierge (Streamlit + Coral MCP)")

AGENT_NFT_ANALYST = "nft-analyst"        # agent name expected in registry.toml
AGENT_TRANSACTION = "transaction-agent" # agent name expected in registry.toml

#############################
# Utilities: AIMLAPI STT
#############################
def transcribe_with_aimlapi_bytes(file_bytes: bytes, model: str="openai/whisper-large", timeout_s:int=60) -> str:
    if not AIMLAPI_KEY:
        raise RuntimeError("AIMLAPI_KEY missing in environment")
    base = "https://api.aimlapi.com/v1"
    create_url = f"{base}/stt/create"
    headers = {"Authorization": f"Bearer {AIMLAPI_KEY}"}
    files = {"file": ("audio.wav", file_bytes, "audio/wav")}
    data = {"model": model}
    r = requests.post(create_url, headers=headers, files=files, data=data, timeout=30)
    r.raise_for_status()
    resp_json = r.json()
    gen_id = resp_json.get("generation_id") or resp_json.get("id")
    if not gen_id: raise RuntimeError("No generation id returned from AIMLAPI: " + r.text)
    status_url = f"{base}/stt/{gen_id}"
    t0=time.time()
    while True:
        r2 = requests.get(status_url, headers=headers, timeout=30)
        r2.raise_for_status()
        body = r2.json()
        status = body.get("status","")
        if status in ("succeeded","completed","done"):
            return body.get("text") or body.get("transcript") or body.get("result",{}).get("text","")
        if time.time()-t0>timeout_s:
            raise TimeoutError("AIMLAPI STT poll timed out")
        time.sleep(1)

#############################
# ElevenLabs TTS
#############################
def eleven_tts_write(text: str, out_path: str):
    if not ELEVENLABS_API_KEY or ELEVENLABS_VOICE=="voice_id_here":
        st.warning("ElevenLabs not configured (ELEVENLABS_API_KEY or ELEVENLABS_VOICE missing)")
        return None
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE}"
    headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type":"application/json"}
    payload = {"text": text}
    r = requests.post(url, headers=headers, json=payload, stream=True, timeout=60)
    if not r.ok:
        st.error(f"ElevenLabs TTS error: {r.status_code} {r.text}")
        return None
    with open(out_path,"wb") as f:
        for chunk in r.iter_content(4096):
            if chunk:
                f.write(chunk)
    return out_path

#############################
# MCP helpers (async)
#############################
async def mcp_list_tools_async(mcp_url: str, access_token: str=""):
    headers = {"Authorization": f"Bearer {access_token}"} if access_token else None
    async with streamablehttp_client(mcp_url, headers=headers) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            simple = []
            for t in tools:
                simple.append({
                    "name": t.name,
                    "description": getattr(t,"description",None),
                    "input_schema": getattr(t, "inputSchema", None)
                })
            return simple

async def mcp_call_tool_async(mcp_url: str, tool_name: str, arguments: dict, access_token: str="", timeout:int=60):
    headers = {"Authorization": f"Bearer {access_token}"} if access_token else None
    async with streamablehttp_client(mcp_url, headers=headers) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=arguments)
            return result

#############################
# UI: voice recording via streamlit-webrtc
#############################
st.header("1) Speak to Nova — Click to record")

webrtc_ctx = webrtc_streamer(
    key="nova-webrtc",
    mode=WebRtcMode.SENDONLY,
    rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
    media_stream_constraints={"audio": True, "video": False},
    desired_playing_state=False
)

recorded_bytes = None
if webrtc_ctx and webrtc_ctx.audio_receiver:
    # Wait for audio frames - user clicks Start and then Stop in the widget
    frames = webrtc_ctx.audio_receiver.get_frames(timeout=1.0)
    if frames:
        # Save frames to a wav file
        import soundfile as sf
        arr = b"".join([f.to_ndarray().tobytes() for f in frames])
        # easier approach: ask user to press snapshot button to save available frames
        pass

st.caption("If browser recording is unreliable, use the Upload fallback below.")

st.subheader("Upload fallback (WAV/MP3) or type")
audio_file = st.file_uploader("Upload recorded audio (WAV/MP3)", type=["wav","mp3","m4a","ogg"])
typed_text = st.text_area("Or type query (fallback):", height=80)

if st.button("Transcribe / Use typed"):
    transcript = None
    if audio_file:
        b = audio_file.read()
        with st.spinner("Transcribing audio..."):
            try:
                transcript = transcribe_with_aimlapi_bytes(b)
                st.success("Transcription complete")
            except Exception as e:
                st.error(f"STT error: {e}")
    else:
        if typed_text.strip():
            transcript = typed_text.strip()
            st.success("Using typed input")
        else:
            st.warning("No audio or typed text provided.")
    if transcript:
        st.session_state["transcript"] = transcript

if "transcript" in st.session_state:
    st.markdown("**Transcript:**")
    st.write(st.session_state["transcript"])

#############################
# Discover agents
#############################
st.header("2) Discover Coral Agents")
if st.button("List Coral agents"):
    with st.spinner("Querying Coral MCP..."):
        try:
            tools = asyncio.run(mcp_list_tools_async(CORAL_MCP_URL, MCP_ACCESS_TOKEN))
            st.session_state["mcp_tools"] = tools
            st.success(f"Found {len(tools)} tools")
        except Exception as e:
            st.error(f"Failed to list tools: {e}")

if "mcp_tools" in st.session_state:
    for t in st.session_state["mcp_tools"]:
        st.write(f"- **{t['name']}** — {t.get('description')}")

tool_names = [t["name"] for t in st.session_state.get("mcp_tools", [])]
selected_tool = st.selectbox("Select agent", options=(tool_names + ["manual input"]), index=0 if tool_names else 0)

#############################
# NFT structured form (auto-shown when selecting nft-analyst)
#############################
st.header("3) NFT query form")
use_structured = False
if selected_tool == AGENT_NFT_ANALYST or selected_tool == "nft-analyst":
    use_structured = True

if use_structured:
    st.info("Structured NFT search (will call nft-analyst agent)")
    collection_slug = st.text_input("Collection slug / contract id", value="solana-skyliner")
    chain = st.selectbox("Chain", ["solana","ethereum"])
    max_price = st.number_input("Max price (native token)", min_value=0.0, value=3.0, step=0.1)
    trait_filters = st.text_input("Traits (comma-separated)", value="")
    limit = st.number_input("Limit results", min_value=1, max_value=100, value=20)
    buyer_email = st.text_input("Buyer email (for crossmint)", value="")
else:
    st.info("Unstructured query: send plain transcript to the selected agent.")

# Send to agent
if st.button("Send to agent"):
    if "transcript" not in st.session_state and not use_structured:
        st.error("No transcript available")
    else:
        if use_structured:
            arguments = {
                "collection_slug": collection_slug,
                "chain": chain,
                "max_price": float(max_price),
                "traits": [t.strip() for t in trait_filters.split(",") if t.strip()],
                "limit": int(limit)
            }
            target = AGENT_NFT_ANALYST
        else:
            # unstructured: send plain text
            arguments = {"input": st.session_state.get("transcript", "")}
            target = selected_tool if selected_tool!="manual input" else AGENT_NFT_ANALYST

        st.write("Calling", target, "with:", arguments)
        with st.spinner("Calling agent..."):
            try:
                result_obj = asyncio.run(mcp_call_tool_async(CORAL_MCP_URL, target, arguments, MCP_ACCESS_TOKEN))
                # Try to extract structured JSON from result
                parsed = None
                try:
                    parsed = getattr(result_obj, "content", None) or result_obj
                except Exception:
                    parsed = result_obj
                st.subheader("Agent raw response")
                st.write(parsed)

                # If parsed contains rarity_scores and floor_history, render them
                # Some agents return JSON strings inside result; attempt to parse
                def extract_json(x):
                    if isinstance(x, str):
                        try:
                            return json.loads(x)
                        except:
                            return None
                    if isinstance(x, dict):
                        return x
                    # If object with attribute 'json' or 'to_dict', try
                    try:
                        return json.loads(str(x))
                    except:
                        return None

                j = extract_json(parsed) or parsed
                if isinstance(j, dict) and ("rarity_scores" in j or "floor_history" in j):
                    st.success("Structured analysis received — rendering results")
                    rarity = j.get("rarity_scores", [])
                    fh = j.get("floor_history", [])
                    # Rarity table
                    if rarity:
                        import pandas as pd
                        rows=[]
                        for item in rarity:
                            rows.append({
                                "token_id": item.get("token_id"),
                                "rank": item.get("rank"),
                                "score": item.get("score"),
                                "traits": ", ".join(item.get("traits") or []),
                                "image": item.get("image")
                            })
                        df = pd.DataFrame(rows)
                        st.subheader("Rarity scores")
                        st.dataframe(df)
                    # Floor history chart/table
                    if fh:
                        try:
                            import pandas as pd
                            df2 = pd.DataFrame(fh)
                            # ensure timestamps converted
                            df2['timestamp'] = pd.to_datetime(df2['timestamp'])
                            st.subheader("Floor history")
                            st.line_chart(df2.set_index('timestamp')['floor_price'])
                        except Exception as e:
                            st.write("Floor history (raw):", fh)

                    # Save last analysis for minting payload
                    st.session_state["last_analysis"] = j

                    # Prepare Crossmint payload UI
                    st.subheader("Prepare mint / checkout")
                    mint_qty = st.number_input("Quantity to mint", min_value=1, max_value=10, value=1)
                    # pick first token candidate by default
                    pick_idx = st.number_input("Pick rarity index (1-based)", min_value=1, max_value=len(rarity) if rarity else 1, value=1)
                    candidate = rarity[pick_idx-1] if rarity and len(rarity)>=pick_idx else None
                    st.markdown("**Selected candidate**")
                    st.write(candidate)

                    if st.button("Request Crossmint checkout URL"):
                        # Build payload for transaction-agent (or call our server directly)
                        tx_args = {
                            "collection_id": j.get("collection_id") or collection_slug,
                            "action": "create_checkout",
                            "token_id": candidate.get("token_id") if candidate else None,
                            "buyer_email": buyer_email or None,
                            "metadata": {"source":"nova-concierge", "analysis": j.get("summary")},
                            "price": candidate.get("price") if candidate else None
                        }
                        st.write("Calling transaction agent with:", tx_args)
                        with st.spinner("Calling transaction agent..."):
                            try:
                                tx_result = asyncio.run(mcp_call_tool_async(CORAL_MCP_URL, AGENT_TRANSACTION, tx_args, MCP_ACCESS_TOKEN))
                                st.write("Transaction agent result:", tx_result)
                                # if agent returns checkout_url, open or display
                                tx_json = None
                                try:
                                    tx_json = json.loads(str(tx_result))
                                except:
                                    tx_json = tx_result
                                if isinstance(tx_json, dict) and tx_json.get("checkout_url"):
                                    st.success("Checkout URL received")
                                    st.write(tx_json.get("checkout_url"))
                                else:
                                    st.info("Transaction agent did not return checkout_url — using server-side Crossmint endpoint fallback.")
                                    # fallback: POST to our server endpoint which will call Crossmint
                                    payload = {
                                        "collection_id": tx_args["collection_id"],
                                        "token_id": tx_args.get("token_id"),
                                        "buyer_email": tx_args.get("buyer_email"),
                                        "metadata": tx_args.get("metadata"),
                                        "qty": int(mint_qty)
                                    }
                                    try:
                                        r = requests.post(f"{CROSSMINT_SERVER_URL}/api/mint", json=payload, timeout=30)
                                        if r.ok:
                                            st.success("Server-side mint request created")
                                            st.write(r.json())
                                        else:
                                            st.error(f"Server mint failed: {r.status_code} {r.text}")
                                    except Exception as e:
                                        st.error(f"Server-side mint call error: {e}")

                            except Exception as e:
                                st.error(f"Transaction agent call failed: {e}")

                else:
                    # Non-structured response: play TTS if textual
                    try:
                        text_out = None
                        if isinstance(parsed, dict):
                            text_out = parsed.get("text") or parsed.get("summary") or json.dumps(parsed)
                        else:
                            text_out = str(parsed)
                        st.subheader("Agent text output")
                        st.write(text_out)
                        tmp = Path(tempfile.gettempdir()) / "nova_tts.mp3"
                        out = eleven_tts_write(text_out, str(tmp))
                        if out:
                            st.audio(str(out))
                    except Exception as e:
                        st.write("Could not TTS response:", e)

            except Exception as e:
                st.error(f"Agent call failed: {e}")

st.write("---")
st.caption("Notes: Transaction agent and Crossmint flows require server-side keys. Use CROSSMINT_SERVER_URL to point to your server that holds CROSSMINT_SERVER_KEY.")
