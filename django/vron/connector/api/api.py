"""
API Handling Class

"""

##########################
# Imports
##########################
from lxml import etree, objectify
from django.conf import settings
from vron.core.util import get_object_or_false
from vron.connector.models import Config, Key
from vron.connector.tasks import log_request
from vron.connector.api.xml_manager import XmlManager
from vron.connector.api.ron import Ron
from vron.connector.api.viator import Viator





##########################
# Class definitions
##########################
class Api( object ):
    """
    The API class responsible to receive the request and
    redirect to the right objects

    """

    def __init__( self, xml_raw ):
        """
        Constructor responsible to set class attributes and
        to process the right request

        :param: xml_raw
        :return: None
        """

        # Gets all config from the DB
        config_options = Config.objects.all()
        config = {}
        for config_option in config_options:
            config[config_option.id] = config_option.value

        # Instantiates class attributes
        self.config_info = config
        self.request_xml = XmlManager( xml_raw )
        self.response_xml = XmlManager()
        self.ron = Ron( config )
        self.viator = Viator( self.request_xml, self.response_xml )

        # Errors
        self.errors = {
            'VRONERR001': 'Malformed or missing elements',
            'VRONERR002': 'Invalid API KEY',
            'VRONERR003': 'RON authentication failed',
        }

    def process( self ):
        """
        Executes the API actions and returns formatted
        xml response.

        :return: XML
        """
        # If XML is valid, gets root tag name to call appropriate API method
        if self.request_xml.validated:
            tag = self.request_xml.get_tag_name()
            if 'BookingRequest' in tag:
                return self.booking_request()
            elif 'AvailabilityRequest' in tag:
                return self.availability_request()
            else:
                return self.basic_error_response( 'Request not supported - ' + tag )
        else:
            return self.basic_error_response( self.request_xml.error_message )

    def basic_error_response( self, error_message ):
        """
        Return error response when no supported tag was found

        :param: error_message
        :return: XML
        """
        self.response_xml.create_root_element( 'Error' )
        message = self.response_xml.create_element( 'message' )
        self.response_xml.create_element_text( error_message, message )
        return self.response_xml.return_xml_string()

    def booking_request( self ):
        """
        Receives a xml request from viator, convert the data for
        RON requirments and write a reservation in RON

        :return: XML
        """
        # Logs request in the background (using celery)
        self.log_request(
            settings.ID_LOG_STATUS_RECEIVED,
            self.viator.get_external_reference()
        )

        # Gets all required viator data and checks if any is empty
        booking_empty_check = self.viator.check_booking_data()
        if booking_empty_check != True:
            return self.viator.booking_response( '', '', 'VRONERR001', booking_empty_check, self.errors['VRONERR001'] )

        # Validates api key
        if not self.validate_api_key( self.viator.get_api_key() ):
            return self.viator.booking_response( '', '', 'VRONERR002', 'ApiKey', self.errors['VRONERR002'] )

        # Logs in RON
        if not self.ron.login( self.viator.get_distributor_id() ):
            return self.viator.booking_response( '', '', 'VRONERR003', 'ResellerId', self.errors['VRONERR003'] )

        # Get tour pickups in RON
        tour_pickups = self.ron.read_tour_pickups(
            self.viator.get_tour_code(),
            self.viator.get_tour_time_id(),
            self.viator.get_basis_id()
        )

        # Creates reservation dictionary for RON
        reservation = {
            'strCfmNo_Ext': self.viator.get_external_reference(),
            'strTourCode': self.viator.get_tour_code(),
            'strVoucherNo': self.viator.get_voucher_number(),
            'intBasisID': self.viator.get_basis_id(),
            'intSubBasisID': self.viator.get_sub_basis_id(),
            'dteTourDate': self.viator.get_tour_date(),
            'intTourTimeID': self.viator.get_tour_time_id(),
            'strPaxFirstName': self.viator.get_first_name(),
            'strPaxLastName': self.viator.get_last_name(),
            'strPaxEmail': self.viator.get_email(),
            'strPaxMobile': self.viator.get_mobile(),
            'intNoPax_Adults': self.viator.get_pax_adults(),
            'intNoPax_Infant': self.viator.get_pax_infants(),
            'intNoPax_Child': self.viator.get_pax_child(),
            'intNoPax_FOC': self.viator.get_pax_foc(),
            'intNoPax_UDef1': self.viator.get_pax_udef1(),
            'strPickupKey': self.viator.get_pickup_key( tour_pickups ),
            'strGeneralComment': 'First tests',
        }

        # Writes booking in RON
        booking_result = self.ron.write_reservation( reservation )

        # Returnx XML formatted response
        return self.viator.booking_response( booking_result, self.ron.error_message )

    def availability_request( self ):
        """
        Receives a xml request from viator, convert the data for
        RON requirments and run an availability check in RON

        :return: Boolean
        """
        return 'Not supported yet!'

    def log_request( self, log_status_id, external_reference, error_message = None ):
        """
        Saves request info to the database

        :param: log_status_id
        :param: external_reference
        :param: error_message
        :return: Boolean
        """
        # sends to the background with celery
        log_request.delay( external_reference, log_status_id, error_message )

    def validate_api_key( self, api_key ):
        """
        Checks if API key is valid

        :return: Boolean
        """
        # Uses base key (set on config) to split the text and identify host id
        base_key = self.config_info[settings.ID_CONFIG_BASE_API_KEY]
        if api_key is not None and base_key in api_key:
            host_id = api_key.replace( base_key, '' )
            self.viator.host_id = host_id
            self.ron.host_id = host_id

            # Searches for key/host_id in the DB
            key = get_object_or_false( Key, name = self.ron.host_id )
            if key:
                return True
        return False