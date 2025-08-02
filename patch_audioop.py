"""
Patch for missing audioop module on deployment platforms.
This should be imported before discord.py to prevent import errors.
"""

import sys

def patch_audioop():
    """Patch the audioop module if it's missing."""
    if 'audioop' not in sys.modules:
        try:
            import audioop
        except ImportError:
            # Create a dummy audioop module
            class DummyAudioop:
                def __getattr__(self, name):
                    return lambda *args, **kwargs: None
            sys.modules['audioop'] = DummyAudioop()

# Apply the patch immediately
patch_audioop() 