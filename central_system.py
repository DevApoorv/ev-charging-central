import asyncio
import logging
from pymongo import MongoClient
from datetime import datetime

try:
    import websockets
except ModuleNotFoundError:
    print("This example relies on the 'websockets' package.")
    print("Please install it by running: ")
    print()
    print(" $ pip install websockets")
    import sys
    sys.exit(1)

from ocpp.routing import on
from ocpp.v16 import ChargePoint as cp
from ocpp.v16 import call_result
from ocpp.v16.enums import Action, RegistrationStatus

logging.basicConfig(level=logging.INFO)

client = MongoClient('localhost', 27017)
mydatabase = client['ocppdb'] 

class MyChargePoint(cp):

    @on(Action.Authorize)
    def authorize(self, id_tag):
        record_count = 0
        result = mydatabase.vehicle.find({"idTag": id_tag})
        result_iter = {}
        response = {"title": "AuthorizeResponse", "type": "object"}
        for x in result:
            record_count += 1
            result_iter = x
        if(record_count != 0):
            response["properties"] = {}
            response["properties"]["idTagInfo"] = {"status": result_iter["status"], "expiryDate": result_iter["expiryDate"], "parentIdTag": result_iter["parentIdTag"]}
        else:
            response["properties"] = {}
            response["properties"]["idTagInfo"] = {"status": "Invalid"}
        
        return response
    # [2,
    #          "19223201",
    #          "BootNotification",
    #          {
    #              "chargePointVendor":"Power Grid",
    #              "chargePointModel":"Model-1 Optimus"

    #          }
    #         ]

    @on(Action.BootNotification)
    def on_boot_notitication(self, charge_point_vendor, charge_point_model,**kwargs):
        return call_result.BootNotificationPayload(
            current_time=datetime.utcnow().isoformat(),
            interval=10,
            status=RegistrationStatus.accepted
        )

    # [2,
    #          "19223202",
    #          "Heartbeat",
    #          {}
    #         ]

    @on(Action.Heartbeat)
    def on_heartbeat(self):
        print('Got a Heartbeat!')
        return call_result.HeartbeatPayload(
            current_time=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S') + "Z"
        )

    # Method used by charge point 
    @on(Action.MeterValues)
    def meter_values(self, connector_id, meter_value, transaction_id):
        return call_result.MeterValuesPayload(
            connectorId=connector_id,
            meterValue=meter_value,
            transactionId=transaction_id
        )

    # Change availability of connector type- Operative, Inoperative
    @on(Action.ChangeAvailability)
    def on_change_availability(self, connector_id, type):
        return call_result.ChangeAvailabilityPayload(
            status=RegistrationStatus.accepted
        )

    #     [
    # 2,
    # "26",
    # "StartTransaction",
    # {
    # "connectorId": 1,
    # "idTag": "dummyToken",
    # "meterStart": 0,
    # "timestamp": "2017-03-08T14:22:27Z"
    # }
    # ]

    @on(Action.StartTransaction)
    def on_start_transaction(self, connector_id, id_tag, meter_start,timestamp):
        obj={"status": "Accepted"}
        return call_result.StartTransactionPayload(
            transaction_id=1111,
            id_tag_info=obj
        )

        #     [
        # 2,
        # "138ffd31-9245-4c63-9185-4036067dffb9",
        # "RemoteStartTransaction",
        # {
        # "connectorId": 1,
        # "idTag": "dummyToken",
        # "chargingProfile": {
        # "chargingProfileId": 2,
        # "transactionId": 123,
        # "stackLevel": 1,
        # "chargingProfilePurpose": "TxProfile",
        # "chargingProfileKind": "Relative",
        # "chargingSchedule": {
        # "duration": 5,
        # "chargingRateUnit": "W",
        # "chargingSchedulePeriod": [
        # {
        # "startPeriod": 0,
        # "limit": 1000,
        # "numberPhases": 3
        # }
        # ]
        # }
        # }
        # }
        # ]
    @on('RemoteStartTransaction')
    def remote_start_transaction(self, connector_id,id_tag, charging_profile):
        return call_result.RemoteStartTransactionPayload(
            status=RegistrationStatus.accepted
        )

    # [
    # 2,
    # "0a8a0fab-7775-4f72-9f4b-ed5bd5a4bed2",
    # "RemoteStopTransaction",
    # {
    # "transactionId": 123
    # }
    # ]
    @on('RemoteStopTransaction')
    def remote_stop_transaction(self, transaction_id):
        return call_result.RemoteStopTransactionPayload(
            status=RegistrationStatus.accepted
        )


async def on_connect(websocket, path):
    """ For every new charge point that connects, create a ChargePoint instance
    and start listening for messages.

    """
    charge_point_id = path.strip('/')
    cp = MyChargePoint(charge_point_id, websocket)

    await cp.start()

async def main():
   server = await websockets.serve(
      on_connect,
      'localhost',
      9000,
      subprotocols=['ocpp2.0.1']
   )

   await server.wait_closed()


if __name__ == '__main__':
   asyncio.run(main())
