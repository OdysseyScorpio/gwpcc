import json

from lib.gwpcc.qevent.basemessage import BaseMessage
from lib.gwpcc.qevent.messages.order import OrderMessage
from lib.gwpcc.qevent.messages.sale import SaleMessage


def send(message: BaseMessage, connection):
    connection.publish('market', json.dumps(message.to_dict()))


def receive(message):
    try:
        payload = json.loads(message)
        msg = BaseMessage(payload['market'], payload['action'], payload['data'])
        if msg.action == 'order':
            msg = OrderMessage.parse(msg)
        if msg.action == 'sale':
            msg = SaleMessage.parse(msg)

        return msg

    except Exception as e:
        print('Unable to parse message, ignoring')
