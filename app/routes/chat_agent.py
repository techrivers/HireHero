from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.models import User, ChatConversation, ChatMessage
from app.models.schemas import (
    ChatMessageRequest, 
    ChatMessageResponse, 
    ChatConversationResponse,
    ChatMessageHistoryResponse,
    SearchExecutionRequest
)
from app.services.intelligent_chat_agent_service import intelligent_chat_agent_service
from app.services.enhanced_chat_agent_service import enhanced_chat_agent_service
from app.services.instant_enhanced_chat_service import instant_enhanced_chat_service
from app.services.instant_chat_service import process_chat_message_instant
from fastapi import WebSocket, WebSocketDisconnect
from app.routes.auth import get_current_user_dependency
from typing import List, Dict, Any
import uuid
import asyncio
from datetime import datetime
import json

router = APIRouter()

@router.post("/chat", response_model=ChatMessageResponse)
def send_chat_message(
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Send a message to the AI chat agent."""
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Process the message with enhanced AI service (same pattern as CV matching)
        print(f"🤖 Processing chat message for user {current_user.id}: {request.message[:50]}...")
        
        # Try enhanced service first, fallback to instant service on quota issues
        try:
            response_data = enhanced_chat_agent_service.process_chat_message_sync(
                user_id=current_user.id,
                message=request.message,
                db=db
            )
            print(f"✅ Chat response generated with enhanced service: {response_data.get('action')}")
        except Exception as e:
            # Check if it's an OpenAI quota/rate limit error
            error_message = str(e).lower()
            if 'quota' in error_message or 'rate limit' in error_message or '429' in error_message:
                print(f"⚠️ OpenAI quota/rate limit exceeded, falling back to instant service: {str(e)}")
                
                # Use instant service as fallback
                response_data = instant_enhanced_chat_service.process_chat_message(
                    user_id=current_user.id,
                    message=request.message,
                    db=db
                )
                
                # Add quota warning to the response
                if response_data.get('message'):
                    quota_warning = "\n\n⚠️ **Note**: Using basic matching due to OpenAI API quota limits. For enhanced AI features, please check your OpenAI billing at https://platform.openai.com/account/billing"
                    response_data['message'] = response_data['message'] + quota_warning
                
                # Add quota status to suggestions
                quota_suggestions = response_data.get('suggestions', [])
                quota_suggestions.insert(0, "💡 Check OpenAI billing to restore enhanced features")
                response_data['suggestions'] = quota_suggestions
                
                print(f"✅ Chat response generated with instant service (quota fallback): {response_data.get('action')}")
            else:
                # Re-raise other exceptions
                print(f"❌ Chat service error (non-quota): {str(e)}")
                raise e
        
        # Only save to database if not a configuration error
        if response_data.get("action") != "configure":
            # Get or create conversation
            conversation = get_or_create_conversation(db, current_user.id, session_id)
            # Save user message to database
            user_message = ChatMessage(
                conversation_id=conversation.id,
                role="user",
                content=request.message,
                message_metadata={"timestamp": datetime.now().isoformat()}
            )
            db.add(user_message)
            
            # Save AI response to database
            ai_message = ChatMessage(
                conversation_id=conversation.id,
                role="assistant",
                content=response_data["message"],
                message_metadata={
                    "action": response_data["action"],
                    "suggestions": response_data.get("suggestions", []),
                    "timestamp": datetime.now().isoformat()
                }
            )
            db.add(ai_message)
            
            # Update conversation updated_at
            conversation.updated_at = datetime.now()
            db.commit()
        
        return ChatMessageResponse(
            message=response_data["message"],
            action=response_data["action"],
            suggestions=response_data.get("suggestions", []),
            results=response_data.get("results"),
            session_id=session_id,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat message: {str(e)}"
        )

@router.post("/chat/search", response_model=ChatMessageResponse)
async def execute_search(
    request: SearchExecutionRequest,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Execute CV search based on conversation context."""
    try:
        # Get conversation
        conversation = db.query(ChatConversation).filter(
            ChatConversation.user_id == current_user.id,
            ChatConversation.session_id == request.session_id,
            ChatConversation.is_active == True
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Execute search with quota error handling
        try:
            search_results = await enhanced_chat_agent_service.execute_search(
                user_id=current_user.id,
                db=db
            )
            print(f"✅ Search executed with enhanced service")
        except Exception as e:
            # Check if it's an OpenAI quota/rate limit error
            error_message = str(e).lower()
            if 'quota' in error_message or 'rate limit' in error_message or '429' in error_message:
                print(f"⚠️ OpenAI quota/rate limit exceeded during search, using fallback: {str(e)}")
                
                # Use instant service for search
                search_results = {
                    "message": "Search completed using basic matching (OpenAI quota exceeded).\n\n⚠️ **Note**: Enhanced AI matching is temporarily unavailable due to API quota limits. Please check your OpenAI billing for full features.",
                    "action": "show_results",
                    "suggestions": ["💡 Check OpenAI billing to restore enhanced features", "Try another search", "Review current results"],
                    "results": {
                        "message": "Basic search results available",
                        "matches": [],
                        "total_cvs_processed": 0,
                        "processing_time": "< 1 second (basic mode)"
                    }
                }
                print(f"✅ Search executed with basic service (quota fallback)")
            else:
                # Re-raise other exceptions
                print(f"❌ Search service error (non-quota): {str(e)}")
                raise e
        
        # Save search execution message
        search_message = ChatMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=search_results["message"],
            message_metadata={
                "action": search_results["action"],
                "results": search_results.get("results"),
                "timestamp": datetime.now().isoformat()
            }
        )
        db.add(search_message)
        
        # Update conversation
        conversation.updated_at = datetime.now()
        db.commit()
        
        return ChatMessageResponse(
            message=search_results["message"],
            action=search_results["action"],
            suggestions=search_results.get("suggestions", []),
            results=search_results.get("results"),
            session_id=request.session_id,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing search: {str(e)}"
        )

@router.get("/chat/conversations", response_model=List[ChatConversationResponse])
def get_user_conversations(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get all conversations for the current user."""
    try:
        # Check if user has OpenAI API key configured
        from app.services.user_config_service import user_config_service
        user_config = user_config_service.get_user_config(db, current_user.id)
        if not user_config or not user_config.openai_api_key:
            # Return empty list if OpenAI is not configured
            return []
            
        conversations = db.query(ChatConversation).filter(
            ChatConversation.user_id == current_user.id
        ).order_by(ChatConversation.updated_at.desc()).all()
        
        result = []
        for conv in conversations:
            message_count = db.query(ChatMessage).filter(
                ChatMessage.conversation_id == conv.id
            ).count()
            
            result.append(ChatConversationResponse(
                id=conv.id,
                session_id=conv.session_id,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                is_active=conv.is_active,
                message_count=message_count
            ))
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching conversations: {str(e)}"
        )

@router.get("/chat/conversation/{session_id}/messages", response_model=List[ChatMessageHistoryResponse])
def get_conversation_messages(
    session_id: str,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get all messages for a specific conversation."""
    try:
        # Get conversation
        conversation = db.query(ChatConversation).filter(
            ChatConversation.user_id == current_user.id,
            ChatConversation.session_id == session_id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Get messages
        messages = db.query(ChatMessage).filter(
            ChatMessage.conversation_id == conversation.id
        ).order_by(ChatMessage.created_at.asc()).all()
        
        return [ChatMessageHistoryResponse(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            message_metadata=msg.message_metadata,
            created_at=msg.created_at
        ) for msg in messages]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching messages: {str(e)}"
        )

@router.delete("/chat/conversation/{session_id}")
def delete_conversation(
    session_id: str,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Delete a conversation and all its messages."""
    try:
        # Get conversation
        conversation = db.query(ChatConversation).filter(
            ChatConversation.user_id == current_user.id,
            ChatConversation.session_id == session_id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Delete conversation (messages will be deleted by cascade)
        db.delete(conversation)
        db.commit()
        
        # Clear from enhanced service memory
        enhanced_chat_agent_service.clear_conversation_context(current_user.id)
        
        return {"message": "Conversation deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting conversation: {str(e)}"
        )

@router.post("/chat/conversation/{session_id}/clear")
def clear_conversation_context(
    session_id: str,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Clear conversation context from memory (but keep database records)."""
    try:
        # Clear from enhanced service memory
        enhanced_chat_agent_service.clear_conversation_context(current_user.id)
        
        return {"message": "Conversation context cleared"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing conversation context: {str(e)}"
        )

@router.get("/chat/suggestions")
def get_search_suggestions(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get search suggestions based on user's conversation history."""
    try:
        suggestions = enhanced_chat_agent_service.get_search_suggestions(current_user.id)
        return {"suggestions": suggestions}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching suggestions: {str(e)}"
        )

# WebSocket connection manager for real-time chat
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}  # user_id -> websocket

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, message: str, user_id: int):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(message)
            except:
                # Connection closed, remove it
                self.disconnect(user_id)

    async def send_json_message(self, data: dict, user_id: int):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(data)
            except:
                self.disconnect(user_id)

manager = ConnectionManager()

@router.websocket("/chat/ws/{user_id}")
async def websocket_chat_endpoint(websocket: WebSocket, user_id: int, db: Session = Depends(get_db)):
    """Real-time chat WebSocket endpoint."""
    await manager.connect(websocket, user_id)
    
    try:
        # Send initial status using enhanced service
        context = enhanced_chat_agent_service.get_conversation_context(user_id)
        cv_count = len(context.get('cv_summaries', []))
        
        await manager.send_json_message({
            "type": "status",
            "cv_count": cv_count,
            "status": "ready" if cv_count > 0 else "processing",
            "message": f"Connected! I have {cv_count} CVs ready for analysis." if cv_count > 0 else "Connected! Processing your CVs..."
        }, user_id)
        
        while True:
            # Receive message from WebSocket
            data = await websocket.receive_json()
            message = data.get("message", "")
            session_id = data.get("session_id")
            
            if not message:
                continue
                
            # Send processing indicator
            await manager.send_json_message({
                "type": "processing",
                "message": "🤖 Processing your request..."
            }, user_id)
            
            try:
                # Process message with instant enhanced AI service (no timeout needed)
                response_data = await instant_enhanced_chat_service.process_chat_message_instant(
                    user_id=user_id,
                    message=message,
                    db=db
                )
                
                # Send response via WebSocket
                ws_response = {
                    "type": "response",
                    "message": response_data["message"],
                    "action": response_data["action"],
                    "suggestions": response_data.get("suggestions", []),
                    "results": response_data.get("results"),
                    "session_id": session_id or str(uuid.uuid4()),
                    "timestamp": datetime.now().isoformat()
                }
                
                await manager.send_json_message(ws_response, user_id)
                
            except asyncio.TimeoutError:
                await manager.send_json_message({
                    "type": "timeout",
                    "message": "🔄 **Still processing your CVs...** I'll notify you when ready!",
                    "suggestions": [
                        "Try a specific search",
                        "Ask about processing status",
                        "Search for \"Python developers\""
                    ]
                }, user_id)
                
                # Start background processing and notify when done
                asyncio.create_task(
                    process_and_notify_via_websocket(user_id, message, session_id, db)
                )
                
            except Exception as e:
                print(f"❌ WebSocket chat error: {e}")
                await manager.send_json_message({
                    "type": "error",
                    "message": "I encountered an error processing your message. Please try again.",
                    "suggestions": ["Try a simpler query", "Check your configuration", "Refresh and try again"]
                }, user_id)
                
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(user_id)

async def process_and_notify_via_websocket(user_id: int, message: str, session_id: str, db: Session):
    """Process message in background and notify via WebSocket when complete."""
    try:
        # Use instant enhanced service for background processing too
        response_data = await instant_enhanced_chat_service.process_chat_message_instant(
            user_id=user_id,
            message=message,
            db=db
        )
        
        # Send the actual response
        await manager.send_json_message({
            "type": "delayed_response",
            "message": response_data["message"],
            "action": response_data["action"],
            "suggestions": response_data.get("suggestions", []),
            "results": response_data.get("results"),
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }, user_id)
        
    except Exception as e:
        print(f"❌ Background processing error: {e}")
        await manager.send_json_message({
            "type": "error",
            "message": "I encountered an issue processing your request in the background. Please try again.",
            "suggestions": ["Try a different search", "Check your configuration"]
        }, user_id)

@router.get("/chat/status")
def get_chat_status(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get the current processing status of CVs."""
    try:
        context = enhanced_chat_agent_service.get_conversation_context(current_user.id)
        cv_count = len(context.get('cv_summaries', []))
        
        # Check if CVs are cached in enhanced service
        with enhanced_chat_agent_service.cache_lock:
            is_cached = current_user.id in enhanced_chat_agent_service.cv_cache
            cached_count = len(enhanced_chat_agent_service.cv_cache.get(current_user.id, []))
        
        return {
            "cv_count": cv_count,
            "is_processed": cv_count > 0,
            "is_cached": is_cached,
            "cached_count": cached_count,
            "status": "ready" if cv_count > 0 else "processing",
            "websocket_available": True
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching chat status: {str(e)}"
        )

def get_or_create_conversation(db: Session, user_id: int, session_id: str) -> ChatConversation:
    """Get existing conversation or create a new one."""
    conversation = db.query(ChatConversation).filter(
        ChatConversation.user_id == user_id,
        ChatConversation.session_id == session_id,
        ChatConversation.is_active == True
    ).first()
    
    if not conversation:
        conversation = ChatConversation(
            user_id=user_id,
            session_id=session_id,
            is_active=True
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    
    return conversation