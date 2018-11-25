"""
Module for PyVLX object.

PyVLX is an asynchronous library for connecting to
a VELUX KLF 200 device for controlling window openers
and roller shutters.
"""
import asyncio
from .config import Config
from .connection import Connection
from .login import Login
from .get_version import GetVersion
from .get_protocol_version import GetProtocolVersion
from .exception import PyVLXException
from .nodes import Nodes
from .scenes import Scenes
from .log import PYVLXLOG
from .heartbeat import Heartbeat


class PyVLX:
    """Class for PyVLX."""

    def __init__(self, path=None, host=None, password=None, log_frames=False, loop=None):
        """Initialize PyVLX class."""
        self.loop = loop or asyncio.get_event_loop()
        self.config = Config(self, path, host, password)
        self.connection = Connection(loop=self.loop, config=self.config)
        self.heartbeat = Heartbeat(pyvlx=self)
        self.heartbeat.start()
        if log_frames:
            self.connection.register_frame_received_cb(self.log_frame)
        self.nodes = Nodes(self)
        self.scenes = Scenes(self)
        self.version = None
        self.protocol_version = None

    async def connect(self):
        """Connect to KLF 200."""
        PYVLXLOG.warning("Connecting to API.")
        await self.connection.connect()
        login = Login(pyvlx=self, password=self.config.password)
        await login.do_api_call()
        if not login.success:
            raise PyVLXException("Unable to login")

    async def update_version(self):
        """Retrieve version and protocol version from API."""
        get_version = GetVersion(pyvlx=self)
        await get_version.do_api_call()
        if not get_version.success:
            raise PyVLXException("Unable to retrieve version")
        self.version = get_version.version
        get_protocol_version = GetProtocolVersion(pyvlx=self)
        await get_protocol_version.do_api_call()
        if not get_protocol_version.success:
            raise PyVLXException("Unable to retrieve protocol version")
        self.protocol_version = get_protocol_version.version
        PYVLXLOG.warning(
            "Connected to: %s, protocol version: %s",
            self.version, self.protocol_version)

    async def send_frame(self, frame):
        """Send frame to API via connection."""
        if not self.connection.connected:
            await self.connect()
            await self.update_version()
        self.connection.write(frame)

    async def disconnect(self):
        """Disconnect from KLF 200."""
        await self.heartbeat.stop()
        self.connection.disconnect()

    async def load_nodes(self, node_id=None):
        """Load devices from KLF 200, if no node_id is specified all nodes are loaded."""
        await self.nodes.load(node_id)

    async def load_scenes(self):
        """Load scenes from KLF 200."""
        await self.scenes.load()

    async def log_frame(self, frame):
        """Log frame to logger."""
        PYVLXLOG.warning("%s", frame)
