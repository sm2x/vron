"""
RON Communication class

http://wiki.respax.com.au/respax/ron_api

"""

##########################
# Imports
##########################
from django.conf import settings
import xmlrpc.client





##########################
# Class definitions
##########################
class Ron( object ):
    """
    Class responsible to send requests to RON
    http://wiki.respax.com.au/respax/ron_api

    """

    def __init__( self, config_info ):
        """
        Constructor responsible to set class attributes
        and login to the RON server

        :param: Dictionary config_info
        :return: Boolean
        """
        self.config_info = config_info
        self.host_id = ''
        self.ron_session_id = ''
        self.error_message = ''

    def connect( self ):
        """
        Tries to connect to the RON server

        :return: Mixed
        """
        url = self.config_info[settings.ID_CONFIG_RON_TEST_URL]
        if self.ron_session_id:
            url += '&' + self.ron_session_id
        return xmlrpc.client.ServerProxy( url )

    def login( self, reseller_id ):
        """
        Tries to login to the RON api

        :param: host_id
        :return: Boolean
        """

        # Creates XML-RPC server connection
        ron = self.connect()

        # Calls login method
        try:
            self.ron_session_id = ron.login(
                self.config_info[settings.ID_CONFIG_RON_USERNAME],
                self.config_info[settings.ID_CONFIG_RON_PASSWORD],
                reseller_id
            )
            return True
        except xmlrpc.client.Fault:
            return False

    def read_tour_pickups( self, tour_code, tour_time_id, basis_id ):
        """
        Returns a list of dictionaries from the host each containing the details of a
        pickup location and time for the specified tour, time and basis combination

        :param: String tour_code
        :param: String tour_time_id
        :param: String basis_id
        :return: List
        """

        # Creates ron XML-RPC server connection
        ron = self.connect()

        # Calls ron method
        try:
            result = ron.readTourPickups( self.host_id, tour_code, tour_time_id, basis_id )
            return result
        except xmlrpc.client.Fault:
            return False

    def write_reservation( self, reservation ):
        """
        Returns a dictionary containing a single associative array of
        extended information for the host including contact information.

        :param: Dictionary reservation
        :return: Mixed
        """

        # Creates ron XML-RPC server connection
        ron = self.connect()

        # Calls ron method
        try:
            result = ron.writeReservation( self.host_id, -1, reservation, { 'strPaymentOption': 'full-agent' }, {} )
            return result
        except xmlrpc.client.Fault as error:
            self.error_message = error.faultString
            return False