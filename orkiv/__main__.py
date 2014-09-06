from kivy.app import App
from kivy.uix.anchorlayout import AnchorLayout
from kivy.properties import ObjectProperty
from sleekxmpp import ClientXMPP
from kivy.uix.textinput import TextInput
from kivy.uix.modalview import ModalView
from kivy.uix.label import Label
from sleekxmpp.exceptions import XMPPError
from sleekxmpp.jid import InvalidJID
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty
from kivy.uix.listview import ListItemButton
import datetime
from kivy.utils import escape_markup


class Orkiv(App):
    icon = 'customicon.png'

    def __init__(self):
        super(Orkiv, self).__init__()
        self.xmpp = None

    def connect_to_jabber(self, jabber_id, password):
        self.xmpp = ClientXMPP(jabber_id, password)
        self.xmpp.reconnect_max_attempts = 1
        connected = self.xmpp.connect()
        if not connected:
            raise XMPPError("unable to connect")
        self.xmpp.process()
        self.xmpp.send_presence()
        self.xmpp.get_roster()
        self.xmpp.add_event_handler('message', self.root.handle_xmpp_message)

    def disconnect_xmpp(self):
        if self.xmpp and self.xmpp.state.ensure("connected"):
            self.xmpp.abort()
        self.xmpp = None

    def on_stop(self):
        self.disconnect_xmpp()

class AccountDetailsForm(AnchorLayout):
    server_box = ObjectProperty()
    username_box = ObjectProperty()
    password_box = ObjectProperty()

    def login(self):
    	jabber_id = self.username_box.text + "@" + self.server_box.text
        modal = ConnectionModal(jabber_id, self.password_box.text)
        modal.open()

class AccountDetailsTextInput(TextInput):
    next = ObjectProperty()

    def _keyboard_on_key_down(self, window, keycode, text, modifiers):
        if keycode[0] == 9:  # 9 is the keycode for
            self.next.focus = True
        elif keycode[0] == 13:  # 13 is the keycode for
            self.parent.parent.parent.login()  # this is not future friendly
        else:
            super(AccountDetailsTextInput, self)._keyboard_on_key_down(
                    window, keycode, text, modifiers)

class ConnectionModal(ModalView):
    def __init__(self, jabber_id, password):
        super(ConnectionModal, self).__init__(auto_dismiss=False,
            anchor_y="bottom")
        self.label = Label(text="Connecting to %s..." % jabber_id)
        self.add_widget(self.label)
        self.jabber_id = jabber_id
        self.password = password
        self.on_open = self.connect_to_jabber

    def connect_to_jabber(self):
        app = Orkiv.get_running_app()
        try:
            app.connect_to_jabber(self.jabber_id, self.password)
            app.root.show_buddy_list()
            self.dismiss()
        except (XMPPError, InvalidJID):
            self.label.text = "Sorry, couldn't connect, check your credentials"
            button = Button(text="Try Again")
            button.size_hint = (1.0, None)
            button.height = "40dp"
            button.bind(on_press=self.dismiss)
            self.add_widget(button)
            app.disconnect_xmpp()

class BuddyList(BoxLayout):
    list_view = ObjectProperty()

    def __init__(self):
        super(BuddyList, self).__init__()
        self.app = Orkiv.get_running_app()
        self.list_view.adapter.data = sorted(self.app.xmpp.client_roster.keys())

    def roster_converter(self, index, jabberid):
        result = {
            "jabberid": jabberid,
            "full_name": self.app.xmpp.client_roster[jabberid]['name']
        }

        presence = sorted(
            self.app.xmpp.client_roster.presence(jabberid).values(),
            key=lambda p: p.get("priority", 100), reverse=True)

        if presence:
            result['status_message'] = presence[0].get('status', '')
            show = presence[0].get('show')
            result['online_status'] = show if show else "available"
        else:
            result['status_message'] = ""
            result['online_status'] = "offline"

        if index % 2:
            result['background_color'] = (0, 0, 0, 1)
        else:
            result['background_color'] = (0.05, 0.05, 0.07, 1)
        return result

class OrkivRoot(BoxLayout):
    def __init__(self):
        super(OrkivRoot, self).__init__()
        self.buddy_list = None
        self.chat_windows = {}

    def show_buddy_list(self):
        self.clear_widgets()
        if not self.buddy_list:
            self.buddy_list = BuddyList()
        for buddy_list_items in self.buddy_list.list_view.adapter.selection:
            buddy_list_items.deselect()
        self.add_widget(self.buddy_list)

    def get_chat_window(self, jabber_id):
        if jabber_id not in self.chat_windows:
            self.chat_windows[jabber_id] = ChatWindow(jabber_id=jabber_id)
        return self.chat_windows[jabber_id]

    def show_buddy_chat(self, jabber_id):
        self.remove_widget(self.buddy_list)
        self.add_widget(self.get_chat_window(jabber_id))

    def handle_xmpp_message(self, message):
        if message['type'] not in ['normal', 'chat']:
            return
        jabber_id = message['from'].bare

        chat_window = self.get_chat_window(jabber_id)
        chat_window.append_chat_message(jabber_id, message['body'], color="aaaaff")

class BuddyListItem(BoxLayout, ListItemButton):
    jabberid = StringProperty()
    full_name = StringProperty()
    status_message = StringProperty()
    online_status = StringProperty()
    background = ObjectProperty()

class ChatWindow(BoxLayout):
    jabber_id = StringProperty()
    chat_log_label = ObjectProperty()
    send_chat_textinput = ObjectProperty()

    def append_chat_message(self, sender, message, color):
        self.chat_log_label.text += "[b](%s) [color=%s]%s[/color][/b]: %s\n" % (
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                color,
                escape_markup(sender),
                escape_markup(message))

    def send_message(self):
        app = Orkiv.get_running_app()
        app.xmpp.send_message(
            mto=self.jabber_id,
            mbody=self.send_chat_textinput.text)
        self.append_chat_message("Me:", self.send_chat_textinput.text, color="aaffbb")
        self.send_chat_textinput.text = ''

Orkiv().run()
