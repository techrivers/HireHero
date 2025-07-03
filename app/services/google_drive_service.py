import os
import json
from typing import List, Dict, Any, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session
from app.models.models import User, UserConfig
from app.utils.encryption import encryption_service
from dotenv import load_dotenv

load_dotenv()

class GoogleDriveService:
    def __init__(self):
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
        self.scopes = ['https://www.googleapis.com/auth/drive.readonly']
    
    def get_authorization_url(self, user_id: int) -> str:
        """Get Google OAuth2 authorization URL."""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=self.scopes
        )
        flow.redirect_uri = self.redirect_uri
        
        authorization_url, _ = flow.authorization_url(
            access_type='offline',  # This is crucial for getting refresh tokens
            prompt='consent',  # Force consent screen to get refresh token
            include_granted_scopes='true',
            state=str(user_id)  # Include user ID in state parameter
        )
        
        return authorization_url
    
    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        print(f"🔄 Exchanging authorization code for tokens...")
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=self.scopes
        )
        flow.redirect_uri = self.redirect_uri
        
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        
        token_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        print(f"✅ Successfully exchanged code for tokens")
        print(f"🔑 Access token: {credentials.token[:20]}...")
        print(f"🔄 Refresh token: {'✅ Present' if credentials.refresh_token else '❌ Missing'}")
        
        if not credentials.refresh_token:
            print("⚠️ WARNING: No refresh token received! User may need to re-authorize.")
        
        return token_data
    
    def save_user_tokens(self, db: Session, user_id: int, tokens: Dict[str, Any]) -> bool:
        """Save user's Google Drive tokens to database."""
        print(f"💾 Saving tokens for user {user_id}")
        
        try:
            user_config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
            if not user_config:
                print(f"📝 Creating new user config for user {user_id}")
                user_config = UserConfig(user_id=user_id)
                db.add(user_config)
            else:
                print(f"📝 Updating existing user config for user {user_id}")
            
            # Encrypt and save full token data
            token_json = json.dumps(tokens)
            user_config.google_drive_token = encryption_service.encrypt(token_json)
            print(f"💾 Saved encrypted access token data")
            
            # Always save refresh token separately if present
            if tokens.get('refresh_token'):
                user_config.google_drive_refresh_token = encryption_service.encrypt(tokens['refresh_token'])
                print(f"🔄 Saved encrypted refresh token")
            else:
                print(f"⚠️ WARNING: No refresh token to save!")
            
            # Update setup completion status
            user_config.is_setup_complete = (
                user_config.google_drive_token is not None and 
                user_config.openai_api_key is not None
            )
            print(f"✅ Setup complete status: {user_config.is_setup_complete}")
            
            db.commit()
            print(f"✅ Successfully saved tokens for user {user_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving tokens for user {user_id}: {e}")
            import traceback
            traceback.print_exc()
            db.rollback()
            return False
    
    def refresh_access_token(self, db: Session, user_id: int) -> bool:
        """Refresh access token using refresh token and save to database."""
        print(f"🔄 Refreshing access token for user {user_id}")
        
        try:
            user_config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
            if not user_config:
                print(f"❌ No user config found for user {user_id}")
                return False
            
            # Get refresh token
            if not user_config.google_drive_refresh_token:
                print(f"❌ No refresh token found for user {user_id}")
                return False
            
            refresh_token = encryption_service.decrypt(user_config.google_drive_refresh_token)
            if not refresh_token:
                print(f"❌ Failed to decrypt refresh token for user {user_id}")
                return False
            
            # Create credentials with refresh token
            credentials = Credentials(
                token=None,  # Will be refreshed
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=self.scopes
            )
            
            # Refresh the token
            print(f"🔄 Making token refresh request...")
            credentials.refresh(Request())
            
            # Save new tokens to database
            new_token_data = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            
            # Update database with new tokens
            user_config.google_drive_token = encryption_service.encrypt(json.dumps(new_token_data))
            if credentials.refresh_token:
                user_config.google_drive_refresh_token = encryption_service.encrypt(credentials.refresh_token)
            
            db.commit()
            print(f"✅ Successfully refreshed and saved new access token for user {user_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error refreshing access token for user {user_id}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_user_credentials(self, db: Session, user_id: int) -> Optional[Credentials]:
        """Get user's Google Drive credentials with automatic token refresh."""
        print(f"🔑 Getting credentials for user {user_id}")
        
        try:
            user_config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
            if not user_config or not user_config.google_drive_token:
                print(f"❌ No Google Drive token found for user {user_id}")
                return None
            
            # Decrypt tokens
            token_json = encryption_service.decrypt(user_config.google_drive_token)
            if not token_json:
                print(f"❌ Failed to decrypt token for user {user_id}")
                return None
            
            token_data = json.loads(token_json)
            
            credentials = Credentials(
                token=token_data.get('token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri'),
                client_id=token_data.get('client_id'),
                client_secret=token_data.get('client_secret'),
                scopes=token_data.get('scopes')
            )
            
            # Check if token is expired and refresh if necessary
            if credentials.expired and credentials.refresh_token:
                print(f"🔄 Token expired, refreshing for user {user_id}")
                if self.refresh_access_token(db, user_id):
                    # Get the refreshed credentials
                    return self.get_user_credentials(db, user_id)
                else:
                    print(f"❌ Failed to refresh expired token for user {user_id}")
                    return None
            
            print(f"✅ Successfully retrieved valid credentials for user {user_id}")
            return credentials
            
        except Exception as e:
            print(f"❌ Error getting credentials for user {user_id}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def find_folder_by_name(self, db: Session, user_id: int, folder_name: str) -> Optional[str]:
        """Find folder ID by name in user's Google Drive."""
        print(f"🔍 Looking for folder '{folder_name}' for user {user_id}")
        
        credentials = self.get_user_credentials(db, user_id)
        if not credentials:
            print(f"❌ No Google Drive credentials found for user {user_id}")
            return None
        
        try:
            service = build('drive', 'v3', credentials=credentials)
            
            # Search for folder
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
            print(f"🔍 Searching with query: {query}")
            
            results = service.files().list(q=query, fields="files(id, name)").execute()
            
            files = results.get('files', [])
            print(f"📁 Found {len(files)} folder(s) matching '{folder_name}'")
            
            if files:
                folder_id = files[0]['id']
                print(f"✅ Found folder '{folder_name}' with ID: {folder_id}")
                return folder_id
            else:
                print(f"❌ No folder named '{folder_name}' found in Google Drive")
                return None
        except HttpError as e:
            print(f"❌ Error finding folder: {e}")
            return None
    
    def list_files_in_folder(self, db: Session, user_id: int, folder_name: str) -> List[Dict[str, Any]]:
        """List all files in a specific folder."""
        print(f"📂 Listing files in folder '{folder_name}' for user {user_id}")
        
        folder_id = self.find_folder_by_name(db, user_id, folder_name)
        if not folder_id:
            print(f"❌ Cannot list files: folder '{folder_name}' not found")
            return []
        
        credentials = self.get_user_credentials(db, user_id)
        if not credentials:
            print(f"❌ Cannot list files: no credentials for user {user_id}")
            return []
        
        try:
            service = build('drive', 'v3', credentials=credentials)
            
            # Get files in folder
            query = f"'{folder_id}' in parents and trashed=false"
            print(f"🔍 Listing files with query: {query}")
            
            results = service.files().list(
                q=query,
                fields="files(id, name, mimeType, size, webViewLink, webContentLink)"
            ).execute()
            
            files = results.get('files', [])
            print(f"📄 Found {len(files)} file(s) in folder '{folder_name}'")
            
            for file in files:
                print(f"  📄 {file.get('name')} (ID: {file.get('id')}, Type: {file.get('mimeType')})")
            
            return files
        except HttpError as e:
            print(f"❌ Error listing files: {e}")
            return []
    
    def download_file(self, db: Session, user_id: int, file_id: str) -> Optional[bytes]:
        """Download file content from Google Drive."""
        credentials = self.get_user_credentials(db, user_id)
        if not credentials:
            return None
        
        try:
            service = build('drive', 'v3', credentials=credentials)
            
            # Get file metadata
            file_metadata = service.files().get(fileId=file_id).execute()
            mime_type = file_metadata.get('mimeType')
            
            # Handle Google Workspace files
            if mime_type.startswith('application/vnd.google-apps'):
                if 'document' in mime_type:
                    # Export Google Doc as PDF
                    request = service.files().export_media(
                        fileId=file_id,
                        mimeType='application/pdf'
                    )
                elif 'spreadsheet' in mime_type:
                    # Export Google Sheet as Excel
                    request = service.files().export_media(
                        fileId=file_id,
                        mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                else:
                    return None
            else:
                # Regular file download
                request = service.files().get_media(fileId=file_id)
            
            file_content = request.execute()
            return file_content
        except HttpError as e:
            print(f"Error downloading file: {e}")
            return None

google_drive_service = GoogleDriveService()
