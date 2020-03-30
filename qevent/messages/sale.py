from typing import Dict, List, Any

from lib.gwpcc.qevent.basemessage import BaseMessage


class SaleMessage(BaseMessage):

    def __init__(self, market, sale_data):
        self.sale_data = sale_data
        super().__init__(market, 'sale', {
            'sale_data': self.sale_data,
        })

    @staticmethod
    def prepare(market, sale_items: List[Dict[str, Any]]):

        # Start building data to send to Message Queue
        sale_data = {'sale_items': []}

        for thing_dict in sale_items:
            sale_data['sale_items'].append((thing_dict['thing'].FullName, thing_dict['discount']))

        return SaleMessage(market, sale_data)

    @staticmethod
    def parse(message: BaseMessage):
        if message.action != 'sale':
            raise Exception('Wrong action type')

        sale_data = message.data['sale_data']

        return SaleMessage(message.market, sale_data)

    def __str__(self):
        lines = ['A sale has just begun on {0}!\n\n'.format(self.market)]

        for name, qty in self.sale_data['sale_items']:
            lines.append('* {0} reduced by {1}%\n'.format(name, qty))

        return ''.join(lines)
