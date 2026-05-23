def is_badge():
    """Are we a badge?"""
    try:
        import machine

        return True
    except ModuleNotFoundError:
        return False
