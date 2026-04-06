"""Flask extensions — initialized in Application Factory."""
# SocketIO is initialized lazily to support graceful degradation
_socketio = None


def get_socketio():
    """Get SocketIO instance (may be None if Redis unavailable)."""
    return _socketio


def set_socketio(instance):
    """Set SocketIO instance."""
    global _socketio
    _socketio = instance
