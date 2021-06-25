"""
Copyright and other info
"""
import base64
import logging
import string
import binascii

from os import path
from random import choice
from requests import post
from Crypto.Cipher import AES
from datetime import datetime
from urllib.request import urlopen
from axolotl.kdf.hkdfv3 import HKDFv3
from axolotl.util.byteutil import ByteUtil
from requests.exceptions import ConnectionError


class CallbackSender:
    """
    Used to send messages to backend.

    """

    def __init__(self, url, login, pwd, msg_endpoint='messages/', jwt_endpoint='token/', logfile_path=None):
        self._logger = self.configure_logger(path_to_log_file=logfile_path)

        self.__url = url
        self.__msg_endpoint = path.join(url, msg_endpoint)
        self.__jwt_endpoint = path.join(url, jwt_endpoint)

        self._login_data = {'username': login, 'password': pwd}

        self._jwt = None
        self._jwt_refresh = None

        self._get_jwt()

    @staticmethod
    def configure_logger(path_to_log_file=None):
        """
        Used to configure logger settings.

        :param path_to_log_file: logger will store logs in a file along this path if specified

        :return: logger obj from logging lib
        """
        import logging

        formatter = logging.Formatter("%(asctime)s - [%(levelname)s] -  %(name)s - (%(filename)s).%(funcName)s(%("
                                      "lineno)d) - %(message)s")

        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)

        # Configure console output for debug
        syslog = logging.StreamHandler()
        syslog.setFormatter(formatter)
        syslog.setLevel(logging.DEBUG)
        logger.addHandler(syslog)

        # Configure output to file
        if path_to_log_file:
            file_log = logging.FileHandler(filename=path_to_log_file, encoding='utf-8')
            file_log.setFormatter(formatter)
            file_log.setLevel(logging.DEBUG)
            logger.addHandler(file_log)

        logger.debug("I'm alive!")
        return logger

    def send_msg(self, **kwargs):
        """

        :param kwargs:
        :return:
        """

        url = self.__msg_endpoint
        files = self._prepare_files(kwargs.get('msg_media'))
        data = self.__prepare_data(**kwargs)
        headers = self._get_headers(app_json=False)

        try:

            response = post(url, headers=headers, data=data, files=files)
            msg = response.json()

            if response.status_code == 201:
                self._logger.info(msg)

            elif response.status_code == 401:
                # TODO: Remove log of this error
                #  Maybe add recursion counter
                self._logger.error(msg)
                self._refresh_jwt()
                self.send_msg(**kwargs)
                return

            else:
                self._logger.critical(msg)

        except ConnectionError as e:
            msg = 'Something went wrong..'
            self._logger.exception(e)

        return msg

    @property
    def msg_template(self):
        """
        Used to get a template for formatting.

        :return: Dictionary with values to formatting
        """
        tmp = {
            "chat": "{chat}",
            "msgType": "inMsg",
            "msg_id": "{msg_id}",
            "source": "{source}",
            "sender": "{sender}",
            "content": "{content}",
            "msg_time": "{msg_time}",
            "replied_msg_id": "{replied_msg_id}",
        }
        return tmp

    def _refresh_jwt(self):
        url = self.__jwt_endpoint
        data = {'refresh': self._jwt_refresh}

        try:

            response = post(url, headers=self._get_headers(), json=data)
            tokens = response.json()

            if response.status_code == 401:
                self._logger.warning(response.json())
                self._get_jwt()
                return

        except ConnectionError as e:
            self._logger.exception(e)
            tokens = {}

        self._jwt = tokens.get('access', None)
        self._jwt_refresh = tokens.get('refresh', None)

        return tokens

    def _get_jwt(self):
        """
        Func
        :return:
        """
        url = '{jwt_endpoint}'.format(jwt_endpoint=self.__jwt_endpoint)
        data = self._login_data

        try:
            tokens = post(url, headers=self._get_headers(auth=False), json=data).json()
            # TODO: Logger answer from server add
            self._logger.debug(tokens)
        except ConnectionError as e:
            # TODO: Logger log here
            self._logger.exception(e)
            tokens = {}

        self._jwt = tokens.get('access', None)
        self._jwt_refresh = tokens.get('refresh', None)

        return tokens

    def _get_headers(self, auth=True, app_json=True):
        """
        Used to get a headers for request.

        :param auth: Add JWT to your request.
        :param app_json: Add {'Content-type': 'application/json; charset=utf-8'}

        :return: Returns headers for a request <br> with or without JWT and Content-Type.
        """
        headers = {}
        if auth:
            if self._jwt and self._jwt_refresh:
                headers['Authorization'] = 'JWT {jwt}'.format(jwt=self._jwt)
            else:
                self._logger.error('Trying to get JWT without authorization!')
                raise AttributeError('To get the JWT, first log in!')

        if app_json:
            headers['Content-Type'] = 'application/json; charset=utf-8'

        return headers

    def getCryptKeys(self, media_type):
        if media_type == "image":
            return '576861747341707020496d616765204b657973'
        elif media_type == "audio" or media_type == "ptt":
            return '576861747341707020417564696f204b657973'
        elif media_type == "video":
            return '576861747341707020566964656f204b657973'
        elif media_type == "document":
            return '576861747341707020446f63756d656e74204b657973'
        else:
            return None

    def __get_and_decrypt_media(self, url, ref_key, media_type):
        """
        Uses to retrieve binary media data from WhatsApp and decrypt it.

        :param url: media download URL
        :param ref_key: binary key to decrypt (from WhatsApp)
        :param media_type: type of decrypted media. Example: image, audio, video, document

        :return: decrypted binary media
        """
        ref_key = base64.b64decode(ref_key)

        keys = self.getCryptKeys(media_type)
        self._logger.debug(keys)
        derivative = HKDFv3().deriveSecrets(ref_key, binascii.unhexlify(keys), 112)
        parts = ByteUtil.split(derivative, 16, 32)
        iv, cipher_key, *other = parts

        AES.key_size = 128
        cr_obj = AES.new(key=cipher_key, mode=AES.MODE_CBC, IV=iv)

        e_img = urlopen(url).read()[:-10]

        return cr_obj.decrypt(e_img)

    @staticmethod
    def generate_id(size=6, chars=string.ascii_letters + string.digits):
        """
        Uses to generate string with random letters and digits

        :param size: desired length of the generated string
        :param chars: characters to be used to generate the string

        :return: random string
        """
        return ''.join(choice(chars) for _ in range(size))

    def generate_filename(self, mimetype):
        """
        Used to generate a string for the filename.

        :param mimetype: Info about media. Example: "image/jpeg"

        :return: filename string in the format: <br> '{media_type}_{random}.{endswith}'
        """
        if not mimetype:
            return
        media_type, endswith = mimetype.split('/')
        endswith = endswith.split(';')[0]
        filename = '{media_type}_{random}.{endswith}'.format(
            media_type=media_type,
            endswith=endswith,
            random=CallbackSender.generate_id(size=8)
        )
        self._logger.debug('Generated file name: {filename}'.format(filename=filename))
        return filename

    def __prepare_data(self, **kwargs):
        """
        Used to prepare data from WhatsApp message for POST request.

        :keyword chat: group id or contact id
        :keyword msg_id: received message id
        :keyword source: privat or group message (pm, gm)
        :keyword sender: id of message owner
        :keyword content: message content
        :keyword msg_time: timestamp of received message
        :keyword msg_media: media from message in dictionary
        :keyword replied_msg_id: id of replied message if this message is reply

        :return: Prepared data for sending a request
        """

        self._logger.debug(kwargs)

        kwargs['msg_time'] = datetime.fromtimestamp(float(kwargs.get('msg_time'))) \
            if kwargs.get('msg_time', False) else None

        data = {
            key: value.format(**kwargs)
            for key, value in self.msg_template.items()
            if key in kwargs.keys() or value.isalpha()
        }

        return {key: value for key, value in data.items() if value is not None}

    def _prepare_files(self, upp_media):
        """
        Used to decrypt WhatsApp media and return dictionary for files field of requests library. \n
        Media types supported - image, audio, document

        :param upp_media: {'url': str, 'ref_key': str, 'media_type': str, 'mimetype': str, 'filename': str},
        filename field required for document

        :return: {'msg_media': (filename, file)}
        """

        self._logger.debug(upp_media)

        if upp_media:
            file = self.__get_and_decrypt_media(upp_media.get('url'), upp_media.get('ref_key'),
                                                upp_media.get('media_type'))
            filename = self.generate_document_filename(upp_media.get('filename')) or \
                self.generate_filename(upp_media.get('mimetype'))
            return {'msg_media': (filename, file)}

        return None

    def generate_document_filename(self, filename):
        """

        :param filename:
        :return:
        """
        if not filename:
            return
        filename = '{file_id}_{filename}'.format(file_id=self.generate_id(8), filename=filename)
        self._logger.debug('Generated document name: {filename}'.format(filename=filename))
        return filename
