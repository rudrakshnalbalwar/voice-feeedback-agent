from livekit import api
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def generate_token(room_name: str, participant_name: str):
    """Generate a LiveKit access token"""
    
    # Get credentials from .env file
    api_key = os.getenv('LIVEKIT_API_KEY')
    api_secret = os.getenv('LIVEKIT_API_SECRET')
    url = os.getenv('LIVEKIT_URL')
    
    if not all([api_key, api_secret, url]):
        print("Error: Missing credentials in .env file")
        print("Required: LIVEKIT_API_KEY, LIVEKIT_API_SECRET, LIVEKIT_URL")
        return None
    
    # Create token
    token = api.AccessToken(api_key, api_secret) \
        .with_identity(participant_name) \
        .with_name(participant_name) \
        .with_grants(api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
        ))
    
    jwt_token = token.to_jwt()
    
    print(f"\n{'='*60}")
    print(f"LiveKit Connection Details")
    print(f"{'='*60}")
    print(f"URL: {url}")
    print(f"Room: {room_name}")
    print(f"Identity: {participant_name}")
    print(f"\nToken (copy this):")
    print(f"{jwt_token}")
    print(f"{'='*60}\n")
    
    return jwt_token

if __name__ == "__main__":
    # Generate token for the feedback agent room
    generate_token(
        room_name="feedback-agent",
        participant_name="user1"
    )