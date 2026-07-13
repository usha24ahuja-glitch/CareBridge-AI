from unittest.mock import MagicMock
import pytest
from src.handlers.events import register_events
from src.session_manager import session_manager

def test_assistant_thread_started_event():
    """Tests that the assistant_thread_started event sets up the session and posts the welcome blocks."""
    app_mock = MagicMock()
    client_mock = MagicMock()
    
    # Trigger event registration to capture the handler
    register_events(app_mock)
    
    # Retrieve registered handler for assistant_thread_started
    thread_started_handler = None
    for call in app_mock.event.call_args_list:
        event_name = call.args[0]
        if event_name == "assistant_thread_started":
            thread_started_handler = call.args[0] # wait, it registers as decorator
            # Let's get the decorated function
            
    # Mocking app.event decorator return
    # A cleaner way is to mock the app structure or import the handlers directly.
    # Let's find the events decorators registered:
    handlers = {}
    def mock_decorator(event_name):
        def decorator(func):
            handlers[event_name] = func
            return func
        return decorator
        
    app_mock.event.side_effect = mock_decorator
    register_events(app_mock)
    
    assert "assistant_thread_started" in handlers
    
    # Invoke the handler
    event_payload = {
        "user": "U12345",
        "assistant_thread": {
            "id": "thread-12345",
            "channel_id": "D12345",
            "user_id": "U12345"
        }
    }
    
    say_mock = MagicMock()
    handlers["assistant_thread_started"](event_payload, say_mock, client_mock)
    
    # 1. Verify session was started and thread_ts was recorded
    session = session_manager.get_session("U12345")
    assert session is not None
    assert session.thread_ts == "thread-12345"
    
    # 2. Verify status was set
    client_mock.assistant_threads_setStatus.assert_called_once_with(
        channel_id="D12345",
        thread_ts="thread-12345",
        status="preparing screening welcome..."
    )
    
    # 3. Verify chat_postMessage was called with thread_ts
    client_mock.chat_postMessage.assert_called_once()
    post_kwargs = client_mock.chat_postMessage.call_args.kwargs
    assert post_kwargs["channel"] == "D12345"
    assert post_kwargs["thread_ts"] == "thread-12345"
    assert "CareBridge" in post_kwargs["text"]
    
    # Clean up session
    session_manager.clear_session("U12345")
