import gi
gi.require_version('Gio', '2.0')
gi.require_version('GLib', '2.0')
from gi.repository import Gio, GLib

class ScreencastPortal:
    def __init__(self):
        self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self.portal_dest = "org.freedesktop.portal.Desktop"
        self.portal_path = "/org/freedesktop/portal/desktop"

        # We need a unique sender name part for the request handles
        unique_name = self.bus.get_unique_name()[1:].replace('.', '_')
        self.request_path_prefix = f"/org/freedesktop/portal/desktop/request/{unique_name}/"
        self.request_token = 0

        self.on_success = None
        self.on_cancel = None

        self.session_path = None
        self.request_subs = []

    def next_token(self):
        self.request_token += 1
        return f"troika_{self.request_token}"

    def request_screencast(self, on_success, on_cancel):
        self.on_success = on_success
        self.on_cancel = on_cancel

        token = self.next_token()
        req_path = self.request_path_prefix + token

        # Subscribe to response
        sub_id = self.bus.signal_subscribe(
            self.portal_dest,
            "org.freedesktop.portal.Request",
            "Response",
            req_path,
            None,
            Gio.DBusSignalFlags.NONE,
            self.on_create_session_response,
            None
        )
        self.request_subs.append(sub_id)

        options = GLib.Variant('a{sv}', {
            'handle_token': GLib.Variant('s', token),
            'session_handle_token': GLib.Variant('s', token),
            'multiple': GLib.Variant('b', False),
            'types': GLib.Variant('u', 1) # Monitor only
        })

        self.bus.call(
            self.portal_dest,
            self.portal_path,
            "org.freedesktop.portal.ScreenCast",
            "CreateSession",
            GLib.Variant('(a{sv})', (options,)),
            None,
            Gio.DBusCallFlags.NONE,
            -1,
            None,
            self.on_call_done,
            None
        )

    def on_create_session_response(self, connection, sender_name, object_path, interface_name, signal_name, parameters, user_data):
        self.unsubscribe_all()
        response, results = parameters.unpack()

        if response != 0:
            if self.on_cancel:
                self.on_cancel("User cancelled or failed (CreateSession).")
            return

        self.session_path = results.get('session_handle')
        self.select_sources()

    def select_sources(self):
        token = self.next_token()
        req_path = self.request_path_prefix + token

        sub_id = self.bus.signal_subscribe(
            self.portal_dest,
            "org.freedesktop.portal.Request",
            "Response",
            req_path,
            None,
            Gio.DBusSignalFlags.NONE,
            self.on_select_sources_response,
            None
        )
        self.request_subs.append(sub_id)

        options = GLib.Variant('a{sv}', {
            'handle_token': GLib.Variant('s', token),
            'multiple': GLib.Variant('b', False),
            'types': GLib.Variant('u', 1) # Monitor
        })

        self.bus.call(
            self.portal_dest,
            self.portal_path,
            "org.freedesktop.portal.ScreenCast",
            "SelectSources",
            GLib.Variant('(oa{sv})', (self.session_path, options)),
            None,
            Gio.DBusCallFlags.NONE,
            -1,
            None,
            self.on_call_done,
            None
        )

    def on_select_sources_response(self, connection, sender_name, object_path, interface_name, signal_name, parameters, user_data):
        self.unsubscribe_all()
        response, results = parameters.unpack()

        if response != 0:
            if self.on_cancel:
                self.on_cancel("User cancelled (SelectSources).")
            return

        self.start_session()

    def start_session(self):
        token = self.next_token()
        req_path = self.request_path_prefix + token

        sub_id = self.bus.signal_subscribe(
            self.portal_dest,
            "org.freedesktop.portal.Request",
            "Response",
            req_path,
            None,
            Gio.DBusSignalFlags.NONE,
            self.on_start_response,
            None
        )
        self.request_subs.append(sub_id)

        options = GLib.Variant('a{sv}', {
            'handle_token': GLib.Variant('s', token)
        })

        self.bus.call(
            self.portal_dest,
            self.portal_path,
            "org.freedesktop.portal.ScreenCast",
            "Start",
            GLib.Variant('(osa{sv})', (self.session_path, "", options)),
            None,
            Gio.DBusCallFlags.NONE,
            -1,
            None,
            self.on_call_done,
            None
        )

    def on_start_response(self, connection, sender_name, object_path, interface_name, signal_name, parameters, user_data):
        self.unsubscribe_all()
        response, results = parameters.unpack()

        if response != 0:
            if self.on_cancel:
                self.on_cancel("User cancelled (Start).")
            return

        streams = results.get('streams', [])
        if not streams:
            if self.on_cancel:
                self.on_cancel("No streams returned by portal.")
            return

        # streams is a list of (node_id, dict)
        self.node_id = streams[0][0]

        # Now OpenPipeWireRemote
        self.open_pipewire_remote()

    def open_pipewire_remote(self):
        options = GLib.Variant('a{sv}', {})
        self.bus.call_with_unix_fd_list(
            self.portal_dest,
            self.portal_path,
            "org.freedesktop.portal.ScreenCast",
            "OpenPipeWireRemote",
            GLib.Variant('(oa{sv})', (self.session_path, options)),
            Gio.DBusCallFlags.NONE,
            -1,
            None,
            None,
            self.on_open_pipewire_remote_done,
            None
        )

    def on_open_pipewire_remote_done(self, source, result, user_data):
        try:
            res, fd_list = source.call_with_unix_fd_list_finish(result)
            if fd_list and fd_list.get_length() > 0:
                fd = fd_list.get(0)
            else:
                fd = -1 # Should not happen typically, but handled as fallback

            if self.on_success:
                self.on_success(self.node_id, fd)
        except Exception as e:
            print("DBus Call Error (OpenPipeWireRemote):", e)
            if self.on_cancel:
                self.on_cancel(str(e))

    def on_call_done(self, source, result, user_data):
        try:
            source.call_finish(result)
        except Exception as e:
            print("DBus Call Error:", e)
            if self.on_cancel:
                self.on_cancel(str(e))

    def unsubscribe_all(self):
        for sub_id in self.request_subs:
            self.bus.signal_unsubscribe(sub_id)
        self.request_subs = []

    def cleanup(self):
        self.unsubscribe_all()
        if self.session_path:
            try:
                self.bus.call_sync(
                    self.portal_dest,
                    self.session_path,
                    "org.freedesktop.portal.Session",
                    "Close",
                    None,
                    None,
                    Gio.DBusCallFlags.NONE,
                    -1,
                    None
                )
            except Exception:
                pass
            self.session_path = None
