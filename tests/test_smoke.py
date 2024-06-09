import sim.run

def test_import_badgebot_app_and_app_export():
    from sim.apps.BadgeBot import BadgeBotApp
    import sim.apps.BadgeBot.app as BadgeBot
    assert BadgeBot.__app_export__ == BadgeBotApp

def test_import_hexdrive_app_and_app_export():
    from sim.apps.BadgeBot.hexdrive import HexDriveApp
    import sim.apps.BadgeBot.hexdrive as HexDrive
    assert HexDrive.__app_export__ == HexDriveApp
