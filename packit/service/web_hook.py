# MIT License
#
# Copyright (c) 2018-2019 Red Hat, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import logging
from io import StringIO

from flask import Flask, request, jsonify

from packit.config import Config
from packit.jobs import SteveJobs
from packit.utils import set_logging


class PackitWebhookReceiver(Flask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        set_logging(level=logging.DEBUG)


app = PackitWebhookReceiver(__name__)
logger = logging.getLogger("packit")


@app.route("/healthz", methods=["GET", "HEAD", "POST"])
def get_health():
    # TODO: add some interesting stats here
    return jsonify({"msg": "We are healthy!"})


@app.route("/webhooks/github/release", methods=["POST"])
def github_release():
    msg = request.get_json()

    if not msg:
        logger.debug("/webhooks/github/release: We haven't received any JSON data.")
        return "We haven't received any JSON data."

    if not (msg.get("action") == "published" and "release" in msg):
        logger.debug("/webhooks/github/release: Not a new release event.")
        logger.debug(f"Action={msg['action']}, keys={msg.keys()}")
        return "We only accept events for new Github releases."

    announce_msg = (
        f"Received release event: "
        f"{msg['repository']['owner']['login']}/{msg['repository']['name']}"
        f" - {msg['release']['tag_name']}"
    )
    return process_event(announce_msg, msg)


@app.route("/webhooks/github/pull_request")
def github_pr():
    msg = request.get_json()

    if not msg:
        logger.debug(
            "/webhooks/github/pull_request: We haven't received any JSON data."
        )
        return "We haven't received any JSON data."

    allowed_actions = ["opened", "edited", "reopened"]
    if not (msg.get("action") in allowed_actions):
        logger.debug(
            f"/webhooks/github/pull_request: Ignoring pull_request event - {msg['action']}"
        )
        return "We only accept events for opened or edited pull_requests."

    announce_msg = (
        f"Received pull_request event: "
    )
    return process_event(announce_msg, msg)


def process_event(event, event_announce):
    buffer = StringIO()
    logHandler = logging.StreamHandler(buffer)
    logHandler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logHandler.setFormatter(formatter)
    logger.addHandler(logHandler)

    logger.debug(event_announce)
    config = Config.get_user_config()

    steve = SteveJobs(config)
    steve.process_message(event)

    logger.removeHandler(logHandler)
    buffer.flush()

    return buffer.getvalue()
