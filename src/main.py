import sys
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio
from src.ui import TroikaApp

class Application(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.github.scientifica007.troikadlite",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = TroikaApp(application=self)
        win.present()

def main():
    app = Application()
    return app.run(sys.argv)

if __name__ == '__main__':
    sys.exit(main())
