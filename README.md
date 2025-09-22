# Nova — Voice-First Web3 Concierge (Streamlit App)

A Streamlit-based voice-first Web3 concierge application that leverages Coral MCP (Model Context Protocol) for multi-agent orchestration, speech-to-text via AIMLAPI, text-to-speech via ElevenLabs, and NFT minting via Crossmint.

## Features

- 🎤 **Voice Input**: Upload audio files (WAV/MP3) or type text directly in the web interface
- 🤖 **Multi-Agent Support**: Discover and interact with Coral MCP agents/tools seamlessly
- 🗣️ **Text-to-Speech**: Convert agent responses to audio using ElevenLabs TTS service
- ⛓️ **Web3 Integration**: Optional NFT minting functionality via Crossmint API
- 🔄 **Real-time Processing**: Async MCP client for efficient and responsive agent communication

## Prerequisites

- Python 3.8 or higher
- Coral MCP Server running (see Multi-Agent-Demo directory for setup)
- API keys for external services (AIMLAPI, ElevenLabs, Crossmint)

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd nova-voice-first-web3-concierge
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   Copy the example environment file and update with your API keys and server URLs:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` to set the required variables (see Configuration section).

## Configuration

Set the following environment variables in your `.env` file:

| Variable           | Description                          | Required |
|--------------------|----------------------------------|----------|
| `CORAL_SERVER_URL`  | URL of the Coral MCP server       | Yes      |
| `CORAL_SERVER_TOKEN`| Optional bearer token for Coral   | No       |
| `AIMLAPI_KEY`       | API key for AIMLAPI speech-to-text| Yes      |
| `ELEVENLABS_API_KEY`| API key for ElevenLabs text-to-speech | Yes  |
| `ELEVENLABS_VOICE`  | Voice ID for ElevenLabs TTS       | Yes      |
| `CROSSMINT_CLIENT_KEY` | Crossmint client key (optional) | No       |
| `CROSSMINT_SERVER_KEY` | Crossmint server key (optional) | No       |

## Usage

1. **Start the Streamlit app**:
   ```bash
   streamlit run nova_streamlit.py
   ```

2. **Open the web interface**:
   Navigate to [http://localhost:8501](http://localhost:8501) in your browser.

3. **Typical workflow**:
   - Upload an audio file or type your request
   - Discover available Coral agents/tools
   - Send your query to a selected agent and receive a response
   - Optionally mint NFTs using Crossmint integration

## Architecture

- **Frontend**: Streamlit web interface for user interaction
- **Speech Processing**: AIMLAPI for speech-to-text, ElevenLabs for text-to-speech
- **Agent Communication**: Async MCP client managing multi-agent orchestration
- **Web3 Integration**: Crossmint API for NFT minting and management

## Development

### Adding Live Microphone Recording

To enable browser-based microphone recording, install the additional dependency:

```bash
pip install streamlit-webrtc
```

Then modify the audio input section in `nova_streamlit.py` to include a WebRTC recorder component.

### Custom Agent Integration

The app automatically discovers tools from your Coral MCP server. To add custom agents:

1. Implement your agent following the MCP protocol
2. Register it in your Coral server configuration
3. Restart the Coral server
4. The agent will appear in the "Discover agents" section of the app

## Troubleshooting

- **Coral MCP Server Connection Issues**: Ensure the Coral server is running and accessible at the configured URL
- **Speech-to-Text or Text-to-Speech Errors**: Verify API keys and service availability
- **Audio Playback Problems**: Confirm your browser supports audio playback
- **NFT Minting Issues**: Check Crossmint configuration and collection setup

## License

[Add your license information here]
