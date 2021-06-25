import threading

import pexpect
import logging

from nameko.extensions import DependencyProvider
from yowsup.config.manager import ConfigManager
from yowsup.layers.network import YowNetworkLayer
from yowsup.layers.protocol_media import YowMediaProtocolLayer
from yowsup.layers import YowLayerEvent
from yowsup.profile.profile import YowProfile
from yowsup.stacks import YowStackBuilder

# from axolotl.duplicatemessagexception import DuplicateMessageException

from src.layer import SendReciveLayer
from yowsup.layers.axolotl.props import PROP_IDENTITY_AUTOTRUST

from src.callback import CallbackSender


class YowsupExtension(DependencyProvider):
    def setup(self):
        number = str(self.container.config['YOWSUP_USERNAME'])
        cfg = self.container.config['YOWSUP_CONFIG']

        self.output('Starting YowsUP...' + number + '.')

        loginReSendMessage = self.container.config['LOGIN_RESEND_MESSAGES']
        passwordReSendMessage = self.container.config['PASSWORD_RESEND_MESSAGES']
        urlReSendMessage = self.container.config['URL_RESEND_MESSAGES']
        logfile_path = self.container.config['LOG_FILE_PATH']
        msg_endpoint = self.container.config['ENDPOINT_RESEND_MESSAGES']
        jwt_endpoint = self.container.config['ENDPOINT_RESEND_JWT']

        cs = CallbackSender(
            url=urlReSendMessage,
            login=loginReSendMessage,
            pwd=passwordReSendMessage,
            logfile_path=logfile_path,
            msg_endpoint=msg_endpoint,
            jwt_endpoint=jwt_endpoint
        )

        stackBuilder = YowStackBuilder()
        self.stack = stackBuilder \
            .pushDefaultLayers() \
            .push(SendReciveLayer(cs, number)) \
            .build()

        config_manager = ConfigManager()
        config = config_manager.load_data(cfg)
        profile = YowProfile(profile_name=number, config=config)
        self.stack.setProfile(profile)

        self.stack.setProp(PROP_IDENTITY_AUTOTRUST, True)

        connectEvent = YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT)
        self.stack.broadcastEvent(connectEvent)

        def startThread():
            try:
                self.stack.loop(timeout=0.5, discrete=0.5)
            except ValueError as e:
                self.output(e)
            except KeyboardInterrupt:
                self.output("\nYowsdown KeyboardInterrupt")
                exit(0)
            except Exception as e:
                self.output(e)
                self.output("Whatsapp exited")
                exit(0)

        t1 = threading.Thread(target=startThread)
        t1.daemon = True
        t1.start()

    def sendTextMessage(self, address,message):
        self.output('Trying to send Message to %s:%s' % (address, message))
      
        self.stack.broadcastEvent(YowLayerEvent(name=SendReciveLayer.EVENT_SEND_MESSAGE, msg=message, number=address))
        return True

    def get_dependency(self, worker_ctx):
        return self

    def output(self, str):
        logging.info(str)
        pass
