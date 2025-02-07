"""Client for the National Rail API"""

import logging

import datetime
from datetime import datetime, timedelta

import json

import httpx
from zeep import AsyncClient, Settings, xsd
from zeep.exceptions import Fault
from zeep.plugins import HistoryPlugin
from zeep.transports import AsyncTransport

from homeassistant.core import HomeAssistant

from .const import WSDL

_LOGGER = logging.getLogger(__name__)


class NationalRailClientException(Exception):
    """Base exception class."""


class NationalRailClientInvalidToken(NationalRailClientException):
    """Token is Invalid"""


class NationalRailClientInvalidInput(NationalRailClientException):
    """Token is Invalid"""


def rebuild_date(base, time):
    """Rebuild a date time object from the simplified representation returned by the api"""
    time = time.split(":")
    hour = int(time[0])
    minute = int(time[1])

    date_object = datetime(
        base.year, base.month, base.day, hour, minute, tzinfo=base.tzinfo
    )

    if (date_object - datetime.now(tz=base.tzinfo)).total_seconds() < -4 * 60 * 60:
        new_base = base + timedelta(days=1)
        date_object = datetime(
            new_base.year,
            new_base.month,
            new_base.day,
            hour,
            minute,
            tzinfo=new_base.tzinfo,
        )
    return date_object


class NationalRailClient:
    """Client for the National Rail API"""

    # def __init__(self, api_token, station, destinations, apiTest=False) -> None:
    def __init__(self, hass: HomeAssistant) -> None:
        # self.station = station
        # self.api_token = api_token
        # self.destinations = destinations if destinations is not None else []

        # self.ftarr = ["from", "to"]

        self.keys = [
            {
                "keyName": "from",
                "displayName": "Arrival",
                "sheduledTag": "sta",
                "estimatedTag": "eta",
            },
            {
                "keyName": "to",
                "displayName": "Departure",
                "sheduledTag": "std",
                "estimatedTag": "etd",
            },
        ]

        settings = Settings(strict=False)

        self.history = HistoryPlugin()

        wsdl_client = httpx.Client(
            verify=True,
            timeout=300,
        )
        httpx_client = httpx.AsyncClient(verify=True, timeout=300)
        transport = AsyncTransport(client=httpx_client, wsdl_client=wsdl_client)
        self.client = AsyncClient(
            wsdl=WSDL, transport=transport, settings=settings, plugins=[self.history]
        )

        self.header_value: xsd.Element

        # self.apitest = apiTest

        # Prepackage the authorisation token
        # header = xsd.Element(
        #     "{http://thalesgroup.com/RTTI/2013-11-28/Token/types}AccessToken",
        #     xsd.ComplexType(
        #         [
        #             xsd.Element(
        #                 "{http://thalesgroup.com/RTTI/2013-11-28/Token/types}TokenValue",
        #                 xsd.String(),
        #             ),
        #         ]
        #     ),
        # )
        # self.header_value = header(TokenValue=self.api_token)

    async def set_header(self, api_token):
        """Set the API header info"""
        # Prepackage the authorisation token
        header = xsd.Element(
            "{http://thalesgroup.com/RTTI/2013-11-28/Token/types}AccessToken",
            xsd.ComplexType(
                [
                    xsd.Element(
                        "{http://thalesgroup.com/RTTI/2013-11-28/Token/types}TokenValue",
                        xsd.String(),
                    ),
                ]
            ),
        )

        self.header_value = header(TokenValue=api_token)

    async def get_raw_arrivals_departures(self, station, destinations, apitest):
        """Get the raw arrivals and departures data from the api"""
        # if len(self.destinations) == 0:
        if len(destinations) == 0:
            res = await self.client.service.GetArrDepBoardWithDetails(
                numRows=10, crs=station, _soapheaders=[self.header_value]
            )
        else:
            res = {}

            # for each in self.destinations:
            for each in destinations:
                res[each] = {"generatedAt": "", "from": {}, "to": {}}

                for ft in self.keys:
                    batch = await self.client.service.GetArrDepBoardWithDetails(
                        numRows=10,
                        crs=station,
                        filterCrs=each,
                        filterType=ft["keyName"],
                        _soapheaders=[self.header_value],
                    )

                    # with open(
                    #     f"{self.station}_{ft["keyName"]}_{each}.txt", "w"
                    # ) as res_file:
                    #     res_file.write(str(batch))

                    if not apitest:
                        try:
                            # Build header info
                            if not res[each]["generatedAt"]:
                                res[each]["generatedAt"] = batch["generatedAt"]
                                res[each]["locationName"] = batch["locationName"]
                                res[each]["crs"] = batch["crs"]
                                res[each]["filterLocationName"] = batch[
                                    "filterLocationName"
                                ]
                                res[each]["filtercrs"] = batch["filtercrs"]

                                if (
                                    batch["nrccMessages"]
                                    and batch["nrccMessages"]["message"]
                                ):
                                    res[each]["messages"] = []
                                    for message in batch["nrccMessages"]["message"]:
                                        res[each]["messages"].append(
                                            message["_value_1"]
                                        )
                                else:
                                    res[each]["messages"] = ""

                            # print(batch)
                            if batch["trainServices"]:
                                if not res[each][ft["keyName"]]:
                                    res[each][ft["keyName"]] = batch["trainServices"][
                                        "service"
                                    ]
                                else:
                                    res[each][ft["keyName"]].append(
                                        batch["trainServices"]["service"]
                                    )
                        except (KeyError, TypeError, NameError) as err:
                            raise NationalRailClientException(
                                f"No train services returned from API for {self.station} to {each}"
                            ) from err
                        except Fault as err:
                            raise NationalRailClientException("Unknown error") from err

        # with open("output.txt", "w") as convert_file:
        #     convert_file.write(str(res))

        return res

    def timeConvert(self, time_base, sheduled, estimated, actual):
        """Common time conversion"""

        perturbation = False
        time_shed = None
        if sheduled is not None:
            time_shed = rebuild_date(time_base, sheduled)

        time_est = None
        if estimated is not None:
            if estimated == "On time":
                time_est = time_shed
            elif estimated in ("Delayed", "Cancelled"):
                time_est = estimated
                perturbation = True
            elif estimated == "No report":
                time_est = rebuild_date(time_base, "00:00")
            else:
                time_est = rebuild_date(time_base, estimated)
                delay = (time_est - time_shed).total_seconds() / 60
                if delay > 9:
                    perturbation = True

        time_act = None
        if actual is not None:
            if actual == "On time":
                time_act = time_shed
            elif actual in ("Delayed", "Cancelled"):
                time_act = actual
                perturbation = True
            elif actual == "No report":
                time_est = rebuild_date(time_base, "00:00")
            else:
                time_act = rebuild_date(time_base, actual)
                delay = (time_act - time_shed).total_seconds() / 60
                if delay > 9:
                    perturbation = True

        return {
            "sheduled": time_shed,
            "estimated": time_est,
            "actual": time_act,
            "perturbation": perturbation,
        }

    def process_data(self, station, destinations, json_message_in):
        """Unpack the data return by the api in a usable format for hass"""

        # _LOGGER.debug("Data for processing: %s", json_message)

        res = {}
        res["dests"] = {}

        # for each in self.destinations:
        for each in destinations:
            res["dests"][each] = {}

            res["station"] = json_message_in[each]["locationName"]
            time_base = json_message_in[each]["generatedAt"]
            res["dests"][each]["messages"] = json_message_in[each]["messages"]

            for ft in self.keys:
                services_list = json_message_in[each][ft["keyName"]]

                status = {}
                status["trains"] = []

                if not services_list:
                    res["dests"][each][ft["displayName"]] = {}
                    continue

                for service in services_list:
                    train = {}
                    # perturbation = False

                    times = self.timeConvert(
                        time_base,
                        service[ft["sheduledTag"]],
                        service[ft["estimatedTag"]],
                        None,
                    )

                    if times["sheduled"] is None and times["estimated"] is None:
                        times["estimated"] = rebuild_date(time_base, "23:59")

                    # time = rebuild_date(time_base, service[ft["sheduledTag"]])

                    # if service[ft["estimatedTag"]] == "On time":
                    #     expected = time
                    # elif (
                    #     service[ft["estimatedTag"]] == "Delayed"
                    #     or service[ft["estimatedTag"]] == "Cancelled"
                    # ):
                    #     expected = service[ft["estimatedTag"]]
                    #     perturbation = True
                    # else:
                    #     expected = rebuild_date(time_base, service[ft["estimatedTag"]])
                    #     delay = (expected - time).total_seconds() / 60
                    #     if delay > 9:
                    #         perturbation = True

                    ############################################################
                    # Create full calling point list
                    ############################################################
                    callingPoints = []
                    otherEnd = {}

                    selectedCallingPoint = [
                        {
                            "locationName": json_message_in[each]["locationName"],
                            "crs": station,
                            "st": times["sheduled"],
                            "et": times["estimated"],
                            "at": None,
                            "isCancelled": service["isCancelled"],
                            "cancelReason": service["cancelReason"],
                        }
                    ]

                    # Get previous calling points
                    if service["previousCallingPoints"] is not None:
                        for callingPoint in service["previousCallingPoints"][
                            "callingPointList"
                        ][0]["callingPoint"]:
                            cpTimes = self.timeConvert(
                                time_base,
                                callingPoint["st"],
                                callingPoint["et"],
                                callingPoint["at"],
                            )

                            if cpTimes["actual"] is not None:
                                atet = cpTimes["actual"]
                            else:
                                atet = cpTimes["estimated"]

                            point = [
                                {
                                    "locationName": callingPoint["locationName"],
                                    "crs": callingPoint["crs"],
                                    "st": cpTimes["sheduled"],
                                    "et": cpTimes["estimated"],
                                    "at": cpTimes["actual"],
                                    "atet": atet,
                                    "isCancelled": callingPoint["isCancelled"],
                                    "cancelReason": callingPoint["cancelReason"],
                                }
                            ]
                            callingPoints = callingPoints + point

                            if callingPoint["crs"] == each:
                                otherEnd = point[0]

                    # Add out calling point
                    callingPoints = callingPoints + selectedCallingPoint

                    # Get subsequent calling points
                    if service["subsequentCallingPoints"] is not None:
                        for callingPoint in service["subsequentCallingPoints"][
                            "callingPointList"
                        ][0]["callingPoint"]:
                            cpTimes = self.timeConvert(
                                time_base,
                                callingPoint["st"],
                                callingPoint["et"],
                                callingPoint["at"],
                            )

                            if cpTimes["actual"] is not None:
                                atet = cpTimes["actual"]
                            else:
                                atet = cpTimes["estimated"]

                            point = [
                                {
                                    "locationName": callingPoint["locationName"],
                                    "crs": callingPoint["crs"],
                                    "st": cpTimes["sheduled"],
                                    "et": cpTimes["estimated"],
                                    "at": cpTimes["actual"],
                                    "atet": atet,
                                    "isCancelled": callingPoint["isCancelled"],
                                    "cancelReason": callingPoint["cancelReason"],
                                }
                            ]
                            callingPoints = callingPoints + point

                            if callingPoint["crs"] == each:
                                otherEnd = point[0]

                    # with open("output.json", "w") as convert_file:
                    #     convert_file.write(str(otherEnd))

                    ############################################################
                    # Assign outputs
                    ############################################################
                    train["scheduled"] = times["sheduled"]
                    train["expected"] = times["estimated"]
                    train["origin"] = service["origin"]["location"][0]["locationName"]
                    train["destination"] = service["destination"]["location"][0][
                        "locationName"
                    ]
                    train["platform"] = service["platform"]
                    train["perturbation"] = times["perturbation"]
                    train["operator"] = service["operator"]
                    train["length"] = service["length"]
                    train["callingPoints"] = callingPoints

                    if otherEnd:
                        train["otherEnd"] = otherEnd
                        status["trains"].append(train)

                # with open("output_test.txt", "w") as convert_file:
                #     convert_file.write(str(status["trains"]))

                status["trains"] = sorted(
                    status["trains"],
                    key=lambda d: d["expected"]
                    if isinstance(d["expected"], datetime)
                    else d["scheduled"],
                )
                res["dests"][each][ft["displayName"]] = status

                for otherEnd in status["trains"]:
                    if "otherEnd" in otherEnd:
                        res["dests"][each]["displayName"] = otherEnd["otherEnd"][
                            "locationName"
                        ]
                        break

        # with open("output_" + self.station + ".txt", "w") as convert_file:
        #     convert_file.write(str(res))
        return res

    async def async_get_data(self, station, destinations, apitest=False):
        """Data refresh function called by the coordinator"""
        try:
            # _LOGGER.info("Requesting depearture data for %s", self.station)
            # raw_data = await self.get_raw_arrivals_departures()
            _LOGGER.info("Requesting depearture data for %s", station)
            raw_data = await self.get_raw_arrivals_departures(
                station, destinations, apitest
            )
        except Fault as err:
            _LOGGER.exception("Exception whilst fetching data: ")
            if err.message == "Unknown fault occured":
                # likely invalid token
                raise NationalRailClientInvalidToken("Invalid API token") from err
            if err.message == "Unexpected server error":
                # likely invalid input
                raise NationalRailClientInvalidInput("Invalid station input") from err

            raise NationalRailClientException("Unknown Error") from err

        # with open("output.txt", "w") as convert_file:
        #     convert_file.write(str(raw_data))

        if not apitest:
            # print(f"API test: {self.apitest}")
            try:
                # _LOGGER.info("Procession station schedule for %s", self.station)
                # data = self.process_data(raw_data)
                _LOGGER.info("Procession station schedule for %s", station)
                data = self.process_data(station, destinations, raw_data)
                # with open("output.json", "w") as convert_file:
                #     convert_file.write(str(data))
            except Exception as err:
                _LOGGER.exception("Exception whilst processing data: ")
                raise NationalRailClientException("unexpected data from api") from err
            return data

        return {}
