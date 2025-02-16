import os
import argparse

from flask import Flask, render_template, request, redirect, url_for, \
    jsonify
from ovos_bus_client.message import Message
from ovos_utils.fakebus import FakeBus
from ovos_utils.log import init_service_logger, LOG
from ovos_utils.xdg_utils import xdg_state_home

from hivemind_bus_client import HiveMessageBusClient

platform = "JarbasFlaskChatRoomV0.2"
bot_name = "HiveMind"

app = Flask(__name__)


class MessageHandler:
    messages = {}
    hivemind: HiveMessageBusClient = None

    @classmethod
    def connect(cls):
        cls.hivemind = HiveMessageBusClient(useragent=platform,
                                            internal_bus=FakeBus())
        cls.hivemind.connect(site_id="flask")
        cls.hivemind.on_mycroft("speak", cls.handle_speak)
        cls.hivemind.on_mycroft("ovos.common_play.play", cls.handle_ocp_play)
        cls.hivemind.on_mycroft('mycroft.audio.service.play', cls.handle_legacy_play)

    @classmethod
    def handle_legacy_play(cls, message: Message):
        tracks = message.data["tracks"]
        room = message.context["room"]
        # TODO - implement playback in browser if desired
        cls.append_message(True, "\n".join([str(t) for t in tracks]),
                           bot_name, room)

    @classmethod
    def handle_ocp_play(cls, message: Message):
        track = message.data["media"]
        room = message.context["room"]
        # TODO - implement playback and nice UI card in browser if desired
        msg = f"{track['artist']} - {track['title']}"
        cls.append_message(True, msg, bot_name, room)
        cls.append_message(True, track['uri'], bot_name, room)

    @classmethod
    def handle_speak(cls, message: Message):
        room = message.context["room"]
        utterance = message.data["utterance"]
        user = message.context["user"]  # could have been handled in skill
        cls.append_message(True, f"@{user} - {utterance}", bot_name, room)

    @classmethod
    def say(cls, utterance, username="Anon", room="general"):
        MessageHandler.append_message(False, utterance, username, room)
        msg = Message("recognizer_loop:utterance",
                      {"utterances": [utterance]},
                      {"source": platform,
                       "room": room,
                       "user": username,
                       "destination": "skills",
                       "platform": platform}
                      )
        cls.hivemind.emit_mycroft(msg)

    @classmethod
    def append_message(cls, incoming, message, username, room):
        if room not in MessageHandler.messages:
            MessageHandler.messages[room] = []
        MessageHandler.messages[room].append({'incoming': incoming,
                                              'username': username,
                                              'message': message})

    @classmethod
    def get_messages(cls, room):
        return MessageHandler.messages.get(room, [])


@app.route('/', methods=['GET'])
def general():
    room = "general"
    return redirect(url_for("chatroom", room=room))


@app.route('/<room>', methods=['GET'])
def chatroom(room):
    return render_template('room.html', room=room)


@app.route('/messages/<room>', methods=['GET'])
def messages(room):
    return jsonify(MessageHandler.get_messages(room))


@app.route('/send_message/<room>', methods=['POST'])
def send_message(room):
    MessageHandler.say(request.form['message'],
                       request.form['username'],
                       room)
    return redirect(url_for("chatroom", room=room))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", help="Chatroom port number",
                        default=8985)
    parser.add_argument("--host", help="Chatroom host",
                        default="0.0.0.0")
    parser.add_argument('--log-level', type=str, default="DEBUG",
                        help="Set the logging level (e.g., DEBUG, INFO, ERROR).")
    parser.add_argument('--log-path', type=str, default=None, help="Set the directory path for logs.")
    args = parser.parse_args()

    # Set log level
    init_service_logger("flask-chat")
    LOG.set_level(args.log_level)

    # Set log path if provided, otherwise use default
    if args.log_path:
        LOG.base_path = args.log_path
    else:
        LOG.base_path = os.path.join(xdg_state_home(), "hivemind")

    if LOG.base_path == "stdout":
        LOG.info("logs printed to stdout (not saved to file)")
    else:
        LOG.info(f"log files can be found at: {LOG.base_path}/flask-chat.log")

    MessageHandler.connect()
    app.run(args.host, args.port, debug=True)


if __name__ == "__main__":
    main()
