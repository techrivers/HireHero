#!/usr/bin/env python3
import sys
sys.path.append('/app')
from app.services.google_drive_service import google_drive_service
from app.models.database import SessionLocal
from googleapiclient.discovery import build

# Get database session
db = SessionLocal()
user_id = 4  # Sana's user ID

try:
    print('=== GOOGLE DRIVE DEBUG SESSION ===')
    
    # Get credentials
    credentials = google_drive_service.get_user_credentials(db, user_id)
    if not credentials:
        print('❌ Failed to get credentials')
        exit()
    
    print('✅ Credentials obtained')
    
    # Build service directly
    service = build('drive', 'v3', credentials=credentials)
    print('✅ Google Drive service built')
    
    # 1. List ALL folders in Google Drive
    print('\n=== ALL FOLDERS IN GOOGLE DRIVE ===')
    try:
        results = service.files().list(
            q='mimeType="application/vnd.google-apps.folder" and trashed=false',
            fields='files(id, name)',
            pageSize=50
        ).execute()
        
        folders = results.get('files', [])
        print(f'Found {len(folders)} folders:')
        for folder in folders:
            print(f'  📁 "{folder["name"]}" (ID: {folder["id"]})')
            
    except Exception as e:
        print(f'❌ Error listing folders: {e}')
    
    # 2. Search specifically for cvs folder
    print('\n=== SEARCHING FOR "cvs" FOLDER ===')
    try:
        query = 'name="cvs" and mimeType="application/vnd.google-apps.folder" and trashed=false'
        print(f'Query: {query}')
        
        results = service.files().list(
            q=query,
            fields='files(id, name)'
        ).execute()
        
        cvs_folders = results.get('files', [])
        print(f'Found {len(cvs_folders)} folders named "cvs":')
        
        if cvs_folders:
            for folder in cvs_folders:
                folder_id = folder['id']
                print(f'  📁 "{folder["name"]}" (ID: {folder_id})')
                
                # 3. List files in cvs folder
                print(f'\n=== FILES IN "cvs" FOLDER ({folder_id}) ===')
                try:
                    file_query = f"'{folder_id}' in parents and trashed=false"
                    print(f'File query: {file_query}')
                    
                    file_results = service.files().list(
                        q=file_query,
                        fields='files(id, name, mimeType, size)',
                        pageSize=50
                    ).execute()
                    
                    files = file_results.get('files', [])
                    print(f'Found {len(files)} files:')
                    for file in files:
                        size = file.get('size', 'N/A')
                        if size != 'N/A':
                            size = f'{int(size) // 1024} KB'
                        print(f'  📄 "{file["name"]}" ({file["mimeType"]}) - Size: {size}')
                        
                except Exception as e:
                    print(f'❌ Error listing files in cvs folder: {e}')
        else:
            print('❌ No folders named "cvs" found')
            
    except Exception as e:
        print(f'❌ Error searching for cvs folder: {e}')
    
    # 4. Test the actual service method
    print('\n=== TESTING SERVICE METHOD ===')
    try:
        files = google_drive_service.list_files_in_folder(db, user_id, 'cvs')
        print(f'Service method returned {len(files)} files:')
        for file in files:
            print(f'  📄 {file}')
    except Exception as e:
        print(f'❌ Service method error: {e}')

except Exception as e:
    print(f'❌ Script error: {e}')
    import traceback
    traceback.print_exc()
finally:
    db.close()