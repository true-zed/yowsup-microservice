import base64
import encodings

from yowsup.layers.interface import YowInterfaceLayer, ProtocolEntityCallback
from yowsup.layers.auth import YowAuthenticationProtocolLayer
from yowsup.layers import YowLayerEvent, EventCallback
from yowsup.layers.network import YowNetworkLayer
import sys
from yowsup.common import YowConstants
import datetime
import os
import logging
from yowsup.layers.protocol_groups.protocolentities import *
from yowsup.layers.protocol_presence.protocolentities import *
from yowsup.layers.protocol_messages.protocolentities import *
from yowsup.layers.protocol_ib.protocolentities import *
from yowsup.layers.protocol_iq.protocolentities import *
from yowsup.layers.protocol_contacts.protocolentities import *
from yowsup.layers.protocol_chatstate.protocolentities import *
from yowsup.layers.protocol_privacy.protocolentities import *
from yowsup.layers.protocol_media.protocolentities import *
from yowsup.layers.protocol_media.mediauploader import MediaUploader
from yowsup.layers.protocol_profiles.protocolentities import *
from yowsup.common.tools import Jid
from yowsup.common.optionalmodules import PILOptionalModule
import urllib.request

logger = logging.getLogger(__name__)


class SendReciveLayer(YowInterfaceLayer):

    DISCONNECT_ACTION_PROMPT = 0

    EVENT_SEND_MESSAGE = "org.openwhatsapp.yowsup.prop.queue.sendmessage"
    
    def __init__(self, cs, myNumber):
        super(SendReciveLayer, self).__init__()
        YowInterfaceLayer.__init__(self)
        self.accountDelWarnings = 0
        self.connected = True
        self.username = None
        self.sendReceipts = True
        self.sendRead = True
        self.disconnectAction = self.__class__.DISCONNECT_ACTION_PROMPT
        self.myNumber = myNumber
        self.credentials = None
        
        self.cs = cs

        # add aliases to make it user to use commands. for example you can then do:
        # /message send foobar "HI"
        # and then it will get automaticlaly mapped to foobar's jid
        self.jidAliases = {
            # "NAME": "PHONE@s.whatsapp.net"
        }

    def aliasToJid(self, calias):
        for alias, ajid in self.jidAliases.items():
            if calias.lower() == alias.lower():
                return Jid.normalize(ajid)

        return Jid.normalize(calias)

    def jidToAlias(self, jid):
        for alias, ajid in self.jidAliases.items():
            if ajid == jid:
                return alias
        return jid

    def setCredentials(self, username, password):
        self.getLayerInterface(YowAuthenticationProtocolLayer).setCredentials(username, password)

        return "%s@s.whatsapp.net" % username

    @EventCallback(YowNetworkLayer.EVENT_STATE_DISCONNECTED)
    def onStateDisconnected(self, layerEvent):
        self.output("Disconnected: %s" % layerEvent.getArg("reason"))
        if self.disconnectAction == self.__class__.DISCONNECT_ACTION_PROMPT:
            self.connected = False
            # self.notifyInputThread()
        else:
            os._exit(os.EX_OK)

    def assertConnected(self):
        if self.connected:
            return True
        else:
            self.output("Not connected", tag="Error", prompt=False)
            return False


    @ProtocolEntityCallback("chatstate")
    def onChatstate(self, entity):
        print(entity)

    @ProtocolEntityCallback("iq")
    def onIq(self, entity):
        print(entity)

    @ProtocolEntityCallback("receipt")
    def onReceipt(self, entity):
        self.toLower(entity.ack())

    @ProtocolEntityCallback("ack")
    def onAck(self, entity):
        # formattedDate = datetime.datetime.fromtimestamp(self.sentCache[entity.getId()][0]).strftime('%d-%m-%Y %H:%M')
        # print("%s [%s]:%s"%(self.username, formattedDate, self.sentCache[entity.getId()][1]))
        if entity.getClass() == "message":
            self.output(entity.getId(), tag="Sent")
            # self.notifyInputThread()

    @ProtocolEntityCallback("success")
    def onSuccess(self, entity):
        self.connected = True
        self.output("Logged in!", "Auth", prompt=False)
        # self.notifyInputThread()

    @ProtocolEntityCallback("failure")
    def onFailure(self, entity):
        self.connected = False
        self.output("Login Failed, reason: %s" % entity.getReason(), prompt=False)

    @ProtocolEntityCallback("notification")
    def onNotification(self, notification):
        notificationData = notification.__str__()
        if notificationData:
            self.output(notificationData, tag="Notification")
        else:
            self.output("From :%s, Type: %s" % (self.jidToAlias(notification.getFrom()), notification.getType()),
                        tag="Notification")
        if self.sendReceipts:
            try:
                self.toLower(notification.ack())
            except Exception as e:
                self.output(e)

    @ProtocolEntityCallback("message")
    def onMessage(self, message):

        message_out = {'source': 'gm' if message.isGroupMessage() else 'pm',
                       'msg_id': str(message.getId()),
                       'msg_time': str(message.getTimestamp())}

        if message_out['source'] == 'pm':
            message_out['sender'] = str(message.getFrom(full=False))
            message_out['chat'] = str(self.myNumber)
        else:
            message_out['sender'] = str(message.getParticipant(full=False))
            message_out['chat'] = str(message.getFrom(full=False))

        if message.message_attributes.extended_text:
            message_out['replied_msg_id'] = \
                str(message.message_attributes.extended_text.context_info.stanza_id)

        if message.getType() == 'text':
            if message.message_attributes.extended_text:
                message_out['content'] = str(message.message_attributes.extended_text.text)
            else:
                message_out['content'] = str(message.conversation)

        if message.getType() == 'media':
            # TODO: Try this
            #  getattr()
            message_out['msg_media'] = {
                'url': str(message.url),
                'ref_key': base64.b64encode(message.media_key),
                'media_type': str(message.media_type)
            }

            if message.media_type == 'image':
                message_out['content'] = str(message.caption)
                message_out['msg_media']['mimetype'] = message.message_attributes.image.downloadablemedia_attributes.mimetype
            if message.media_type == 'ptt':
                message_out['msg_media']['mimetype'] = message.message_attributes.audio.downloadablemedia_attributes.mimetype
            if message.media_type == 'audio':
                message_out['msg_media']['mimetype'] = message.message_attributes.audio.downloadablemedia_attributes.mimetype
            if message.media_type == 'document':
                message_out['msg_media']['filename'] = message.message_attributes.document.file_name

        print('=================Start=================')
        print(message_out)
        print('==================End==================')

        print(self.cs.send_msg(**message_out))

        if self.sendReceipts:
            self.toLower(message.ack(self.sendRead))
            self.output("Sent delivered receipt" + " and Read" if self.sendRead else "",
                        tag="Message %s" % message.getId())

    @EventCallback(EVENT_SEND_MESSAGE)
    def doSendMesage(self, layerEvent):
        content = layerEvent.getArg("msg")
        number = layerEvent.getArg("number")
        self.output("Send Message to %s : %s" % (number, content))
        jid = number

        if self.assertConnected():
            outgoingMessage = TextMessageProtocolEntity(
                content.encode("utf-8") if sys.version_info >= (3, 0) else content, to=self.aliasToJid(number))
            self.toLower(outgoingMessage)
    # TODO: Return message ID from here

    def getTextMessageBody(self, message):
        if isinstance(message, TextMessageProtocolEntity):
            return message.conversation
        elif isinstance(message, ExtendedTextMessageProtocolEntity):
            return str(message.message_attributes.extended_text)
        else:
            raise NotImplementedError()

    def getMediaMessageBody(self, message):
        # type: (DownloadableMediaMessageProtocolEntity) -> str
        return str(message.message_attributes)

    def getDownloadableMediaMessageBody(self, message):
        return "[media_type={media_type}, length={media_size}, url={media_url}, key={media_key}]".format(
            media_type=message.media_type,
            media_size=message.file_length,
            media_url=message.url,
            media_key=base64.b64encode(message.media_key)
        )

    ########### callbacks ############

    def __str__(self):
        return "Send Recive Interface Layer"

    def output(self, str, tag="", prompt=""):
        logging.info(str)
        pass
