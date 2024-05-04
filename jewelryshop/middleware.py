from django.http import HttpResponseForbidden
from ipware import get_client_ip
import geoip2.database
import logging
from django.conf import settings

class CountryAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.reader = geoip2.database.Reader('GeoIP2-Country-Test.mmdb')
        self.logger = logging.getLogger(__name__)

    def __call__(self, request):
        client_ip, _ = get_client_ip(request)
        if client_ip and client_ip != '127.0.0.1': 
            try:
                response = self.reader.country(client_ip)
                country_code = response.country.iso_code
                self.logger.info(f"Request from IP {client_ip} is from country {country_code}")
                if country_code != 'BD':  
                    self.logger.warning(f"Access from IP {client_ip} (country: {country_code}) is restricted.")
                    return HttpResponseForbidden("Access from your country is restricted.")
            except Exception as e:
                self.logger.error(f"Error while processing request from IP {client_ip}: {e}")
        return self.get_response(request)


class IPDomainFilterMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self.is_malicious(request):
            return HttpResponseForbidden("Access Forbidden")
        return self.get_response(request)

    def is_malicious(self, request):
        client_ip = request.META.get('REMOTE_ADDR')

        if client_ip in settings.MALICIOUS_IPS:
            return True

        host = request.get_host()
        domain = host.split(':')[0]

        if domain in settings.MALICIOUS_DOMAINS:
            return True

        return False

        