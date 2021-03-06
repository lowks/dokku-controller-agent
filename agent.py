from docker import Client
import socket
from netaddr import IPAddress, IPNetwork
import redis
import json
import time
import os
import urlparse
import netifaces

url = urlparse.urlparse(os.environ.get('REDIS_URL', 'redis://localhost:6379/'))
pool = redis.ConnectionPool(host=url.hostname, port=url.port, db=0, password=url.password)
redis_connection = redis.StrictRedis(connection_pool=pool)
private_ip = os.environ.get('PRIVATE_IP', None)
if private_ip:
    private_ip = IPAddress(private_ip)
private_network = os.environ.get('PRIVATE_NETWORK', None)
if private_network:
    private_network = IPNetwork(private_network)

d = Client()


def get_private_ip_or_hostname():
    if private_ip:
        return str(private_ip)
    for iface in netifaces.interfaces():
        if iface.startswith("eth"):
            for address_list in netifaces.ifaddresses(iface).values():
                for address_dict in address_list:
                    if not ":" in address_dict['addr']:
                        if IPAddress(address_dict['addr']).is_private():
                            if not private_network or IPAddress(address_dict['addr']) in private_network:
                                return address_dict['addr']
    return socket.gethostname()


while True:
    apps = []
    containers = d.containers()  # Get all current containers from docker
    for container in containers:
        app_name = container['Image']
        if 'dokcon/' in app_name:
            apps.append(
                [
                    app_name.split("dokcon/")[1].split(":")[0],
                    container['Ports'].split("->")[0].replace("0.0.0.0:", "")
                ]
            )
    print "reporting %s" % json.dumps({get_private_ip_or_hostname(): apps})
    redis_connection.publish("app_announce", json.dumps({get_private_ip_or_hostname(): apps}))
    time.sleep(10)
